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


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f(); print("ok", k)
