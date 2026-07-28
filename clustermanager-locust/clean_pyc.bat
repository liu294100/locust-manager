@echo off
chcp 65001 >nul 2>&1
echo Cleaning __pycache__ and .pyc files...

for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        rd /s /q "%%d"
        echo   Removed: %%d
    )
)

del /s /q *.pyc >nul 2>&1

echo Done.
