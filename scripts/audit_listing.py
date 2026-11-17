#!/usr/bin/env python3
"""Compare the code.nsa.gov project listing against the live GitHub orgs.

Reads _data/repos.json, _data/temp.json, _data/ignore.yml and code.json,
queries the GitHub REST API and writes a Markdown report (default AUDIT.md).
Read-only with respect to the site data.

    python3 scripts/audit_listing.py [--include-org ORG ...] [-o AUDIT.md]
"""

import argparse
import datetime
import os
import sys

from listing_common import (DEFAULT_EXCLUDE, DEFAULT_ORGS, GitHub, load_ignore,
                            load_json, parse_repo_url, rendered, successor)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STALE_ROWS = 25


def md_escape(s):
    return (s or "").replace("|", "\\|").replace("\n", " ").strip()


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--include-org", action="append",
                    help="GitHub org to treat as first-party (repeatable); "
                         "default: %s" % ", ".join(DEFAULT_ORGS))
    ap.add_argument("-o", "--output", default=os.path.join(ROOT, "AUDIT.md"))
    args = ap.parse_args()
    orgs = args.include_org or DEFAULT_ORGS
    org_keys = {o.lower() for o in orgs}

    repos = load_json(os.path.join(ROOT, "_data", "repos.json"))["list"]
    temp = load_json(os.path.join(ROOT, "_data", "temp.json"))["list"]
    ignore = load_ignore(os.path.join(ROOT, "_data", "ignore.yml"))
    code = load_json(os.path.join(ROOT, "code.json"))["releases"]
    gh = GitHub()

    live = {}
    for org in orgs:
        for r in gh.org_repos(org):
            live[r["html_url"].lower()] = r

    listed = repos + temp
    listed_urls = {e["html_url"].lower() for e in listed if e.get("html_url")}
    shown = rendered(repos, temp, ignore)

    # Missing: live first-party repos absent from the listing.
    missing = [r for u, r in live.items() if u not in listed_urls]
    missing.sort(key=lambda r: (r["owner"]["login"].lower(), r["created_at"]))

    # Dead or empty links, and archived-but-listed.
    dead, archived, stale = [], [], []
    for e in listed:
        url = e.get("html_url") or ""
        if not url:
            dead.append((e["name"], "(empty `html_url`)", "no GitHub link rendered"))
            continue
        ref = parse_repo_url(url)
        if ref is None:
            continue  # org-level link such as https://github.com/nbgallery
        live_repo = live.get(url.lower())
        if live_repo is None:
            if ref[0].lower() in org_keys:
                live_repo = None  # first-party repo not in the org listing
            else:
                live_repo = gh.repo(*ref)
            if live_repo is None:
                dead.append((e["name"], url, "HTTP 404"))
                continue
        if live_repo["archived"] and url not in ignore:
            archived.append((e["name"], url, live_repo["pushed_at"][:10],
                             successor(gh, url, live_repo) or "-",
                             "yes" if e.get("archived") else "no"))
        if live_repo["stargazers_count"] != e.get("stargazers_count"):
            stale.append((e["name"], e.get("stargazers_count", 0),
                          live_repo["stargazers_count"],
                          e.get("forks_count", 0), live_repo["forks_count"]))
    stale.sort(key=lambda s: abs(s[2] - s[1]), reverse=True)

    # code.json drift against the live orgs.
    code_urls = [c["repositoryURL"].lower() for c in code]
    dupes = sorted({u for u in code_urls if code_urls.count(u) > 1})
    code_missing = sorted(r["html_url"] for u, r in live.items()
                          if u not in set(code_urls))
    code_gone = sorted(c["repositoryURL"] for c in code
                       if c["repositoryURL"].lower() not in live)

    now = datetime.datetime.now(datetime.timezone.utc)
    live_active = sum(1 for r in live.values() if not r["archived"])
    lines = [
        "# code.nsa.gov listing audit",
        "",
        "Generated %s by `scripts/audit_listing.py` from the GitHub REST API "
        "(orgs: %s; excluded repo names: %s)."
        % (now.strftime("%Y-%m-%d %H:%M UTC"), ", ".join(orgs),
           ", ".join("`%s`" % x for x in DEFAULT_EXCLUDE)),
        "",
        "## Summary",
        "",
        table(["Measure", "Count"], [
            ("Entries in `_data/repos.json` + `_data/temp.json`", len(listed)),
            ("Entries rendered (minus `_data/ignore.yml`)", len(shown)),
            ("Entries in `code.json`", len(code)),
            ("Live public repos in the orgs", len(live)),
            ("  of which not archived", live_active),
            ("Live repos missing from the listing", len(missing)),
            ("Dead or empty links in the listing", len(dead)),
            ("Archived repos listed without any marker", sum(1 for a in archived if a[4] == "no")),
            ("Listed repos whose star count differs from live", len(stale)),
        ]),
        "",
        "## Missing from the listing (%d)" % len(missing),
        "",
        table(["Repository", "Created", "Stars", "Archived", "Description"],
              [("[%s](%s)" % (r["full_name"], r["html_url"]), r["created_at"][:10],
                r["stargazers_count"], "yes" if r["archived"] else "no",
                md_escape(r["description"])) for r in missing]),
        "",
        "## Dead or empty links (%d)" % len(dead),
        "",
        table(["Entry", "URL", "Problem"], dead),
        "",
        "## Archived upstream but listed as active (%d)" % len(archived),
        "",
        "Successor is only filled in where a non-archived continuation was "
        "found and verified via the API.",
        "",
        table(["Entry", "URL", "Last push", "Successor", "Marked archived in data"],
              archived),
        "",
        "## Stale statistics (top %d of %d by star delta)"
        % (min(STALE_ROWS, len(stale)), len(stale)),
        "",
        table(["Entry", "Stars listed", "Stars live", "Forks listed", "Forks live"],
              stale[:STALE_ROWS]),
        "",
        "## code.json drift",
        "",
        "- Live repos with no `code.json` release: %d" % len(code_missing),
        "- `code.json` releases not found in the live orgs: %d%s"
        % (len(code_gone), (" (" + ", ".join(code_gone) + ")") if code_gone else ""),
        "- Duplicate `repositoryURL` values: %d%s"
        % (len(dupes), (" (" + ", ".join(dupes) + ")") if dupes else ""),
        "",
    ]
    with open(args.output, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print("wrote %s: %d listed, %d rendered, %d live, %d missing, %d dead, "
          "%d archived-listed, %d stale"
          % (args.output, len(listed), len(shown), len(live), len(missing),
             len(dead), len(archived), len(stale)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
