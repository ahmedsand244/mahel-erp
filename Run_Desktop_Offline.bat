@echo off
title Al-Namaa ERP Desktop (100% Offline Local Mode)
echo Starting Al-Namaa ERP in 100%% Local Offline Mode (No Internet Required)...
cd /d "%~dp0"
python desktop_app.py local
pause
