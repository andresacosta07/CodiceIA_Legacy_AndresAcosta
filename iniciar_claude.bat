@echo off
REM Igual que iniciar.bat pero arranca con "Claude via suscripcion" (CLI de Claude Code, sin clave de API).
cd /d "%~dp0"
call iniciar.bat --claude %*
