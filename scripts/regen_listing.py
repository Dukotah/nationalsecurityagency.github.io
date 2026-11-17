#!/usr/bin/env python3
"""Regenerate _data/repos.json and code.json from the live GitHub orgs.

    python3 scripts/regen_listing.py [--include-org ORG ...] [--dry-run]

Output keeps the shape of the checked-in files so a regeneration diff is
data-only:

* First-party entries (repos owned by an --include-org) are rebuilt from the
  API, grouped by org in the order given and sorted by creation date, which is
  how the existing files are ordered. A display name already used in the file
  for the same URL (e.g. "SeaBee") is kept.
* Entries owned by anyone else (Apache Accumulo, beer-garden, ...) are kept
  as written, in their original order; only forks/stars and the canonical URL
  are refreshed. They are not added to code.json, matching the existing file.
* Archived repos stay listed and get "archived": true in repos.json and
  "status": "Archival" in code.json (a code.gov metadata 2.0 status value).
* External repo URLs that now return 404 are appended to _data/ignore.yml so
  the page stops rendering them; the entry itself is left in repos.json.
"""

import argparse
import os
import sys

from listing_common import (DEFAULT_EXCLUDE, DEFAULT_ORGS, GitHub, dump_json,
                            load_ignore, load_json, parse_repo_url)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONTACTS = {
    "nsacyber": {
        "email": "cybersecurity_requests@nsa.gov",
        "URL": "https://www.nsa.gov/about/contact-us/",
        "name": "NSA Cybersecurity",
        "phone": "410-854-4200",
    },
}
DEFAULT_CONTACT = {
    "email": "tech_transfer@nsa.gov",
    "URL": "https://www.nsa.gov/Research/Technology-Transfer-Program/",
    "name": "NSA Technology Transfer Program",
    "phone": "1-866-680-4539",
}


def repo_entry(r, name):
    e = {
        "name": name,
        "html_url": r["html_url"],
        "forks_count": r["forks_count"],
        "stargazers_count": r["stargazers_count"],
        "description": r["description"] or "",
        "homepage": r["homepage"] or "",
    }
    if r["archived"]:
        e["archived"] = True
    return e


def code_release(gh, r, name):
    full = r["full_name"]
    lic = gh.get("/repos/%s/license" % full)
    if lic and lic.get("license"):
        licenses = [{
            "URL": "%s/blob/%s/%s" % (r["html_url"], r["default_branch"], lic["path"]),
            "name": lic["license"]["name"],
        }]
    else:
        licenses = None  # code.gov 2.0: null when no license is available
    languages = gh.get("/repos/%s/languages" % full) or {}
    return {
        "name": name,
        "repositoryURL": r["html_url"],
        "description": r["description"] or "",
        "permissions": {"licenses": licenses, "usageType": "openSource"},
        "laborHours": 1,
        "tags": r.get("topics") or [],
        "contact": dict(CONTACTS.get(r["owner"]["login"].lower(), DEFAULT_CONTACT)),
        "status": "Archival" if r["archived"] else "Production",
        "vcs": "git",
        "homepageURL": r["homepage"] or r["html_url"],
        "downloadURL": "%s/archive/%s.zip" % (r["html_url"], r["default_branch"]),
        "date": {
            "created": r["created_at"][:10],
            "metadataLastUpdated": r["updated_at"][:10],
            "lastModified": r["pushed_at"][:10],
        },
        "languages": list(languages),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--include-org", action="append",
                    help="GitHub org whose public repos are listed (repeatable); "
                         "default: %s" % ", ".join(DEFAULT_ORGS))
    ap.add_argument("--exclude", action="append", default=list(DEFAULT_EXCLUDE),
                    help="repo name to leave out (repeatable); default: .github")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would change without writing files")
    args = ap.parse_args()
    orgs = args.include_org or DEFAULT_ORGS
    org_keys = {o.lower() for o in orgs}

    repos_path = os.path.join(ROOT, "_data", "repos.json")
    code_path = os.path.join(ROOT, "code.json")
    ignore_path = os.path.join(ROOT, "_data", "ignore.yml")
    repos_doc = load_json(repos_path)
    code_doc = load_json(code_path)
    ignore = load_ignore(ignore_path)
    gh = GitHub()

    old = repos_doc["list"]
    old_names = {e["html_url"].lower(): e["name"] for e in old if e.get("html_url")}
    old_code_names = {c["repositoryURL"].lower(): c["name"]
                      for c in code_doc["releases"]}

    first_party, releases = [], []
    for org in orgs:
        for r in gh.org_repos(org, exclude=args.exclude):
            key = r["html_url"].lower()
            first_party.append(repo_entry(r, old_names.get(key, r["name"])))
            releases.append(code_release(gh, r, old_code_names.get(key, r["name"])))

    externals, dead = [], []
    for e in old:
        ref = parse_repo_url(e.get("html_url"))
        if ref and ref[0].lower() in org_keys:
            continue  # first-party; rebuilt above (or gone upstream)
        e = dict(e)
        if ref:
            r = gh.repo(*ref)
            if r is None:
                dead.append(e["html_url"])
            else:
                e["html_url"] = r["html_url"]
                e["forks_count"] = r["forks_count"]
                e["stargazers_count"] = r["stargazers_count"]
                if r["archived"]:
                    e["archived"] = True
                else:
                    e.pop("archived", None)
        externals.append(e)

    new_list = first_party + externals
    old_urls = {e.get("html_url", "").lower() for e in old}
    new_urls = {e.get("html_url", "").lower() for e in new_list}
    added = sorted(u for u in new_urls - old_urls)
    removed = sorted(u for u in old_urls - new_urls)
    new_ignore = [u for u in dead if u not in ignore]

    print("repos.json: %d -> %d entries (+%d added, -%d removed, %d archived)"
          % (len(old), len(new_list), len(added), len(removed),
             sum(1 for e in new_list if e.get("archived"))))
    print("code.json:  %d -> %d releases" % (len(code_doc["releases"]), len(releases)))
    for u in removed:
        print("  removed (no longer in org): %s" % u)
    for u in new_ignore:
        print("  dead external link, adding to ignore.yml: %s" % u)
    if args.dry_run:
        return 0

    repos_doc["list"] = new_list
    code_doc["releases"] = releases
    dump_json(repos_path, repos_doc)
    dump_json(code_path, code_doc)
    if new_ignore:
        with open(ignore_path, encoding="utf-8") as f:
            text = f.read()
        if not text.endswith("\n"):
            text += "\n"
        text += "".join("  - %s\n" % u for u in new_ignore)
        with open(ignore_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
