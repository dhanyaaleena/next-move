#!/usr/bin/env python3
"""Back up, move and restore everything in your job search.

Your data lives in two places:
  * on disk, in me/ (profile, CV, jobs with answers and contacts, notes) plus your tailored CVs folder,
    tracker page and Excel copy;
  * in your browser: statuses, their history, interview rounds, rejection stages, people you added,
    messaged ticks. Get these out with the tracker's "Back up" → "Download backup file".

    python scripts/backup.py statuses [file.json]   # copy browser statuses into me/statuses.json
    python scripts/backup.py save [--browser file.json] [--to folder]
                                                    # one zip with everything (picks up the newest
                                                    # backup file from Downloads automatically)
    python scripts/backup.py restore backup.zip     # unpack on a new computer (never overwrites)

me/statuses.json is embedded in the tracker page on every build, so a new or cleared browser gets
your statuses back. A status is only ever replaced by a newer change.
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DEFAULT_ME, ROOT, load_yaml, me_path  # noqa: E402

DOWNLOADS = os.path.expanduser("~/Downloads")


def profile_of(me):
    p = me_path(me, "profile.yaml")
    return load_yaml(p) if os.path.exists(p) else {}


def find_browser_backup(prefix):
    files = glob.glob(os.path.join(DOWNLOADS, f"{prefix}-tracker-backup-*.json"))
    return max(files, key=os.path.getmtime) if files else None


def read_backup(path):
    with open(path, encoding="utf-8") as f:
        inc = json.load(f)
    if inc.get("format") == "next-move-backup":
        br = inc.get("browser") or {}
        return br.get("store") or {}, br.get("tailored") or {}
    if "jobs" in inc:  # the quick-copy text from the Back up dialog
        return inc, {}
    sys.exit(f"{path} isn't a Next Move backup")


def merge(cur, inc):
    """Same rule as the page: a status is replaced only by a newer change. Returns how many changed."""
    n = 0
    cur.setdefault("jobs", {})
    for k in ("msgd",):
        cur.setdefault(k, {})
        for key, v in (inc.get(k) or {}).items():
            cur[k].setdefault(key, v)
    cur.setdefault("extra", {})
    for jid, people in (inc.get("extra") or {}).items():
        have = cur["extra"].setdefault(jid, [])
        for p in people:
            if not any(x[0] == p[0] for x in have):
                have.append(p)
    for jid, a in (inc.get("jobs") or {}).items():
        b = cur["jobs"].setdefault(jid, {})
        if a.get("status") and (not b.get("status") or (a.get("updated") and (not b.get("updated") or a["updated"] > b["updated"]))):
            for k in ("status", "updated", "hist", "rejStage", "round"):
                if a.get(k) is not None:
                    b[k] = a[k]
                else:
                    b.pop(k, None)
            n += 1
        for k in ("firstSeen", "snap"):
            if not b.get(k) and a.get(k):
                b[k] = a[k]
    if inc.get("baseline") and not cur.get("baseline"):
        cur["baseline"] = inc["baseline"]
    return n


def cmd_statuses(me, path):
    prof = profile_of(me)
    path = path or find_browser_backup(prof.get("storage_prefix", ""))
    if not path:
        sys.exit("No backup file found. In the tracker: Back up → Download backup file, then run this again.")
    store, tailored = read_backup(path)
    out = me_path(me, "statuses.json")
    saved = {}
    if os.path.exists(out):
        with open(out, encoding="utf-8") as f:
            saved = json.load(f)
    cur = saved.get("store") or {}
    n = merge(cur, store)
    tl = saved.get("tailored") or {}
    for k, v in tailored.items():
        tl.setdefault(k, v)
    saved = {"saved": dt.datetime.now().isoformat(timespec="seconds"), "from": os.path.basename(path), "store": cur, "tailored": tl}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(saved, f, ensure_ascii=False, indent=1)
    tracked = sum(1 for r in cur["jobs"].values() if r.get("status") and r["status"] != "To apply")
    print(f"statuses: {n} updated from {os.path.basename(path)} → {out} ({tracked} tracked roles)")
    return path


def add_tree(z, src, arc):
    if os.path.isfile(src):
        z.write(src, arc)
        return 1
    n = 0
    for root, _, files in os.walk(src):
        for fn in files:
            if fn == ".DS_Store":
                continue
            full = os.path.join(root, fn)
            z.write(full, os.path.join(arc, os.path.relpath(full, src)))
            n += 1
    return n


def cmd_save(me, browser, to):
    prof = profile_of(me)
    bfile = browser or find_browser_backup(prof.get("storage_prefix", ""))
    if bfile:
        cmd_statuses(me, bfile)
    else:
        print("note: no browser backup file found in Downloads — statuses come from me/statuses.json only.\n"
              "      In the tracker: Back up → Download backup file, then run this again to include the latest.")
    folder = os.path.expanduser(to or prof.get("backup_folder") or "~/Documents/Next Move backups")
    os.makedirs(folder, exist_ok=True)
    name = os.path.join(folder, f"next-move-{prof.get('storage_prefix', 'me')}-{dt.date.today().isoformat()}.zip")
    me_dir = me or DEFAULT_ME
    with zipfile.ZipFile(name, "w", zipfile.ZIP_DEFLATED) as z:
        counts = {"me": add_tree(z, me_dir, "me")}
        for key, arc in (("tailored_cv_folder", "tailored_cvs"), ("output_file", "tracker"), ("excel_file", "excel")):
            p = prof.get(key)
            if p and os.path.exists(os.path.expanduser(p)):
                src = os.path.expanduser(p)
                counts[arc] = add_tree(z, src, arc if os.path.isdir(src) else os.path.join(arc, os.path.basename(src)))
        if bfile:
            z.write(bfile, os.path.join("browser", os.path.basename(bfile)))
            counts["browser"] = 1
        z.writestr("BACKUP.json", json.dumps({"created": dt.datetime.now().isoformat(timespec="seconds"),
                                              "storage_prefix": prof.get("storage_prefix"),
                                              "paths": {k: prof.get(k) for k in ("tailored_cv_folder", "output_file", "excel_file")},
                                              "files": counts}, indent=1))
    print(f"saved {name}")
    print("  " + ", ".join(f"{k}: {v} file{'s' if v != 1 else ''}" for k, v in counts.items()))


def cmd_restore(me, zpath):
    me_dir = me or DEFAULT_ME
    with zipfile.ZipFile(zpath) as z:
        info = json.loads(z.read("BACKUP.json")) if "BACKUP.json" in z.namelist() else {}
        paths = info.get("paths") or {}
        target_me = me_dir
        if os.path.exists(me_dir) and os.listdir(me_dir):
            target_me = me_dir.rstrip("/") + ".restored-" + dt.date.today().isoformat()
            print(f"{me_dir} already has data, so nothing there is touched; restoring into {target_me}.\n"
                  f"Compare the two and swap the folders when you're happy.")
        dest = {"me/": target_me, "tailored_cvs/": os.path.expanduser(paths.get("tailored_cv_folder") or "~/Downloads/Tailored CVs"),
                "excel/": os.path.dirname(os.path.expanduser(paths.get("excel_file") or "~/Downloads/x")),
                "tracker/": os.path.dirname(os.path.expanduser(paths.get("output_file") or "~/Downloads/x")),
                "browser/": os.path.join(target_me, "browser-backups")}
        wrote = skipped = 0
        for n in z.namelist():
            for pre, base in dest.items():
                if n.startswith(pre) and not n.endswith("/"):
                    out = os.path.join(base, n[len(pre):])
                    if os.path.exists(out):
                        skipped += 1
                        break
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    with open(out, "wb") as f:
                        f.write(z.read(n))
                    wrote += 1
                    break
    print(f"restored {wrote} files ({skipped} already there, left as they were)")
    if target_me == me_dir:
        print("next: python scripts/build.py  — the page will carry your statuses into this browser")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--me", help="folder with profile.yaml etc. (default: ./me)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("statuses", help="copy a browser backup file into me/statuses.json")
    s1.add_argument("file", nargs="?")
    s2 = sub.add_parser("save", help="zip everything")
    s2.add_argument("--browser")
    s2.add_argument("--to")
    s3 = sub.add_parser("restore", help="unpack a backup zip")
    s3.add_argument("zip")
    a = ap.parse_args()
    if a.cmd == "statuses":
        cmd_statuses(a.me, a.file)
    elif a.cmd == "save":
        cmd_save(a.me, a.browser, a.to)
    else:
        cmd_restore(a.me, a.zip)
