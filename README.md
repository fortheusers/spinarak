# AutoJSONThing
---

See #ci-scripts in the 4TU Discord. This needs to:

- Accept committed repo metadata
- Create hostable zip packages out of repo metadata
- Generate repo.json for all build artifacts

Order of operations:
- For each package directory:
	- Read pkgbuild.json
	- Download assets
	- Create zip package from assets (THIS FORMAT IS UNCLEAR)
	- If successful, create repo.json blurb
		- Copy the following from pkgbuild.json:
			- category
			- package name
			- license
			- title
			- source url
			- author
			- version
			- details
			- description
			- (copy or append) changes
		- Generate the following:
			- Binary path (???)
			- Update date
			- Counters (extracted, webdls, appdls)
			- Zip filesize
		- Add blurb to repo.json
	- Place zip in hosting directory
- Place repo.json in hosting directory