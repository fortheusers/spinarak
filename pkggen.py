#! /usr/bin/python3

import os,json
from datetime import datetime
version='0.0.0'
ignored_directories=[".git"]

print("This is pkggen.py by CompuCat v"+version)
pkg_dirs=list(filter(lambda x: (x not in ignored_directories) and os.path.isfile(x+"/pkgbuild.json"), next(os.walk('.'))[1])) #Walks directory tree, gets top level directories, then filters out ignored directories such as .git.
print(str(len(pkg_dirs))+" detected packages:")
print(pkg_dirs)

repojson={'packages':[]}

for pkg in pkg_dirs: # - For each package directory:
    pkgbuild=json.load(open(pkg+"/pkgbuild.json")) # 	- Read pkgbuild.json
    for asset in pkgbuild['assets']:
        print(asset)
# 	- Download assets
# 	- Create zip package from assets (THIS FORMAT IS UNCLEAR)
# 	- If successful, create repo.json blurb
    pkginfo={ #Copy info from pkgbuild
        'category': pkgbuild['info']['category'],
        'package': pkgbuild['package'],
        'license': pkgbuild['info']['license'],
        'title': pkgbuild['info']['title'],
        'url': pkgbuild['info']['url'],
        'author': pkgbuild['info']['author'],
        'version': pkgbuild['info']['version'],
        'details': pkgbuild['info']['details'],
        'description': pkgbuild['info']['description'],
        'changelog': pkgbuild['changes'], #TODO: handle changelog better
        'updated': print(datetime.utcfromtimestamp(os.path.getmtime(pkg+"/pkgbuild.json")).strftime('%Y-%m-%d'))
    }
# 		- Generate the following:
# 			- Binary path (???)
# 			- Update date
    #TODO: get counts from stats API
    pkginfo['extracted']=-1
    pkginfo['web_dls']=-1
    pkginfo['app_dls']=-1
# 			- Zip filesize
    repojson['packages'].append(pkginfo) # Add blurb to repo.json
# 	- Place zip in hosting directory
# - Place repo.json in hosting directory
