# Spinarak

![logo](https://archives.bulbagarden.net/media/upload/2/2b/0167Spinarak.png)

**Spinarak** is a tool to generate a [libget](https://github.com/vgmoose/libget) repo, given a set of `pkgbuild` files describing packages. Developed for internal use at ForTheUsers to replace the original `repogen.py` script.

It is named after the beloved Pokémon [Spinarak](https://bulbapedia.bulbagarden.net/wiki/Spinarak_(Pok%C3%A9mon)), as it performs the delicate task of wrapping together messy piles of homebrew into a neat web of packages.

> It spins webs that are strong enough to withstand having stones set on them...

## Purpose

In short, Spinarak does the following:
- For each committed `pkgbuild.json`:
	- Download non-local package assets
	- Generate package metadata (`manifest.install`, `info.json`)
	- Fetch statistics from 4TU's stats system
	- Zip packages for distribution
- Generate the repository's index (`repo.json`), listing all built packages

## Usage

Generating a repository is simple:

#### 1. Set up the build directory
Create a directory to serve as the build directory; then, create subdirectories named for each package within it. Each subdirectory must contain `pkgbuild.json` (TODO: create document describing this format) describing how the package should be built; it can also optionally contain local assets to be used during packaging.

#### 2. Package your packages

Simply run `python3 spinarak.py` in the build directory. (TODO: dependencies, docker) Optionally, you can modify the sample `config.json` as you see fit; within it, you can change the output directory (`out` by default). You can also blacklist directories from being built as packages and set valid extensions for binary files. (If and only if the `pkgbuild.json` does not specify which file is the main binary of the package, Spinarak will use this list to detect valid binary files by their extension.) If a `config.json` is not present, Spinarak will use its default configuration.

A few notes about Spinarak's character and behavior:
- *It's an observant little spider*: it will auto-detect a previous libget repo in the output directory and update it.
- *It's a lazy little spider*: it will only update packages that have not changed.
- *It's a responsible little spider*: it will refuse to create a libget repo if the output directory isn't blank or nonexistent.

#### 3. Host your repository

The output directory is now a complete *libget* repo, which may be statically hosted via any conventional means.

## Known issues/limitations

- built packages include the pkgbuild, which isn't necessary
- stats API integration is completely missing
- Temp directories sometimes make it into the final zips by accident. (Maybe. Need to verify that this bug still happens.)

## TODO

- Link with stats API

Contributors:
- [CompuCat](https://compucat.me/about) - primary development
- [vgmoose](https://vgmoose.com) - Dockerization, integration with the Homebrew App Store
- [crc32](https://web.archive.org/web/20250427223458/https://crc32.dev/) and [pwsincd](https://github.com/pwsincd) - Referencing libget formatting
- [Whovian9369](https://digipres.club/@Whovian9369) - Writing documentation

...and the rest of the 4TU team.
