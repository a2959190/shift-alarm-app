[app]

title = 排班闹钟
package.name = shiftalarm
package.domain = org.shiftalarm
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 0.1
version.code = 1

# 依赖库（只写 pip 包名，json/calendar 是Python自带不用写）
requirements = python3,kivy==2.3.1,plyer==2.1.0,pyjnius==1.7.0

# 安卓权限
android.permissions = VIBRATE,WAKE_LOCK,RECEIVE_BOOT_COMPLETED,POST_NOTIFICATIONS

# 图标
icon.filename = icon.png

# 方向
orientation = portrait
fullscreen = 0

# 安卓版本
android.api = 34
android.minapi = 21
android.ndk = 27
android.build_tools = 34.0.0

# 接受 SDK 许可
android.accept_sdk_license = True

# 启用 AndroidX
android.enable_androidx = True

# Java 版本
android.java.source = 17

# 日志
log_level = 2

[buildozer]
log_level = 2
warn_on_root = 0
