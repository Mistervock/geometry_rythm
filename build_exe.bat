@echo off
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --onefile --name GeometryRhythm --paths core --add-data "core\fonts;fonts" --add-data "core\sounds;sounds" main.py
if exist build rmdir /s /q build
if exist GeometryRhythm.spec del GeometryRhythm.spec
echo.
echo Готово: dist\GeometryRhythm.exe — скопируйте его рядом с папками songs, data, images.
pause
