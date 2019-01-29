# FCAPlus
A series of patches to improve the FirstClass Android client. 

## Usage
### Requirements
You should make sure you have all of the following tools, and that they are located in your PATH.
* Java JDK
* Android SDK (make sure both the `platform-tools` folder AND one of the `build-tools` subfolders are in your path. Specifically, you need to make sure `adb` and `apksigner` are both in your path)
* Git
* [apktool](https://ibotpeaches.github.io/Apktool/)
* FirstClass Android client (to patch; tested with version 1.5.143.13451)

### Instructions
You will need to have a copy of the original FirstClass APK, which you can get from your Android phone. (I personally use [MyAppSharer](https://play.google.com/store/apps/details?id=com.yschi.MyAppSharer) to do this) Place that APK in the directory containing `patch.py`, and make sure it's named `com.opentext.bluefield.apk`.

Once you've done that, connect your phone to your computer and run `python patch.py install`. All of the patches in the `patches/` folder will automatically be applied to the APK, and the newly-created APK will then be installed on your phone.

## Creating patches
Make sure you've built the patched app at least once before you do this!

After building the patched app, you will notice a new `work/` folder. Make your changes in this folder. To test your changes, use `python patch.py build_test` and `python patch.py install_test`. **Do NOT use the non-`_test` versions of these commands, as this will rebuild the app using only the patches in the `patches/` folder, and will erase your changes.**

Once you've completed your changes, you can run `python patch.py create_patch`, which will ask you for the name of the patch's directory (make sure it follows the same format as all of the others!) and a short description of the patch. This will create a new directory under the `patches/` folder, which can then be submitted as a pull request.