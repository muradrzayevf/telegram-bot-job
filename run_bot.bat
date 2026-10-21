@echo off
cd /d "%~dp0"
set PY=C:\Users\rzaye\AppData\Local\Programs\Python\Python313\python.exe
if not exist "%PY%" set PY=python
"%PY%" bot.py %*
pause
