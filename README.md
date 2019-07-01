# AutoJSONThing
---

See #ci-scripts in the 4TU Discord. This needs to:

- Accept committed repo `pkgbuild.json`s
- Download package assets, generate metadata, and zip up packages
- Generate repo.json for all built packages

To run: `python3 pkggen.py` in a directory containing subdirectories named for each package...each themselves containing a pkgbuild.

KNOWN ISSUES:
- zip assets not supported yet
- nested zip assets not supported
- built packages include the pkgbuild, which isn't necessary
- if a zip asset is local, it will be removed
- changelog isn't handled well
- stats API integration is completely missing