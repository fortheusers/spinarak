#! /usr/bin/python3
### 4TU Tools: pkggen.py by CompuCat.
### WARNING: This script does a good bit of directory tomfoolery. Back/forward slashes not tested on Windows/macOS/what have you; works fine on Linux.
import os,sys,json
from datetime import datetime
import urllib.request
import shutil
import tempfile
import glob

### Configurable parameters
version='0.0.3'
ignored_directories=[".git"] #These will *NOT* be scanned for pkgbuilds
output_directory="out" #Repository output directory
valid_binary_extensions=(".nro", ".elf", ".rpx") #Extensions to search for when guessing binary path

### Methods, etc.
def underprint(x): print(x+"\n"+('-'*len(x))) #Prints with underline. Classy, eh?

def get_size(start_path): #I do love my oneliners. Oneliner to get the size of a directory recursively.
	return sum([sum([os.path.getsize(os.path.join(dirpath,f)) for f in filenames if not os.path.islink(os.path.join(dirpath,f))]) for dirpath, dirnames, filenames in os.walk(start_path)])

def remove_prefix(text, prefix): #thanks SE for community-standard method, strips prefix from string
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

def handleAsset(pkg, asset, manifest, subasset=False, prepend="\t"): #Downloads and places a given asset.
	if subasset: asset_file=open(asset['url'], "rb")
	elif os.path.isfile(pkg+asset['url']): # Check if file exists locally
		print(prepend+"Asset is local.")
		asset_file=open(pkg+asset['url'], "rb")
	else: # Download asset from URL
		print(prepend+"Downloading asset...", end="")
		sys.stdout.flush()
		asset_file=tempfile.NamedTemporaryFile()
		shutil.copyfileobj(urllib.request.urlopen(asset['url']), asset_file)
		print("done.")
		#asset_file_path=pkg+'/temp_asset'
	if asset['type'] in ('update', 'get', 'local', 'extract'):
		print(prepend+"- Type is "+asset['type']+", moving to /"+asset['dest'].strip("/"))
		manifest.write(asset['type'].upper()[0]+": "+asset['dest'].strip("/")+"\n")
		os.makedirs(os.path.dirname(pkg+"/"+asset['dest'].strip("/")), exist_ok=True)
		shutil.copyfileobj(asset_file, open(pkg+"/"+asset['dest'].strip("/"), "wb"))
	elif asset['type'] == 'icon':
		print(prepend+"- Type is icon, moving to /icon.png")
		shutil.copyfileobj(asset_file, open(pkg+'/icon.png', "wb"))
	elif asset['type'] == 'screenshot':
		print(prepend+"- Type is screenshot, moving to /screen.png")
		shutil.copyfileobj(asset_file, open(pkg+'/screen.png', "wb"))
	elif asset['type'] == 'zip':
		print(prepend+"- Type is zip, has "+str(len(asset['zip']))+" sub-asset(s)")
		tempdir = tempfile.TemporaryDirectory()
		shutil.unpack_archive(asset_file.name, extract_dir=tempdir.name, format="zip")
		for subasset in asset['zip']:
			for filepath in glob.glob(tempdir.name+subasset['path'], recursive=True):
				if not os.path.isdir(filepath):
					handleAsset(pkg, {'url':filepath, 'type':subasset['type'], 'dest':subasset['dest']+remove_prefix(filepath, tempdir.name+subasset['path'].rstrip("*/"))}, manifest, subasset=True, prepend=prepend+"\t")
					#TODO: check that rstrip to see what other globbable weird characters need stripping
	else: print("ERROR: asset of unknown type detected. Skipping.")

def main():
	#Initialize script and detect packages.
	underprint("4TU Tools: This is pkggen.py v"+version+" by CompuCat.")
	pkg_dirs=list(filter(lambda x: (x not in ignored_directories) and os.path.isfile(x+"/pkgbuild.json"), next(os.walk('.'))[1])) #Finds top-level directories that are not ignored and have a pkgbuild.
	print(str(len(pkg_dirs))+" detected packages: "+str(pkg_dirs)+"\n")

	os.makedirs(output_directory, exist_ok=True) #Create output directory
	repojson={'packages':[]} #Instantiate repo.json format

	#Package all the things
	for pkg in pkg_dirs:
		#TODO: avoid rebuilding packages that haven't actually changed.
		pkgbuild=json.load(open(pkg+"/pkgbuild.json")) #Read pkgbuild.json
		underprint("Now packaging: "+pkgbuild['info']['title'])
		manifest=open(pkg+"/manifest.install", 'w')
		#TODO: validate the pkgbuild and gracefully skip invalid packages

		print(str(len(pkgbuild['assets']))+" asset(s) detected")
		for asset in pkgbuild['assets']: handleAsset(pkg, asset, manifest)

		pkginfo={ #Format package info
			'category': pkgbuild['info']['category'],
			'name': pkgbuild['package'],
			'license': pkgbuild['info']['license'],
			'title': pkgbuild['info']['title'],
			'url': pkgbuild['info']['url'],
			'author': pkgbuild['info']['author'],
			'version': pkgbuild['info']['version'],
			'details': pkgbuild['info']['details'],
			'description': pkgbuild['info']['description'],
			'changelog': pkgbuild['changes'], #TODO: handle changelog better
			'updated': str(datetime.utcfromtimestamp(os.path.getmtime(pkg+"/pkgbuild.json")).strftime('%Y-%m-%d')),
		}
		json.dump(pkginfo, open(pkg+"/info.json", "w"), indent=1) # Output package info to info.json
		print("info.json generated.")
		manifest.close()
		print("manifest.install generated.")
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
			if pkginfo['category']=="theme":
				repo_extended_info['binary']="none"
				print("INFO: binary path not specified. Category is theme, so autofilling \"none\".")
			else:
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

if __name__ == "__main__": main()
