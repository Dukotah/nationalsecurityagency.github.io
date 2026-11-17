# code.nsa.gov

[![Build Status][bs]][bl] [![Apache License][li]][ll]

This Site Was built by using the 18F/uswds Jekyll theme. For more information
visit [U.S. Web Design System](https://designsystem.digital.gov).

You can view the original theme and documentation
[HERE](https://github.com/18F/uswds-jekyll).

Useful page edit information for maintainers and contributors:

* The `pages/index.md` file can be edited to change the sites main image as
  well as edit the featured repo. From the same file tagline and page intro can
  also be changed.
* The `data/navigation.yml` file can be edited to change the secondary and
  primary links for the header as well as the links present in the footer.
* The `data/header.yml` file can be edited to add or remove the top usa-banner,
  the logo image and link information.
* The `data/footer.yml` file can be edited to change the footer heading,
  contact information, social links, footer logo and return to top link.
* The `data/temp.json` file can be edited to add in a repository that exists
  outside of [NSAcyber](https://github.com/nsacyber) or
  [nationalsecurityagency](https://github.com/nationalsecurityagency) GitHub
  orgs.

## How this fork differs from code.nsa.gov

This is an unofficial fork. code.nsa.gov is built from the upstream `main`
branch; nothing here is published by NSA.

* `_data/repos.json` and `code.json` are regenerated from the live
  [nationalsecurityagency](https://github.com/nationalsecurityagency) and
  [NSAcyber](https://github.com/nsacyber) orgs instead of the 2021 snapshot.
  Entries for repositories outside those orgs are kept as written, with only
  their star and fork counts refreshed.
* Archived repositories stay listed but carry `"archived": true` in
  `_data/repos.json` (shown as an "Archived" label on the card) and
  `"status": "Archival"` in `code.json`.
* External links that return 404 are added to `_data/ignore.yml`.
* `scripts/audit_listing.py` writes `AUDIT.md`, a report of missing repos,
  dead links, archived repos and stale statistics.
* `scripts/regen_listing.py` rewrites the data files. Both scripts use only
  the Python standard library and read a token from `GH_TOKEN`,
  `GITHUB_TOKEN` or `gh auth token`:

  ```sh
  python3 scripts/regen_listing.py --dry-run
  python3 scripts/regen_listing.py
  python3 scripts/audit_listing.py
  bundle exec jekyll build
  ```

* `.github/workflows/refresh-listing.yml` runs the regenerator monthly (or on
  demand) and opens a pull request in the fork. It does not run in the
  upstream repository.

[bs]: https://github.com/nationalsecurityagency/nationalsecurityagency.github.io/workflows/CI/badge.svg
[bl]: https://github.com/nationalsecurityagency/nationalsecurityagency.github.io/actions
[li]: http://img.shields.io/badge/license-Apache%202.0-blue.svg
[ll]: https://github.com/nationalsecurityagency/nationalsecurityagency.github.io/blob/main/LICENSE

