"""Shared helpers: paths, loading the profile / CV / jobs, stable job IDs."""
import datetime as dt
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ME = os.environ.get("JOB_TRACKER_HOME") or os.path.join(ROOT, "me")

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("Missing dependency: run  pip install -r requirements.txt")


def me_path(me, *parts):
    return os.path.join(me or DEFAULT_ME, *parts)


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_json(path, default=None):
    if not os.path.exists(path):
        if default is not None:
            return default
        sys.exit(f"{path} not found")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def load_profile(me=None):
    p = me_path(me, "profile.yaml")
    if not os.path.exists(p):
        sys.exit(f"No profile at {p}. Copy examples/profile.example.yaml there (or ask Claude to set you up).")
    return load_yaml(p)


def load_country(code):
    p = os.path.join(ROOT, "countries", f"{code}.yaml")
    return load_yaml(p) if os.path.exists(p) else None


def norm(s):
    """Must match norm() in template/tracker.html - IDs are shared with the browser."""
    s = "" if s is None else str(s)
    s = s.lower()
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def make_id(company, role):
    return norm(company) + "|" + norm(role)


def url_key(u):
    """Must match urlKey() in the template."""
    from urllib.parse import urlparse
    try:
        x = urlparse(u)
        if not x.netloc:
            raise ValueError
        host = re.sub(r"^www\.", "", x.netloc)
        path = re.sub(r"/application/?$", "", x.path).rstrip("/")
        return (host + path).lower()
    except Exception:
        return str(u or "").lower()


def today():
    return dt.date.today().isoformat()
