[app]
title = Jeff
package.name = jeff
package.domain = org.jefestar

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 0.1

requirements = python3,kivy

orientation = portrait
fullscreen = 0

# IcÃ´ne et image de dÃ©marrage optionnelles (dÃ©pose icon.png / presplash.png
# Ã  cÃ´tÃ© de ce fichier si tu veux les personnaliser, sinon laisse commentÃ©)
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

android.permissions =

android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
