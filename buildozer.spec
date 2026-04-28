[app]
title = The Ghost Architect
package.name = ghostarchitect
package.domain = org.ghost
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0

requirements = python3,kivy==2.3.0,kivymd,pyjnius,numpy,psutil,sounddevice

android.permissions = VIBRATE,RECORD_AUDIO,FOREGROUND_SERVICE,REQUEST_IGNORE_BATTERY_OPTIMIZATIONS

android.api = 33
android.minapi = 26
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
