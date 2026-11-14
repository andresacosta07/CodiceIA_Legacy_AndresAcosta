@echo off
REM Doble clic para iniciar el Copiloto de Modernizacion (Windows).
REM Comprueba el equipo, instala lo necesario la primera vez, levanta la app y abre el navegador.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py run.py %*
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    python run.py %*
  ) else (
    echo No se encontro Python. Instale Python 3.10 o superior desde https://www.python.org/downloads/ ^(marque "Add python.exe to PATH"^) y vuelva a hacer doble clic.
    pause
    exit /b 1
  )
)
if errorlevel 1 pause
