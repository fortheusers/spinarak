#! /usr/bin/python3
### 4TU Tools: pkggen.py by CompuCat.
### WARNING: This script does a good bit of directory tomfoolery. Back/forward slashes not tested on Windows; works fine on Linux.
import os,json
from datetime import datetime
import urllib.request
import shutil
from zipfile import ZipFile
version='0.0.1'
ignored_directories=[".git"]
output_directory="out"
valid_binary_extensions=(".nro", ".elf", ".rpx")


def underprint(x): print(x+"\n"+('-'*len(x))) #Prints with underline. Classy, eh?

def get_size(start_path): #Thanks stackoverflow, modified example to get directory size
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

###Initialize script and get list of packages to...well, package.
underprint("4TU Tools: This is pkggen.py v"+version+" by CompuCat.")
pkg_dirs=list(filter(lambda x: (x not in ignored_directories) and os.path.isfile(x+"/pkgbuild.json"), next(os.walk('.'))[1])) #Walks directory tree, gets top level directories, then filters out ignored directories such as .git.
print(str(len(pkg_dirs))+" detected packages: "+str(pkg_dirs)+"\n")
os.makedirs(output_directory, exist_ok=True) #Create output directory

repojson={'packages':[]}

###Package all the things
for pkg in pkg_dirs:
	pkgbuild=json.load(open(pkg+"/pkgbuild.json")) #Read pkgbuild.json
	underprint("Now packaging: "+pkgbuild['info']['title'])
	manifest=""
	print(str(len(pkgbuild['assets']))+" asset(s) detected")
	for asset in pkgbuild['assets']: #Possible asset types: update, get, local, extract, zip, icon, screenshot
		if os.path.isfile(pkg+asset['url']): # Check if file exists locally
			print("\tAsset is local.")
			asset_file_path=pkg+asset['url']
		else: # Download asset from URL 
			print("\tDownloading asset...", end="")
			with urllib.request.urlopen(asset['url']) as response, open(pkg+"/temp_asset", 'wb') as out_file:
				shutil.copyfileobj(response, out_file)
			print("done.")
			asset_file_path=pkg+'/temp_asset'
		if asset['type'] in ('update', 'get', 'local', 'extract'):
			print("\t- Type is "+asset['type']+", moving to "+asset['dest'])
			manifest+=asset['type'].upper()[0]+": "+asset['dest'].strip("/")
			os.makedirs(os.path.dirname(pkg+"/"+asset['dest'].strip("/")), exist_ok=True)
			shutil.move(asset_file_path, pkg+"/"+asset['dest'].strip("/"))
		elif asset['type'] == 'icon':
			print("\t- Type is icon, moving to /icon.png")
			shutil.move(asset_file_path, pkg+'/icon.png')
		elif asset['type'] == 'screenshot':
			print("\t- Type is screenshot, moving to /screen.png")
			shutil.move(asset_file_path, pkg+'/screen.png')
		elif asset['type'] == 'zip':
			print("\t- Type is zip, has "+str(len(asset['zip']))+" sub-asset(s)")
			for subasset in asset['zip']: #WARNING: this will not traverse a nested zip.
				print("TODO") #TODO: handle subassets
			os.remove(asset_file_path) #WARNING: this will remove a local zip. Not a problem for CI where it's all refreshed anyway, but still. Also, zips aren't likely to be local anyway.
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
	json.dump(pkginfo, open(pkg+"/info.json", "w"), indent=1) # Output package info to info.json
	print("info.json generated.")
	print("Package is "+str(get_size(pkg)//1024)+" KiB large.")
	shutil.make_archive(output_directory+"/"+pkg, 'zip', pkg) # Zip folder and output to out directory
	# TODO: above make_archive includes the pkgbuild. Rewriting to use the zipfile module directly would allow avoiding the pkgbuild in the output zip
	print("Zipped package is "+str(os.path.getsize(output_directory+"/"+pkg+".zip")//1024)+" KiB large.")
	
	repo_extended_info={ #repo.json has package info plus extended info
		'extracted': get_size(pkg)//1024,
		'filesize': os.path.getsize(output_directory+"/"+pkg+".zip")//1024,
		'web_dls': -1, #TODO: get these counts from stats API
		'app_dls': -1 #TODO
	}
	#Attempt to read binary path from pkgbuild; otherwise, guess it.
	try: repo_extended_info['binary']=pkgbuild['info']['binary']
	except:
		broken=False
		for (dirpath, dirnames, filenames) in os.walk(pkg):
			for file in filenames:
				if file.endswith(valid_binary_extensions):
					repo_extended_info['binary']=os.path.join(dirpath,file)[os.path.join(dirpath,file).index("/"):]
					broken=True
					break
				if broken: break
		if not broken: print("WARNING: binary path not specified in pkgbuild.json, and no binary found!")
		else: print("WARNING: binary path not specified in pkgbuild.json; guessing "+repo_extended_info['binary']+".")
	repo_extended_info.update(pkginfo) #Add package info and extended info together
	
	repojson['packages'].append(repo_extended_info) #Append package info to repo.json
	print() #Console newline at end of package. for prettiness
json.dump(repojson, open(output_directory+"/repo.json", "w"), indent=1) #Output repo.json
print("out/repo.json generated.")
print("All done. Enjoy your new repo :)")
