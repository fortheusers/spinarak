#! /usr/bin/python3
### 4TU Tools: spinarak.py by CompuCat
### WARNING: This script does a good bit of directory tomfoolery. Back/forward slashes not tested on Windows/macOS/what have you; works fine on Linux.
import os, sys, json, shutil, zipfile, glob, tempfile, datetime, io
import urllib.request

version = '0.0.8'

#Build opener that prevents failed retrieves on some sites
opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]
urllib.request.install_opener(opener)

config_default = """# spinarak config
ignored_directories = ".git"
output_directory = "public"
valid_binary_extensions = [".nro", ".elf", ".rpx"]
"""

# Original zipit code:
# http://stackoverflow.com/a/6078528
#
# Call `zipit` with the path to either a directory or a file.
# All paths packed into the zip are relative to the directory
# or the directory of the file.

# zipit has been modified to not require an archive name (since it's not writing to one)
# it now uses a bytes object to store the zip contents so it never hits disk
# Additionally it has been given an 'exclude' argument which should be passed a list of file names to exclude from the zip
def zipit(path, exclude = None):
	virtual_zip = io.BytesIO()
	archive = zipfile.ZipFile(virtual_zip, "w", zipfile.ZIP_DEFLATED)
	if os.path.isdir(path):
		_zippy(path, path, archive, exclude)
	else:
		_, name = os.path.split(path)
		archive.write(path, name)
	return virtual_zip
	
def _zippy(base_path, path, archive, exclude):
	paths = os.listdir(path)
	for p in paths:
		q = os.path.join(path, p)
		if os.path.isdir(q):
			_zippy(base_path, q, archive, exclude)
		else:
			if p in exclude:
				continue
			archive.write(q, os.path.relpath(q, base_path))

### Methods, etc.
def underprint(x): print(x+"\n"+('-'*len(x.strip()))) #Prints with underline. Classy, eh?

def get_size(start_path): #I do love my oneliners. Oneliner to get the size of a directory recursively.
	return sum([sum([os.path.getsize(os.path.join(dirpath,f)) for f in filenames if not os.path.islink(os.path.join(dirpath,f))]) for dirpath, dirnames, filenames in os.walk(start_path)])

def remove_prefix(text, prefix): #thanks SE for community-standard method, strips prefix from string
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

def handleAsset(pkg, asset, manifest, subasset=False, prepend="\t"): #Downloads and places a given asset.
	if subasset: asset_file=open(asset['url'], "rb")
	elif os.path.isfile(pkg+'/'+asset['url']): # Check if file exists locally
		print(prepend+"Asset is local.")
		asset_file=tempfile.NamedTemporaryFile()
		shutil.copyfileobj(open(pkg+'/'+asset['url'], "rb"), asset_file)
		asset_file.seek(0)
	else: # Download asset from URL
		print(prepend+"Downloading "+asset['url']+"...", end="")
		sys.stdout.flush()
		asset_file=tempfile.NamedTemporaryFile()
		shutil.copyfileobj(urllib.request.urlopen(asset['url']), asset_file)
		asset_file.seek(0)
		print("done.")
		#asset_file_path=pkg+'/temp_asset'
	if asset['type'] in ('update', 'get', 'local', 'extract'):
		print(prepend+"- Type is "+asset['type']+", moving to /"+asset['dest'].strip("/"))
		manifest.write(asset['type'].upper()[0]+": "+asset['dest'].strip("/")+"\n") #Write manifest.install
		os.makedirs(os.path.dirname(pkg+"/"+asset['dest'].strip("/")), exist_ok=True)
		shutil.copyfileobj(asset_file, open(pkg+"/"+asset['dest'].strip("/"), "wb"))
	elif asset['type'] == 'icon':
		print(prepend+"- Type is icon, moving to /icon.png")
		shutil.copyfileobj(asset_file, open(pkg+'/icon.png', "wb"))
		os.makedirs(config.output_directory+'/packages/'+pkg, exist_ok=True)
		shutil.copyfile(pkg+'/icon.png', config.output_directory+'/packages/'+pkg+'/icon.png')
	elif asset['type'] == 'screenshot':
		print(prepend+"- Type is screenshot, moving to /screen.png")
		shutil.copyfileobj(asset_file, open(pkg+'/screen.png', "wb"))
		os.makedirs(config.output_directory+'/packages/'+pkg, exist_ok=True)
		shutil.copyfile(pkg+'/screen.png', config.output_directory+'/packages/'+pkg+'/screen.png')
	elif asset['type'] == 'zip':
		print(prepend+"- Type is zip, has "+str(len(asset['zip']))+" sub-asset(s)")
		with tempfile.TemporaryDirectory() as tempdirname:
			shutil.unpack_archive(asset_file.name, extract_dir=tempdirname, format="zip")
			handledSubAssets=0
			for subasset in asset['zip']:
				for filepath in glob.glob(tempdirname+"/"+subasset['path'].lstrip("/"), recursive=True):
					if not os.path.isdir(filepath): #Don't try to handle a directory as an asset - assets must be single files
						#TODO: check that rstrip to see what other globbable weird characters need stripping
						subassetInfo={
							'url':filepath,
							'type':subasset['type'],
							'dest':("/"+subasset['dest'].lstrip("/")+remove_prefix(filepath, tempdirname+"/"+subasset['path'].lstrip("/").rstrip(".*/"))) if 'dest' in subasset else None
						}
						handleAsset(pkg, subassetInfo, manifest, subasset=True, prepend=prepend+"\t")
						handledSubAssets+=1
			if handledSubAssets!=len(asset['zip']): print("INFO: discrepancy in subassets handled vs. listed. "+str(handledSubAssets)+" handled, "+str(len(asset['zip']))+" listed.")
	else: print("ERROR: asset of unknown type detected. Skipping.")
	asset_file.close()

def main():
	#Initialize script and create output directory.
	underprint("This is Spinarak v"+version+" by CompuCat and the 4TU Team.")

	if not os.path.isfile(os.path.join(__file__, "config.py")):
		with open(os.path.join(__file__, "config.py"), 'w+') as cfg:
			cfg.write(config_default)

	import config

	#Instantiate output directory if needed and look for pre-existing libget repo.
	updatingRepo=False #This flag is True if and only if the output directory is a valid libget repo; it tells Spinarak to skip repackaging packages that haven't changed.
	if os.path.isdir(config.output_directory):
		if len(os.listdir(config.output_directory))==0: pass
		else:
			try:
				previousRepojson=json.load(open(config.output_directory+"/repo.json"))
				updatingRepo=True
				print("INFO: the output directory is already a libget repo! Updating the existing repo.")
			except:
				print("ERROR: output directory is not empty and is not a libget repo. Stopping.")
				sys.exit(0)
	else: os.makedirs(config.output_directory)

	if not os.path.isdir(os.path.join(config.output_directory, "zips")):
		os.mkdir(os.path.join(config.output_directory, "zips"))


	pkg_dirs=list(filter(lambda x: (x not in config.ignored_directories) and os.path.isfile(x+"/pkgbuild.json"), next(os.walk("."))[1])) #Finds top-level directories that are not ignored and have a pkgbuild.
	print(str(len(pkg_dirs))+" detected packages: "+str(pkg_dirs)+"\n")

	repojson={'packages':[]} #Instantiate repo.json format
	failedPackages=[]
	skippedPackages=[]

	#Package all the things
	for pkg in pkg_dirs:
		#TODO: avoid rebuilding packages that haven't actually changed.
		#Open and validate pkgbuild
		try:
			pkgbuild=json.load(open(pkg+"/pkgbuild.json")) #Read pkgbuild.json
			for x in ('category','package','license','title','url','author','version','details','description'): #Check for required components
				if x not in pkgbuild and x not in pkgbuild['info']: raise LookupError("pkgbuild.json is missing the "+x+" component.")
		except Exception as e:
			 failedPackages.append(pkg)
			 print("ERROR: failed to build "+pkg+"! Error message: "+str(e)+"\n")
			 continue

		if updatingRepo: #Avoid rebuilding packages that haven't changed.
			prevPkgInfo=next(((pkg for pkg in previousRepojson['packages'] if pkg['name']==pkgbuild['package'])), None) #Search for existing package
			if prevPkgInfo == None: underprint("Now packaging: "+pkgbuild['info']['title'])
			else:
				if prevPkgInfo['version']==pkgbuild['info']['version']:
					print(pkgbuild['info']['title']+" hasn't changed, skipping.\n")
					skippedPackages.append(pkg)
					repojson['packages'].append(prevPkgInfo) #Copy package info from previous repo.json
					continue
				else:
					underprint("Now updating: "+pkgbuild['info']['title'])
					os.remove(config.output_directory+"/zips/"+pkg+".zip")
		else: underprint("Now packaging: "+pkgbuild['info']['title'])
		manifest=open(pkg+"/manifest.install", 'w')

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
			'updated': str(datetime.datetime.utcfromtimestamp(os.path.getmtime(pkg+"/pkgbuild.json")).strftime('%Y-%m-%d')),
		}
		try: pkginfo['changelog']=pkgbuild['changelog']
		except:
			if 'changes' in pkgbuild:
				pkginfo['changelog']=pkgbuild['changes']
				print("WARNING: the `changes` field was deprecated from the start. Use `changelog` instead.")
			else: print("WARNING: no changelog found!")
		json.dump(pkginfo, open(pkg+"/info.json", "w"), indent=1) # Output package info to info.json
		print("info.json generated.")
		manifest.close()
		print("manifest.install generated.")
		print("Package is "+str(get_size(pkg)//1024)+" KiB large.")
		z = zipit(pkg, exclude = ["pkgbuild.json"]) #Create in-memory zip.
		with open(config.output_directory+"/zips/"+pkg+".zip", "w+b") as out:
			out.write(z.getvalue()) #Write the zip out.
		# shutil.make_archive(config.output_directory+"/zips/"+pkg, 'zip', pkg) # Zip folder and output to out directory
		# TODO: above make_archive includes the pkgbuild. Rewriting to use the zipfile module directly would allow avoiding the pkgbuild in the output zip
		print("Package written to "+config.output_directory+"/zips/"+pkg+".zip")
		print("Zipped package is "+str(os.path.getsize(config.output_directory+"/zips/"+pkg+".zip")//1024)+" KiB large.")

		repo_extended_info={ #repo.json has package info plus extended info
			'extracted': get_size(pkg)//1024,
			'filesize': os.path.getsize(config.output_directory+"/zips/"+pkg+".zip")//1024,
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
						if file.endswith(tuple(config.valid_binary_extensions)):
							repo_extended_info['binary']=os.path.join(dirpath,file)[os.path.join(dirpath,file).index("/"):]
							broken=True
							break
						if broken: break
				if not broken: print("WARNING: "+pkgbuild['info']['title']+"'s binary path not specified in pkgbuild.json, and no binary found!")
				else: print("WARNING: binary path not specified in pkgbuild.json; guessing "+repo_extended_info['binary']+".")
		repo_extended_info.update(pkginfo) #Add package info and extended info together

		repojson['packages'].append(repo_extended_info) #Append package info to repo.json
		print() #Console newline at end of package. for prettiness

	json.dump(repojson, open(config.output_directory+"/repo.json", "w"), indent=1) #Output repo.json
	print(config.output_directory+"/repo.json generated.")

	underprint("\nSUMMARY")
	print("Built "+str(len(pkg_dirs)-len(failedPackages)-len(skippedPackages))+" of "+str(len(pkg_dirs))+" packages.")
	if len(failedPackages)>0: print("Failed packages: "+str(failedPackages))
	if len(skippedPackages)>0: print("Skipped packages: "+str(skippedPackages))
	print("All done. Enjoy your new repo :)")

if __name__ == "__main__": main()