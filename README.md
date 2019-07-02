# AutoJSONThing
---

This is a 4TU tool to generate a libget repo from a set of pkgbuilds.

In short, this will:
- Accept committed repo `pkgbuild.json`s
- Download package assets, generate metadata, and zip up packages
- Generate repo.json for all built packages

To run: `python3 pkggen.py` in a directory containing subdirectories named for each package...each themselves containing a pkgbuild.

You can blacklist directories in the top few lines of the script; you can also change the output directory (`/out` by default).

KNOWN ISSUES:
- zip assets not supported yet
- nested zip assets not supported
- built packages include the pkgbuild, which isn't necessary
- if a zip asset is local, it will be removed
- changelog consists of last change only
- stats API integration is completely missing
- always rebuilds all packages regardless of change date (change date is sync'd with pkgbuild.json modified date though)

TODO:
- parse cli arguments for output directory
- Dockerize the crap out of this
