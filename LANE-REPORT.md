# LANE 10 report: nationalsecurityagency.github.io (code.nsa.gov)

Branch: `lane/listing-refresh` (pushed to `origin`, fork-only; not upstream-bound).

## 1. Upstream contribution rules

- No CONTRIBUTING.md exists. README: `pages/index.md`, `_data/*.yml` are the
  maintainer-editable surfaces; `_data/temp.json` is for repos outside the two orgs.
- CI (`.github/workflows/jekyll.yaml`) = `bundle exec jekyll build` on Ruby 3.3.
- Maintainer stance (ctubbsii, PR #54, 2023-04): outside contributions to the
  generated data cannot be trusted/accepted; they use an internal Python script.
  Issue #51 ("Dynamically generate repos.json") remains open.
- The tracker is currently flooded with spam issues (#77-#88); keep any issue
  single, factual and short to read.

## 2. What changed and why

Commits on `lane/listing-refresh` (on top of upstream `main` c45ecc6):

| Commit | Content |
|---|---|
| `0f9eb15` | `scripts/audit_listing.py` + `scripts/listing_common.py` (stdlib only, GitHub REST, token from `GH_TOKEN`/`GITHUB_TOKEN`/`gh auth token`) and `AUDIT.md` = its output against the unmodified upstream data. |
| `70b967f` | `scripts/regen_listing.py`: rebuilds `_data/repos.json` + `code.json` in the same field shape and ordering (per org, by creation date; display names like "SeaBee" kept; external entries kept as written with only stats/canonical URL refreshed; `--include-org`, `--exclude`, `--dry-run`). |
| `906412f` | Regenerated data (2026-11-17). Data-only diff: 112 -> 142 entries, +31 repos, -1 (nsacyber/Cyber-Challenge, 404), 48 flagged `"archived": true`, `code.json` 97 -> 127 releases (archived = `"status": "Archival"`), dead `anbangr/OpenAttestation` appended to `ignore.yml`. |
| `9c6ce84` | Template: "Archived" label on cards (3 lines in `_includes/project-list.html`, reuses `card-link` + Font Awesome 5 `fa-archive`). Separate commit so the data commit renders unchanged without it. |
| `efd5364` | `.github/workflows/refresh-listing.yml`: `workflow_dispatch` + monthly cron, guarded by `if: github.repository != 'NationalSecurityAgency/...'`; regenerates, audits, runs `jekyll build`, opens a PR with `AUDIT.md` as body. |
| `27063f7` | README section "How this fork differs from code.nsa.gov". |

Design choice on archived repos: kept listed with a flag rather than moved to
`ignore.yml`, because several (SIMP, 10 QGIS plugins) are still widely used and
have live successors; hiding them would lose that. The flag is ignored by the
unmodified template, so the data commit is safe on its own.

## 3. Evidence

Audit against upstream data (`python3 scripts/audit_listing.py`, ~26 s):

```
wrote .../AUDIT.md: 112 listed, 109 rendered, 127 live, 31 missing, 4 dead, 43 archived-listed, 104 stale
```

Regeneration (`python3 scripts/regen_listing.py`), checked afterwards:

```
order preserved for common: True
removed ['https://github.com/nsacyber/cyber-challenge']
code.json top-level keys/metadata unchanged: True True
release key set identical to original: ('name','repositoryURL','description','permissions','laborHours','tags','contact','status','vcs','homepageURL','downloadURL','date','languages')
licenses null (no license file): ghidra-extensions, datawave-tables, datawave-stack-docker-images, datawave-helm-charts, ghidra-frida, datawave-accumulo-plugins, ghidra-lisa, dnf-model-counting
Archival releases: 48
CR bytes in any changed file: none (LF kept)
git diff --stat: _data/ignore.yml 3 +-, _data/repos.json 792 +-, code.json 2109 +-
```

Rendered project count (entries in repos.json + temp.json not in ignore.yml,
exactly what `project-list.html` iterates):

| | Entries | Rendered cards | Archived labels |
|---|---|---|---|
| upstream `main` | 112 | 109 | 0 |
| `lane/listing-refresh` | 142 | 138 | 47 |

`bundle exec jekyll build` passes on both trees (Ruby 3.3.8, bundler 2.5.16, `bundle install` from the
checked-in Gemfile.lock; only the theme's existing Sass deprecation warnings):

```
== AFTER (lane/listing-refresh 27063f7)
WARNING: 266 repetitive deprecation warnings omitted.
                    done in 79.231 seconds.
== BEFORE (main c45ecc6)
WARNING: 266 repetitive deprecation warnings omitted.
                    done in 67.928 seconds.
before: site-before/index.html cards=109 archived_labels=0
after:  site-after/index.html  cards=138 archived_labels=47
exit=0
```

(card counts = `grep -c '<div class="card">'` on the built `index.html`, matching
the structural count in the table above.)

Workflow `refresh-listing.yml` has not been run on GitHub yet (see next steps).

## 4. Competing work check

- #51 Dynamically generate repos.json (open, 2023): ctubbsii said internal scripts exist and may replace any outside implementation.
  https://github.com/NationalSecurityAgency/nationalsecurityagency.github.io/issues/51
- #54 Generate repos.json via workflow (closed unmerged 2023-04-28): "I do not think that we're going to be able to keep this updated with anything contributed from outside."
  https://github.com/NationalSecurityAgency/nationalsecurityagency.github.io/pull/54
- #49 Sort repo list and use github api (closed), #50 sort by stars (closed).
- #33 OpenAttestation is not found on GitHub (closed 2021-10-31) - yet the dead entry is still listed.
- #36 (2021-10-25) was the last bulk regeneration; fbb89f4 (2025-07-11) hand-added SeaBee.
- No open PR touches `_data/repos.json` or `code.json`.

## 5. Draft upstream ISSUE (paste verbatim; no PR)

Title: `Project listing audit: 31 repos missing, 43 archived repos shown as active (relates to #51)`

Body:

````markdown
Hi, a short, data-only report in case it is useful for #51. I read the maintainer
comments on #51 and #54 about the internal script and the constraints on
outside contributions, so this is **not** a PR and I will not open one unless you
ask for it.

I compared `_data/repos.json` and `code.json` (last bulk update in #36, plus the
SeaBee entry in fbb89f4) against the public repos of NationalSecurityAgency and
nsacyber as of 2026-11-17:

| Measure | Count |
|---|---|
| Entries rendered on code.nsa.gov | 109 |
| Live public repos in the two orgs (excluding `.github`) | 127 |
| Live repos missing from the listing | 31 |
| Dead or empty links | 4 |
| Archived repos listed without any marker | 43 |
| Live repos with no `code.json` release | 31 |

**Missing, not archived** (selection): TraceAnalysis, Foundation, ghidra-extensions,
ghidra-frida, ghidra-volatility, ghidra-lisa, openflame, rank-based-linkage,
dnf-model-counting, nsacyber/ELITEWOLF (653 stars), nsacyber/RIM-Tool, and 16
datawave-* service repos. Also missing but archived: maat, qgis-densityanalysis-plugin,
qgis-h3library-plugin, qgis-cotraveler-plugin.

**Dead links:** nsacyber/Cyber-Challenge (404), anbangr/OpenAttestation (404,
reported in #33), and Apache NIFI / SEAndroid have an empty `html_url`.

**Archived but shown as active:** SIMP (continued at https://github.com/simp),
10 qgis-* plugins (continued at https://github.com/hamiltoncj/qgis-*), DCP, MADCert,
kmyth, pelz, accumulo-python3, and 27 nsacyber repos (e.g. GRASSMARLIN,
Windows-Secure-Host-Baseline, WALKOFF, goSecure).

**Stale stats:** e.g. ghidra shows 29,303 stars (live: 100,463).

The full tables are in the report below. It was produced by a short,
standard-library-only Python script that only reads the public REST API; the same
repo also has a regenerator that writes both files in their existing field order,
so a diff is data-only. Both are here if they are of any use to the internal
process, entirely optional:

- Report: https://github.com/Dukotah/nationalsecurityagency.github.io/blob/lane/listing-refresh/AUDIT.md
- Scripts: https://github.com/Dukotah/nationalsecurityagency.github.io/tree/lane/listing-refresh/scripts

Happy to close this if it duplicates work already in progress.
````

## 6. Land probability and next steps

- Issue: **High** that it is read - it is factual, small, references #51/#54 and asks for nothing; the maintainer is active (merged dependabot PRs in 2026).
- Data PR: **Low** - the maintainer explicitly closed #54 because generated data from outside contributors cannot be trusted under their constraints and must come from their internal script.

Owner next steps:
1. Review `AUDIT.md` and the issue text; open the issue yourself if you want (lanes never contact upstream). The draft deliberately contains no `@` mentions, so nobody is notified.
2. To try the fork workflow: in the fork's Settings > Actions > General enable "Allow GitHub Actions to create and approve pull requests", then run "Refresh listing" manually.
3. Optionally enable GitHub Pages on the fork from `lane/listing-refresh` to see the rendered listing (the `CNAME` file would need removing on a fork branch first).
