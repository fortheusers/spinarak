#! /usr/bin/python3
import os,json
from datetime import datetime
import urllib.request
import shutil
from zipfile import ZipFile
version='0.0.0'
ignored_directories=[".git"]
output_directory="out"

###Initialize script and get list of packages to...well, package.
print("This is pkggen.py by CompuCat v"+version)
pkg_dirs=list(filter(lambda x: (x not in ignored_directories) and os.path.isfile(x+"/pkgbuild.json"), next(os.walk('.'))[1])) #Walks directory tree, gets top level directories, then filters out ignored directories such as .git.
print(str(len(pkg_dirs))+" detected packages:")
print(pkg_dirs)

repojson={'packages':[]}

###Package all the things
for pkg in pkg_dirs:
	pkgbuild=json.load(open(pkg+"/pkgbuild.json")) #Read pkgbuild.json
	print("Now packaging: "+pkgbuild['info']['title'])
	manifest=""
	for asset in pkgbuild['assets']: #Possible asset types: update, get, local, extract, zip, icon, screenshot
		print("\tAsset detected")
		if os.path.isfile(pkg+asset['url']): # Check if file exists locally
			print("\t\tAsset is local.")
			asset_file_path=pkg+asset['url']
		else: # Download asset from URL 
			print("\t\tDownloading asset...", end="")
			with urllib.request.urlopen(asset['url']) as response, open(pkg+"/temp_asset", 'wb') as out_file:
				shutil.copyfileobj(response, out_file)
			print("done.")
			asset_file_path=pkg+'/temp_asset'
		if asset['type'] in ('update', 'get', 'local', 'extract'):
			print("\t\t- Type is "+asset['type']+", moving to "+asset['dest'])
			manifest+=asset['type'].upper()[0]+": "+asset['dest'].strip("/")
			os.makedirs(os.path.dirname(pkg+"/"+asset['dest'].strip("/")), exist_ok=True)
			shutil.move(asset_file_path, pkg+"/"+asset['dest'].strip("/"))
		elif asset['type'] == 'icon':
			print("\t\t- Type is icon, moving to /icon.png")
			shutil.move(asset_file_path, pkg+'/icon.png')
		elif asset['type'] == 'screenshot':
			print("\t\t- Type is screenshot, moving to /screen.png")
			shutil.move(asset_file_path, pkg+'/screen.png')
		elif asset['type'] == 'zip':
			print("\t\t- Type is zip, TODO")
			for subasset in asset['zip']: #WARNING: this will not traverse a nested zip.
				
		else: print("ERROR: asset of unknown type detected. Skipping.")
	
	pkginfo={ #Format package info
		'category': pkgbuild['info']['category'],
		'name': pkgbuild['package'],
		'license': pkgbuild['info']['license'],
		'title': pkgbuild['info']['title'],
		'url': pkgbuild['info']['url'],
		'author': pkgbuild['info']['author'],
		'version': pkgbuild['info']['version'],
		'details': "pingpong",#pkgbuild['info']['details'],
		'description': "test",#pkgbuild['info']['description'],
		'changelog': pkgbuild['changes'], #TODO: handle changelog better
		'updated': str(datetime.utcfromtimestamp(os.path.getmtime(pkg+"/pkgbuild.json")).strftime('%Y-%m-%d')), #TODO: only generate if package is actually different
	}
	# Output package info to info.json
	# Get size of folder
	# Zip folder and output to out directory
	# Get size of zipped folder
	
	repo_extended_info={ #repo.json has package info plus extended info
		'binary': 'TODO', #TODO: generate binary path
		'extracted': -1, #TODO: calculate these sizes and actually include them GASP
		'filesize': -1,
		'web_dls': -1, #TODO: get these counts from stats API
		'app_dls': -1
	}
	repo_extended_info.update(pkginfo) #Add package info and extended info together
	
	repojson['packages'].append(repo_extended_info) # Add info blurb to repo.json
# - Place repo.json in output directory
