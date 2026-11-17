@echo off
setlocal
cd /d "%~dp0\..\.."
echo [1/4] Installing Monn desktop dependencies...
py -m pip install -e ".[desktop]"
if errorlevel 1 goto :error
echo [2/4] Creating Monn Studio icon...
py scripts\create_studio_icon.py
if errorlevel 1 goto :error
echo [3/4] Building Windows desktop application...
py -m PyInstaller --noconfirm --clean packaging\windows\monn-studio.spec
if errorlevel 1 goto :error
echo [4/4] Creating Desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$exe=(Resolve-Path 'dist\MonnStudio.exe').Path; $desk=[Environment]::GetFolderPath('Desktop'); $shell=New-Object -ComObject WScript.Shell; $link=$shell.CreateShortcut((Join-Path $desk 'Monn Studio.lnk')); $link.TargetPath=$exe; $link.WorkingDirectory=(Split-Path $exe); $link.IconLocation=$exe; $link.Description='Monn Studio Game Creation Environment'; $link.Save()"
echo.
echo Build complete: dist\MonnStudio.exe
echo Desktop shortcut created: Monn Studio
echo Optional installer: install Inno Setup, then compile packaging\windows\MonnStudio.iss
pause
exit /b 0
:error
echo Build failed. Review the error above.
pause
exit /b 1
