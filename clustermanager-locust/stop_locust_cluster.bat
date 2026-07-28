@echo off
echo Stopping all Locust processes...
taskkill /f /im python.exe 2>nul
taskkill /f /im pythonw.exe 2>nul
echo All Locust processes have been stopped.
timeout /t 2 >nul