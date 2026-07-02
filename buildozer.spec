[app]

# 应用名称
title = 排班闹钟

# 包名（唯一标识，像身份证号）
package.name = shiftalarm
package.domain = org.shiftalarm

# 源码路径
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

# 版本号
version = 0.1
version.code = 1

# 依赖库（打包时会自动下载）
requirements = python3,kivy==2.3.1,plyer,json,calendar

# 权限（安卓需要的）
android.permissions = VIBRATE,WAKE_LOCK,RECEIVE_BOOT_COMPLETED,POST_NOTIFICATIONS

# 图标
icon.filename = icon.png

# 方向：portrait=竖屏, landscape=横屏, all=自适应
orientation = portrait

# 全屏
fullscreen = 0

# 最低安卓版本
android.minapi = 21

# 目标安卓版本
android.api = 34

# NDK 版本
android.ndk = 27c

# SDK 版本
android.sdk = 34

# 是否启用 AndroidX（新版安卓必须）
android.enable_androidx = True

# Java 版本
android.java.source = 17

# 日志级别
log_level = 2

# 是否使用默认的 Gradle 构建
android.gradle_dependencies = ''

[buildozer]

# 日志级别
log_level = 2

# 每次打包前是否先更新 SDK/NDK
warn_on_root = 0
