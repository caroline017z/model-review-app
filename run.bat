@echo off
title 38DN VP Model Review
echo.
echo  ========================================
echo   38DN VP Pricing Model Review Tool
echo  ========================================
echo.
echo  Opening http://localhost:8501 ...
echo  Keep this window open while using the app.
echo  Press Ctrl+C to stop.
echo.
start http://localhost:8501
python -m streamlit run "%~dp0app.py" --server.port 8501 --server.headless true
pause
