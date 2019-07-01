pkgbuild.json has:
- Package name string
- Info blurb
	- Title string
	- Author string
	- Category string 
	- Version string 
	- URL string 
	- License string 
	- Description string 
	- Details string 
- Changes string
- Assets array of blurbs, containing:
	- URL for asset string
	- Asset type string
	- ???
	
Repo.json has:
- Packages, an array of blurbs, containing:
	- Category string (COPY)
	- Binary path string
	- Update date string
	- Package name string (COPY)
	- License string (COPY)
	- Title string (COPY)
	- Source URL string (COPY)
	- Author string (COPY)
	- Changelog string (copy or append from changes string)
	- Extracted size in kibibytes
	- Version string (COPY)
	- Filesize int
	- web_dls int counter
	- details string (COPY)
	- app_dls int counter
	- description string (COPY)
	
pkggen needs to generate for each package:
- assets
- manifest.install
- info.json

repo.json is just all the info.json's