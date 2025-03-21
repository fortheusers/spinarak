#! /usr/bin/python3
### 4TU Tools: spinarak.py by CompuCat.
### WARNING: This script does a good bit of directory tomfoolery. Back/forward slashes not tested on Windows/macOS/what have you; works fine on Linux.
import os,sys,json
from datetime import datetime
import urllib.request
import shutil
import tempfile
import glob
import zipfile
import hashlib

version='0.0.9'

config_default={
	"ignored_directories": [".git"],
	"output_directory": "public",
	"valid_binary_extensions": (".nro", ".elf", ".rpx", ".cia", ".3dsx", ".dol")
}

cdnUrl = None
# set of files to always update, regardless of version
alwaysUpdate = set()

### Methods, etc.
def underprint(x): print(x+"\n"+('-'*len(x.strip()))) #Prints with underline. Classy, eh?

def get_size(start_path): #I do love my oneliners. Oneliner to get the size of a directory recursively.
	return sum([sum([os.path.getsize(os.path.join(dirpath,f)) for f in filenames if not os.path.islink(os.path.join(dirpath,f))]) for dirpath, dirnames, filenames in os.walk(start_path)])

def remove_prefix(text, prefix): #thanks SE for community-standard method, strips prefix from string
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

def downloadFileDirect(url, dest): #Downloads a file from a URL to a destination path on disk
	# we try to use wget if it's present, as this preserves the created at date from the server
	if shutil.which("wget"):
		os.system(f"wget -O {dest} {url}")
	# just use urllib
	with urllib.request.urlopen(url) as response, open(dest, 'wb') as out_file:
		shutil.copyfileobj(response, out_file)
	# ensure the modified and accesss times are the same as the birth time
	createdTime = os.stat(dest).st_birthtime
	os.utime(dest, (createdTime, createdTime))

def handleAsset(pkg, asset, manifest, subasset=False, prepend="\t", screenCount=0): #Downloads and places a given asset.
	if subasset: asset_file=open(asset['url'], "rb")
	elif os.path.isfile(pkg+'/'+asset['url']): # Check if file exists locally
		print(prepend+"Asset is local.")
		asset_file=tempfile.NamedTemporaryFile()
		shutil.copyfileobj(open(pkg+'/'+asset['url'], "rb"), asset_file)
		asset_file.seek(0)
	else: # Download asset from URL
		print(prepend+"Downloading "+asset['url']+"...")
		sys.stdout.flush()
		random_path = tempfile.NamedTemporaryFile().name + ".download"
		# for downloaded files, it's been moved manually to a temp location, so don't use a tmpfile
		downloadFileDirect(asset['url'], random_path)
		asset_file = open(random_path, "rb")
		print("File downloaded.")
	if asset['type'] in ('update', 'get', 'local', 'extract'):
		print(prepend+"- Type is "+asset['type']+", moving to /"+asset['dest'].strip("/"))
		manifest.write(asset['type'].upper()[0]+": "+asset['dest'].strip("/")+"\n") #Write manifest.install
		os.makedirs(os.path.dirname(pkg+"/"+asset['dest'].strip("/")), exist_ok=True)
		shutil.copy2(asset_file.name, pkg+"/"+asset['dest'].strip("/"))
	elif asset['type'] == 'icon':
		print(prepend+"- Type is icon, moving to /icon.png")
		shutil.copyfileobj(asset_file, open(pkg+'/icon.png', "wb"))
		os.makedirs(config["output_directory"]+'/packages/'+pkg, exist_ok=True)
		shutil.copyfile(pkg+'/icon.png', config["output_directory"]+'/packages/'+pkg+'/icon.png')
	elif asset['type'] == 'banner':
		print(prepend+"- Type is banner, moving to /screen.png")
		shutil.copyfileobj(asset_file, open(pkg+'/screen.png', "wb"))
		os.makedirs(config["output_directory"]+'/packages/'+pkg, exist_ok=True)
		shutil.copyfile(pkg+'/screen.png', config["output_directory"]+'/packages/'+pkg+'/screen.png')
	elif asset['type'] == 'screenshot':
		print(prepend+"- Type is screenshot, moving to /screen"+str(screenCount)+".png")
		shutil.copyfileobj(asset_file, open(pkg+'/screen'+str(screenCount)+'.png', "wb"))
		os.makedirs(config["output_directory"]+'/packages/'+pkg, exist_ok=True)
		shutil.copyfile(pkg+'/screen'+str(screenCount)+'.png', config["output_directory"]+'/packages/'+pkg+'/screen'+str(screenCount)+'.png')
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
	global config
	try: config=json.load(open("config.json"))
	except:
		print("Couldn't load config.json; using default configuration.")
		config=config_default
	
	if cdnUrl:
		print(f"INFO: (CI Mode) Downloading existing repo.json from {cdnUrl}")
		os.makedirs("public", exist_ok=True)
		# if we're running in CI mode, download an existing repo.json from the CDN
		req = urllib.request.Request(cdnUrl)
		with urllib.request.urlopen(req) as response:
			with open(config["output_directory"]+"/repo.json", "w") as f:
				f.write(response.read().decode("utf-8"))
		# this file's precense will be detected as an existing repo

	#Instantiate output directory if needed and look for pre-existing libget repo.
	updatingRepo=False #This flag is True if and only if the output directory is a valid libget repo; it tells Spinarak to skip repackaging packages that haven't changed.
	if os.path.isdir(config["output_directory"]):
		if len(os.listdir(config["output_directory"]))==0: pass
		else:
			try:
				previousRepojson=json.load(open(config["output_directory"]+"/repo.json"))
				updatingRepo=True
				print("INFO: the output directory is already a libget repo! Updating the existing repo.")
			except:
				print("ERROR: output directory is not empty and is not a libget repo. Stopping.")
				sys.exit(0)
	else: os.makedirs(config["output_directory"])

	#Detect packages.
	pkg_dirs=list(filter(lambda x: (x not in config["ignored_directories"]) and os.path.isfile(x+"/pkgbuild.json"), next(os.walk('.'))[1])) #Finds top-level directories that are not ignored and have a pkgbuild.
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
				# only refresh if the version has changed or the package is marked for always update
				if prevPkgInfo['version']==pkgbuild['info']['version'] and pkg not in alwaysUpdate:
					print(pkgbuild['info']['title']+" hasn't changed, skipping.\n")
					skippedPackages.append(pkg)
					repojson['packages'].append(prevPkgInfo) #Copy package info from previous repo.json
					continue
				else:
					underprint("Now updating: "+pkgbuild['info']['title'])
					zipPath = config["output_directory"]+"/zips/"+pkg+".zip"
					if os.path.exists(zipPath): # might not exist if it's a force update or CI update
						os.remove(zipPath)
		else: underprint("Now packaging: "+pkgbuild['info']['title'])
		manifest=open(pkg+"/manifest.install", 'w')

		print(str(len(pkgbuild['assets']))+" asset(s) detected")
		screenCount = 0
		for asset in pkgbuild['assets']:
			if asset['type'] == 'screenshot':
				screenCount += 1
			handleAsset(pkg, asset, manifest, screenCount=screenCount)

		pkginfo={ #Format package info.json
			# packages that describe the app itself
			'title': pkgbuild['info']['title'],
			'description': pkgbuild['info']['description'],
			'author': pkgbuild['info']['author'],
			'version': pkgbuild['info']['version'],
			'license': pkgbuild['info']['license'],
			'url': pkgbuild['info']['url'],
			'category': pkgbuild['info']['category'],
			'details': pkgbuild['info']['details'],
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

		# re-open the manifest, and ensure that there are no duplicate entries
		seen = set()
		entries = []
		with open(pkg+"/manifest.install", "r") as f:
			for line in f.readlines()[::-1]: # from bottom to top
				line = line.strip()
				if not line:
					continue
				# assume the first character is the type
				if line[2:] in seen:
					continue # skip already seen entries
				seen.add(line[3:])
				entries.append(line) # preserves the type
		# overwrite the manifest with the deduplicated entries
		with open(pkg+"/manifest.install", "w") as f:
			for line in entries[::-1]:
				f.write(line + "\n")
					
		print("manifest.install generated.")
		print("Package is "+str(get_size(pkg)//1024)+" KiB large.")

		# make the zip dir if it doesn't exist
		os.makedirs(config["output_directory"]+"/zips", exist_ok=True)
		outputZip = config["output_directory"]+"/zips/"+pkg+".zip"
		failedPkg = False
		# go through and zip only the files that we know for sure are in the manifest
		with zipfile.ZipFile(outputZip, "w", zipfile.ZIP_DEFLATED) as z:
			for line in entries[::-1]:
				line = line.strip()[3:]
				if os.path.isfile(pkg+"/"+line):
					z.write(pkg+"/"+line, line)
				else:
					print(f"ERROR: {line} is in the manifest, but does not exist at {pkg}/{line}")
					failedPackages.append(pkg)
					failedPkg = True
					break
			# add in the info.json and manifest.install
			z.write(pkg+"/info.json", "info.json")
			z.write(pkg+"/manifest.install", "manifest.install")
		if failedPkg:
			continue

		print("Package written to "+config["output_directory"]+"/zips/"+pkg+".zip")
		print("Zipped package is "+str(os.path.getsize(config["output_directory"]+"/zips/"+pkg+".zip")//1024)+" KiB large.")

		# copy over the manifest.install and info.json to the public directory
		os.makedirs(config["output_directory"]+'/packages/'+pkg, exist_ok=True)
		shutil.copyfile(pkg+'/info.json', config["output_directory"]+'/packages/'+pkg+'/info.json')
		shutil.copyfile(pkg+'/manifest.install', config["output_directory"]+'/packages/'+pkg+'/manifest.install')
		print("Copied info.json and manifest.install to public package folder")

		repo_extended_info={
			"name": pkgbuild['package'],
		}
		# add in all info.json info after the name
		repo_extended_info.update(pkginfo)

		#Attempt to read binary path from pkgbuild; otherwise, guess it.
		try: binaryPath=pkgbuild['info']['binary']
		except:
			if pkginfo['category']=="theme":
				print("INFO: binary path not specified. Category is theme, so autofilling \"none\".")
			else:
				broken=False
				for (dirpath, dirnames, filenames) in os.walk(pkg):
					for file in filenames:
						if file.endswith(tuple(config["valid_binary_extensions"])):
							binaryPath=os.path.join(dirpath,file)[os.path.join(dirpath,file).index("/"):]
							broken=True
							# make sure the filemagic of this isn't Zip
							with open(os.path.join(dirpath, file), "rb") as f:
								if f.read(2) == b"PK":
									print(f"ERROR: {file} is a zip file, not a binary. Check that the pkgbuild is extracting the zip file correctly.")
									failedPackages.append(pkg)
									failedPkg = True
									broken = False
									break
							break
						if broken: break
				if not broken: print("WARNING: "+pkgbuild['info']['title']+"'s binary path not specified in pkgbuild.json, and no binary found!")
				else: print("WARNING: binary path not specified in pkgbuild.json; using: "+binaryPath)
		if failedPkg:
			continue

		# add in the size of the extracted and zipped files
		repo_extended_info.update({ #repo.json has package info plus extended info
			'filesize': os.path.getsize(config["output_directory"]+"/zips/"+pkg+".zip")//1024,
			'extracted': get_size(pkg)//1024,
			'md5': hashlib.md5(open(config["output_directory"]+"/zips/"+pkg+".zip", "rb").read()).hexdigest(),
			'sha256': hashlib.sha256(open(config["output_directory"]+"/zips/"+pkg+".zip", "rb").read()).hexdigest(),
			'updated': str(datetime.utcfromtimestamp(os.path.getmtime(pkg+"/pkgbuild.json")).strftime('%Y-%m-%d')),
			# file birth time of the binary, if present, otherwise any file in the manifest
			'appCreated': str(datetime.utcfromtimestamp(os.stat(pkg+binaryPath).st_birthtime).strftime('%Y-%m-%d')) if binaryPath else str(datetime.utcfromtimestamp(os.stat(pkg+"/"+entries[0][3:]).st_birthtime).strftime('%Y-%m-%d')),
			'binary': binaryPath if binaryPath else "none",
			'screens': screenCount,
			'web_dls': -1, #TODO: get these counts from stats API
			'app_dls': -1 #TODO
		})

		repojson['packages'].append(repo_extended_info) #Append package info to repo.json
		print() #Console newline at end of package. for prettiness

	json.dump(repojson, open(config["output_directory"]+"/repo.json", "w"), indent=1) #Output repo.json
	print(config["output_directory"]+"/repo.json generated.")

	underprint("\nSUMMARY")
	print("Built "+str(len(pkg_dirs)-len(failedPackages)-len(skippedPackages))+" of "+str(len(pkg_dirs))+" packages.")
	if len(failedPackages)>0: print("Failed packages: "+str(failedPackages))
	if len(skippedPackages)>0: print("Skipped packages: "+str(skippedPackages))

	if cdnUrl:
		# write updated files to a txt file
		updatedPackages = set(pkg_dirs) - set(failedPackages) - set(skippedPackages)
		with open("updated_packages.txt", "w") as f:
			f.write(",".join(list(updatedPackages)))
			print("(CI Mode) Wrote updated packages string to updated_packages.txt")
	
	print("All done. Enjoy your new repo :)")

	# if we had any failed packages, exit with a non-zero status
	if len(failedPackages) > 0:
		sys.exit(1)

if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description="Spinarak: a libget package builder")
	parser.add_argument("-c", help="use the given CDN URL to download an existing repo.json")
	parser.add_argument("packages", nargs="*", help="list of packages to force rebuild, regardless of version")
	args = parser.parse_args()
	if args.c:
		cdnUrl = args.c
		print(f"INFO: Using {cdnUrl} as the CDN URL")
	if args.packages:
		print(f"INFO: Manually going to update {args.packages}")
		alwaysUpdate = set(args.packages)
	main()
