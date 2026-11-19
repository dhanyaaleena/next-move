"""Offline tests: python -m pytest tests  (or python tests/test_scripts.py)."""
import json, os, subprocess, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import search_jobs as S  # noqa: E402
from common import load_yaml, make_id  # noqa: E402

LI = '''<li><div class="base-card" data-entity-urn="urn:li:jobPosting:4491333580">
<a class="base-card__full-link" href="https://uk.linkedin.com/jobs/view/senior-agent-4491333580?trk=x"></a>
<h3 class="base-search-card__title">
  Senior Backend Engineer
</h3><h4 class="base-search-card__subtitle"><a href="#">Example &amp; Co</a></h4>
<span class="job-search-card__location">Berlin, Germany</span>
<time class="job-search-card__listdate" datetime="2026-11-18">1 day ago</time></div></li>
<li><div class="base-card" data-entity-urn="urn:li:jobPosting:4491333581">
<h3 class="base-search-card__title">Product Manager</h3><h4 class="base-search-card__subtitle">Other</h4>
<span class="job-search-card__location">London</span></div></li>'''


def profile():
    return load_yaml(os.path.join(ROOT, "examples", "profile.example.yaml"))


def test_parse_linkedin():
    r = S.parse_linkedin(LI)
    assert len(r) == 2
    assert r[0]["url"] == "https://www.linkedin.com/jobs/view/4491333580"
    assert r[0]["role"] == "Senior Backend Engineer" and r[0]["company"] == "Example & Co"
    assert r[0]["place"] == "Berlin, Germany" and r[0]["posted"] == "2026-11-18"


def test_matchers():
    t, l = S.title_matcher(profile()), S.location_matcher(profile())
    assert t("Senior Backend Engineer") == "Backend"
    assert t("Product Manager") is None
    assert l("Amsterdam, North Holland") == "Netherlands"
    assert l("Remote - Europe") == "Remote EU"
    assert l("London") is None


def test_ids_match_browser():
    # same normalisation as norm() in template/tracker.html
    assert make_id("Acme (via Hays)", "Backend Engineer – Payments!") == "acme|backend engineer payments"


def test_pipeline():
    me = tempfile.mkdtemp()
    try:
        shutil.copy(os.path.join(ROOT, "examples", "profile.example.yaml"), os.path.join(me, "profile.yaml"))
        shutil.copy(os.path.join(ROOT, "examples", "cv.example.json"), os.path.join(me, "cv.json"))
        def run(script, *args):
            return subprocess.run([sys.executable, script, "--me", me, *args], capture_output=True, text=True, cwd=ROOT)
        r = run("scripts/jobs.py", "add", "--file", "examples/jobs.example.json")
        assert "3 added" in r.stdout, r.stdout + r.stderr
        r = run("scripts/jobs.py", "add", "--file", "examples/jobs.example.json")
        assert "0 added, 3 already tracked" in r.stdout
        bad = {"company": "X", "role": "Backend Engineer", "url": "https://x.example/1", "location": "Berlin",
               "track": "Backend", "fit": "High", "visa": {"status": "unclear"}}
        r = run("scripts/jobs.py", "add", "--json", json.dumps(bad))
        assert "REFUSED" in r.stdout
        r = run("scripts/build.py", "--out", os.path.join(me, "t.html"))
        assert r.returncode == 0, r.stderr
        html = open(os.path.join(me, "t.html"), encoding="utf-8").read()
        assert "/*__CONFIG__*/" not in html and "Example Fintech GmbH" in html
    finally:
        shutil.rmtree(me)


def test_answers_checker():
    import answers as A
    prof, cv = profile(), json.load(open(os.path.join(ROOT, "examples", "cv.example.json")))
    job = {"company": "Example Fintech GmbH", "role": "Backend Engineer"}
    good = [{"q": "Why do you want to work here?", "a": "Example Fintech is rebuilding card payments, which is what I do. I moved our ledger to Go handling 3M+ transactions a day."}]
    e, w, _ = A.check(job, good, prof, cv)
    assert not e and not w, (e, w)
    bad = [{"q": "Why this role?", "a": "I'm passionate about Rust and cut costs by 85%.", "limit": 20}]
    e, w, _ = A.check(job, bad, prof, cv)
    assert any("85" in x for x in e) and any("Rust" in x for x in e) and any("allows 20" in x for x in e), e
    assert any("passionate" in x for x in w), w
    honest = [{"q": "Fit?", "a": "I haven't used Rust yet, but I'd pick it up quickly."}]
    assert not A.check(job, honest, prof, cv)[0]
    generic = [{"q": "Why do you want to work here?", "a": "I like building reliable systems that people depend on every day, with a team that cares about quality."}]
    assert any("never names" in x for x in A.check(job, generic, prof, cv)[1])


def test_backup_merge_and_roundtrip():
    import backup as B
    cur = {"jobs": {"a|x": {"status": "Applied", "updated": "2026-11-10T10:00:00Z"},
                    "b|y": {"status": "To apply", "updated": "2026-11-12T10:00:00Z"}}}
    inc = {"jobs": {"a|x": {"status": "Rejected", "updated": "2026-11-11T10:00:00Z", "hist": [{"s": "Applied"}, {"s": "Rejected"}]},
                    "b|y": {"status": "Applied", "updated": "2026-11-01T10:00:00Z"},
                    "c|z": {"status": "Interviewing", "updated": "2026-11-05T10:00:00Z", "round": 2}},
           "msgd": {"a|x|Sam": "2026-11-02"}, "extra": {"a|x": [["Sam Lee", "EM", "", "Added by you"]]}}
    assert B.merge(cur, inc) == 2
    assert cur["jobs"]["a|x"]["status"] == "Rejected" and cur["jobs"]["a|x"]["hist"]   # newer wins
    assert cur["jobs"]["b|y"]["status"] == "To apply"                                   # newer local reset kept
    assert cur["jobs"]["c|z"]["round"] == 2 and cur["msgd"] and cur["extra"]["a|x"]
    tmp = tempfile.mkdtemp()
    try:
        me = os.path.join(tmp, "me"); os.makedirs(me)
        open(os.path.join(me, "profile.yaml"), "w").write("storage_prefix: t\n")
        open(os.path.join(me, "jobs.json"), "w").write('{"jobs": []}')
        bk = os.path.join(tmp, "t-tracker-backup-2026-11-19.json")
        json.dump({"format": "next-move-backup", "browser": {"store": inc, "tailored": {}}}, open(bk, "w"))
        B.cmd_save(me, bk, os.path.join(tmp, "out"))
        assert json.load(open(os.path.join(me, "statuses.json")))["store"]["jobs"]["c|z"]["status"] == "Interviewing"
        z = [f for f in os.listdir(os.path.join(tmp, "out")) if f.endswith(".zip")][0]
        me2 = os.path.join(tmp, "me2")
        B.cmd_restore(me2, os.path.join(tmp, "out", z))
        assert os.path.exists(os.path.join(me2, "statuses.json")) and os.path.exists(os.path.join(me2, "jobs.json"))
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f(); print("ok", k)
