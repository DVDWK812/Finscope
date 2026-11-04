@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_local.ps1" -Port 8511
pause
