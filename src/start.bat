@echo off
chcp 65001 >nul
title Warehouse Optimizer

echo ============================================================
echo   Warehouse Optimizer -- ABC Ari Kolonisi + Apriori
echo   Karaboga 2005 -- abc.erciyes.edu.tr
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/4] n8n Otomasyon Servisi baslatiliyor...
start "n8n Workflow Engine" cmd /k "n8n start"

timeout /t 5 /nobreak >nul

echo [2/4] Flask API baslatiliyor...
start "Flask API" cmd /k "cd backend && python app.py"

timeout /t 3 /nobreak >nul

echo [3/4] Frontend aciliyor...
start "" "%~dp0frontend\index.html"

echo [4/4] Hazir!
echo.
echo   API : http://localhost:5000/api/health
echo   Web : frontend/index.html
echo   n8n : http://localhost:5678
echo.
echo Kapatmak icin bu pencereleri kapatin.
pause