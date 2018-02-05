#!/usr/bin/python

import distutils
import hashlib
import os
import shutil
import subprocess
import sys

from distutils import dir_util

APK_NAME = "com.opentext.bluefield.apk"
EXPECTED_SHA256 = "02d8be9dbce2dc41934dd0f76055c613eafaedb96f537538fc55c0d988c98d64"
EXPECTED_VERSION = ""

OUTPUT_UNSIGNED_APK_NAME = "fcaplus.unsigned.apk"
OUTPUT_APK_NAME = "fcaplus.apk"

base_path = os.path.dirname(os.path.realpath(__file__))

apk_path = os.path.join(base_path, APK_NAME)
output_unsigned_apk_path = os.path.join(base_path, OUTPUT_UNSIGNED_APK_NAME)
output_apk_path = os.path.join(base_path, OUTPUT_APK_NAME)

orig_path = os.path.join(base_path, "orig/")
work_path = os.path.join(base_path, "work/")
patches_path = os.path.join(base_path, "patches/")
private_path = os.path.join(base_path, "private/")

keystore_path = os.path.join(private_path, "keystore.jks")

def hash_file(file):
	sha256 = hashlib.sha256()

	with open(file, 'rb') as f:
		while True:
			data = f.read(65536)
			if not data:
				break
			sha256.update(data)
	
	return sha256.hexdigest()

def read_file_as_text(file):
	with open(file, 'r') as f:
		return f.read()

def command_exists(command):
	with open(os.devnull, 'w') as devnull:
		rc = subprocess.call(command, stdout=devnull, stderr=devnull, shell=True)
		if rc == 0:
			return True
		else:
			return False

def run_command(command, stdout=None):
	rc = subprocess.call(command, stdout=stdout, shell=False)
	return rc

def build():
	# look for the apk and check its validity
	if not os.path.exists(apk_path):
		print("Couldn't find APK file %s to patch." % apk_path)
		sys.exit(1)
	
	if hash_file(APK_NAME) != EXPECTED_SHA256:
		print("APK file did not match expected SHA256 hash; it's probably the wrong version or a corrupt file.")
		sys.exit(1)

	# check that required tools exist
	if not command_exists("git --version"):
		print("Couldn't find git. Make sure you have git installed and located in your PATH.")
		sys.exit(1)

	if not command_exists("adb version"):
		print("Couldn't find adb. Make sure you have the Android SDK installed and its platform-tools directory located in your PATH.")
		sys.exit(1)

	if not command_exists("apksigner --version"):
		print("Couldn't find adb. Make sure you have the Android SDK installed and one of its build-tools directories located in your PATH.")
		sys.exit(1)

	if not command_exists("keytool -help"):
		print("Couldn't find keytool. Make sure you have the Java JDK installed and located in your PATH.")
		sys.exit(1)

	if not command_exists("apktool --version"):
		print("Couldn't find apktool. Make sure you have it installed and located in your PATH.")
		sys.exit(1)

	# found a valid apk, first clean up existing app data folders
	if os.path.exists(orig_path):
		shutil.rmtree(orig_path)

	if os.path.exists(work_path):
		shutil.rmtree(work_path)

	# create a private/ folder if needed
	if not os.path.exists(private_path):
		os.mkdir(private_path)

	# create a keystore if needed
	if not os.path.exists(keystore_path):
		rc = run_command([
			"keytool",
			"-genkey", "-v", "-keystore", keystore_path,
			"-storepass", "fcaplus", "-keypass", "fcaplus",
			"-dname", "CN=\"FCAPlus User\", OU=FCAPlus, O=FCAPlus, L=Unknown, ST=Unknown, C=Unknown"
		])
		if rc != 0:
			print("keytool gave return code %d, stopping!" % rc)
			sys.exit(1)

	# unpack it into the orig folder
	print("Decoding original APK with apktool...")
	rc = run_command([ "apktool", "d", "-o", orig_path, apk_path ])
	if rc != 0:
		print("apktool gave return code %d, stopping!" % rc)
		sys.exit(1)

	# copy the original files to the working folder so we can apply patches
	print("Copying extracted APK to working folder...")
	distutils.dir_util.copy_tree(orig_path, work_path)

	# create a git repo to keep track the patches
	rc = run_command([ "git", "-C", work_path, "init" ])
	if rc != 0:
		print("git gave return code %d, stopping!" % rc)
		sys.exit(1)

	gitignore = open(os.path.join(work_path, ".gitignore"), "w")
	gitignore.write("build/")
	gitignore.close()

	with open(os.devnull, 'w') as devnull:
		rc = run_command([ "git", "-C", work_path, "add", "." ], stdout=devnull)
		if rc != 0:
			print("git gave return code %d, stopping!" % rc)
			sys.exit(1)

		rc = run_command([ "git", "-C", work_path, "commit", "-m", "original code" ], stdout=devnull)
		if rc != 0:
			print("git gave return code %d, stopping!" % rc)
			sys.exit(1)

	# actually apply the patches
	for patch_folder_name in os.listdir(patches_path):
		if patch_folder_name == ".DS_Store":
			continue

		patch_path = os.path.join(patches_path, patch_folder_name)

		if not os.path.isdir(patch_path):
			print("Found unexpected file %s in patches folder, stopping!" % patch_folder_name)

		patch_desc_path = os.path.join(patch_path, "desc.txt")
		patch_changes_patch = os.path.join(patch_path, "changes.patch")

		desc = read_file_as_text(patch_desc_path)

		print("Applying patch '%s'..." % desc)

		# apply changes
		rc = run_command([ "git", "-C", work_path, "apply", patch_changes_patch ])
		if rc != 0:
			print("git gave return code %d, stopping!" % rc)
			sys.exit(1)

		# save as a commit (this way, future patches won't include previous changes)
		with open(os.devnull, 'w') as devnull:
			rc = run_command([ "git", "-C", work_path, "add", "." ], stdout=devnull)
			if rc != 0:
				print("git gave return code %d, stopping!" % rc)
				sys.exit(1)

		rc = run_command([ "git", "-C", work_path, "commit", "-m", desc ])
		if rc != 0:
			print("git gave return code %d, stopping!" % rc)
			sys.exit(1)

	package_and_sign()

def package_and_sign():
	# package the new apk
	rc = run_command(["apktool", "b", "-o", output_unsigned_apk_path, work_path])
	if rc != 0:
		print("apktool gave return code %d, stopping!" % rc)
		sys.exit(1)

	# sign the apk
	rc = run_command(["apksigner", "sign", "-ks", keystore_path, "--ks-pass", "pass:fcaplus", "--key-pass", "pass:fcaplus", "--out", output_apk_path, output_unsigned_apk_path])
	if rc != 0:
		print("apksigner gave return code %d, stopping!" % rc)
		sys.exit(1)

	print("Signed APK created at %s" % OUTPUT_APK_NAME)

def install(second_try=False):
	rc = run_command(["adb", "install", "-r", output_apk_path])
	if rc == 0:
		# it worked
		print("FCAPlus was successfully installed")
		return
	elif rc == 1:
		if not second_try:
			# try uninstalling the app and try again
			run_command(["adb", "uninstall", "com.opentext.bluefield"])
			run_command(["adb", "uninstall", "com.opentext.bluefieldpatch"])
			install(second_try=True)
		else:
			print("adb gave return code %d, stopping!" % rc)
			sys.exit(1)
	else:
		print("adb gave return code %d, stopping!" % rc)
		sys.exit(1)

def help():
	print("Usage: python patch.py [action], where action is one of:")
	print("* build - Build a patched FirstClass APK")
	print("* diff - Used to create a patch")
	print("* install - Build a patched FirstClass APK, and then use ADB to install it on a connected Android device")

action = "build"

if len(sys.argv) > 1:
	action = sys.argv[1]
else:
	print("No action specified, assuming 'build'.")

if action == "build":
	build()
elif action == "diff":
	print("diff doesn't work yet")
elif action == "help":
	help()
elif action == "install":
	build()
	install()
else:
	print("Unknown action '%s'!" % action)
	help()