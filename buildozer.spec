[app]
title = 排班闹钟
package.name = shiftalarm
package.domain = org.shiftalarm
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 0.1
version.code = 1
requirements = python3,kivy==2.3.1,plyer
android.permissions = VIBRATE,WAKE_LOCK,RECEIVE_BOOT_COMPLETED,POST_NOTIFICATIONS
icon.filename = icon.png
orientation = portrait
fullscreen = 0
android.api = 34
android.minapi = 21
android.ndk = 27
android.build_tools = 34.0.0
android.accept_sdk_license = True
android.enable_androidx = True
android.java.source = 17
log_level = 2

[buildozer]
log_level = 2
warn_on_root = 0
