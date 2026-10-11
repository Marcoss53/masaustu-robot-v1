@echo off
REM ==========================================================
REM  Masaustu Robot v1 - baslatici
REM  Ilk calistirmada sanal ortam (.venv) kurar ve paketleri yukler.
REM  Kullanim:  baslat.bat          (normal)
REM             baslat.bat --test   (donanim + API testi)
REM             baslat.bat --yazi   (klavyeden yazarak konus)
REM ==========================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo [Kurulum] Sanal ortam olusturuluyor...
    py -3.11 -m venv .venv 2>nul || python -m venv .venv
    if not exist ".venv\Scripts\python.exe" (
        echo [HATA] Python 3.11 bulunamadi. KURULUM.md - Adim 2'ye bak.
        pause
        exit /b 1
    )
)

if not exist ".venv\kurulum_tamam.txt" (
    echo [Kurulum] Paketler yukleniyor, ilk seferde birkac dakika surebilir...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [HATA] Paketler yuklenemedi. Internet baglantisini kontrol edip tekrar dene.
        pause
        exit /b 1
    )
    echo ok> ".venv\kurulum_tamam.txt"
)

if "%XAI_API_KEY%"=="" (
    echo [UYARI] XAI_API_KEY ortam degiskeni yok. Robot konusamaz. KURULUM.md - Adim 3.
)

".venv\Scripts\python.exe" robot.py %*
echo.
echo Program kapandi.
pause
