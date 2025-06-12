@echo off

@REM REM Сборка APK
@REM flet build apk --verbose

@REM REM Установка APK
adb install -r build\apk\app-release.apk

REM Запуск приложения
adb shell monkey -p ru.vegas.stockwatch -c android.intent.category.LAUNCHER 1

pause
