@echo off
REM Windows acilinca robot programi kendiliginden baslasin (Baslangic klasorune kucuk bir .bat koyar)
chcp 65001 >nul
set "HEDEF=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Masaustu Robot.bat"
> "%HEDEF%" echo @echo off
>> "%HEDEF%" echo cd /d "%~dp0"
>> "%HEDEF%" echo start "Masaustu Robot" /min baslat.bat
echo Tamam: Windows acilisinda robot otomatik baslayacak.
echo Kaldirmak icin su dosyayi sil: %HEDEF%
pause
