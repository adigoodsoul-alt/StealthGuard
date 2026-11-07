@echo off
chcp 65001 >nul
title StealthGuard — Аварийное восстановление видимости
echo ========================================================
echo   StealthGuard — Аварийное восстановление видимости
echo ========================================================
echo.

:: 1. Сброс маски скрытия дисков в реестре
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDrives /f >nul 2>nul
echo [OK] Маска скрытия дисков (NoDrives) успешно удалена из реестра.

:: 2. Восстановление боковой панели навигации Проводника
reg add "HKCU\Software\Classes\CLSID\{F5FB2C77-0E2F-4A16-A381-3E560C68BC83}" /v "System.IsPinnedToNameSpaceTree" /t REG_DWORD /d 1 /f >nul 2>nul
echo [OK] Отображение дисков в боковой панели навигации Проводника включено.

:: 3. Размонтирование возможных виртуальных дисков-приманок
for %%D in (W V U T S R Q P O N M L K J I H G F E D) do (
    subst %%D: /d >nul 2>nul
)
echo [OK] Виртуальные диски-приманки (subst) отмонтированы.

echo.
:: 4. Восстановление атрибутов файлов
set /p TARGET_PATH="Введите путь к защищавшейся папке или диску для возврата видимости (например, Y:\Secret или Y:\) или нажмите Enter для пропуска: "
if not "%TARGET_PATH%"=="" (
    echo Снятие атрибутов System и Hidden с %TARGET_PATH%...
    attrib -s -h "%TARGET_PATH%" >nul 2>nul
    attrib -s -h "%TARGET_PATH%\*" /s /d >nul 2>nul
    
    :: Возврат системных атрибутов служебным файлам Windows
    for /r "%TARGET_PATH%" %%F in (desktop.ini thumbs.db) do (
        if exist "%%F" attrib +s +h "%%F" >nul 2>nul
    )
    echo [OK] Атрибуты видимости файлов и папок восстановлены (системные файлы снова скрыты).
)

echo.
:: 5. Перезапуск Проводника Windows для применения изменений
echo Перезапуск Проводника Windows...
taskkill /f /im explorer.exe >nul 2>nul
timeout /t 1 /nobreak >nul
start explorer.exe
echo.
echo ========================================================
echo [ГОТОВО] Все настройки проводника и видимость восстановлены!
echo ========================================================
echo.
pause
