"""Shared helpers for audit_listing.py and regen_listing.py (stdlib only).

Authentication: GH_TOKEN or GITHUB_TOKEN from the environment, otherwise the
token of a logged-in GitHub CLI (`gh auth token`). Unauthenticated requests
work too but hit the 60 requests/hour limit quickly.
"""

import json
import os
import re
import subprocess
import urllib.error
import urllib.request

API = "https://api.github.com"
DEFAULT_ORGS = ["NationalSecurityAgency", "nsacyber"]
# Org profile repositories are not projects.
DEFAULT_EXCLUDE = [".github"]

REPO_URL_RE = re.compile(r"^https://github\.com/([^/]+)/([^/]+?)/?$", re.I)


def _token():
    for var in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True,
                             text=True, check=True)
        return out.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


class GitHub:
    def __init__(self):
        self.token = _token()
        self.cache = {}

    def _request(self, url):
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "code-nsa-gov-listing")
        if self.token:
            req.add_header("Authorization", "Bearer " + self.token)
        with urllib.request.urlopen(req, timeout=60) as resp:
            nxt = None
            for part in (resp.headers.get("Link") or "").split(","):
                m = re.search(r'<([^>]+)>;\s*rel="next"', part)
                if m:
                    nxt = m.group(1)
            return json.load(resp), nxt

    def get(self, path):
        """GET an API path, following pagination. Returns None on 404."""
        if path in self.cache:
            return self.cache[path]
        url = path if path.startswith("http") else API + path
        result = None
        try:
            while url:
                data, url = self._request(url)
                if isinstance(data, list):
                    result = (result or []) + data
                else:
                    result = data
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            result = None
        self.cache[path] = result
        return result

    def org_repos(self, org, exclude=DEFAULT_EXCLUDE):
        repos = self.get("/orgs/%s/repos?type=public&per_page=100" % org) or []
        repos = [r for r in repos if r["name"] not in exclude and not r["private"]]
        return sorted(repos, key=lambda r: r["created_at"])

    def repo(self, owner, name):
        return self.get("/repos/%s/%s" % (owner, name))


def parse_repo_url(url):
    """Return (owner, name) for a github.com/<owner>/<repo> URL, else None."""
    m = REPO_URL_RE.match(url or "")
    return (m.group(1), m.group(2)) if m else None


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump_json(path, obj):
    # Same formatting as the checked-in files: 2-space indent, trailing newline.
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, indent=2) + "\n")


def load_ignore(path):
    """Read the `toc:` URL list from _data/ignore.yml (flat list only)."""
    urls = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("- "):
                urls.append(line[2:].strip())
    return urls


def rendered(repos_list, temp_list, ignore):
    """Entries the Jekyll template actually renders (project-list.html)."""
    return [e for e in repos_list + temp_list if e.get("html_url") not in ignore]


def successor(gh, entry_url, repo):
    """Best-known successor URL for an archived repo, verified to exist."""
    owner, name = parse_repo_url(entry_url)
    candidates = []
    if name.lower() == "simp":
        candidates.append(("simp", None))
    if name.lower().startswith("qgis-"):
        candidates.append(("hamiltoncj", name))
    for c_owner, c_name in candidates:
        if c_name is None:
            if gh.get("/orgs/%s" % c_owner):
                return "https://github.com/%s" % c_owner
        else:
            r = gh.repo(c_owner, c_name)
            if r and not r["archived"]:
                return r["html_url"]
    return ""
