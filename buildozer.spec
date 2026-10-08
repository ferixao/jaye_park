[app]
title = Jaye Park
package.name = jayepark
package.domain = org.jayepark
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,db
version = 1.0.0
requirements = python3,kivy==2.3.0,kivymd==1.0.2,pillow,arabic-reshaper
orientation = portrait
fullscreen = 0
android.api = 31
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.presplash_color = #FF8800
android.logcat_filters = *:S python:D
p4a.bootstrap = sdl2
p4a.branch = master
