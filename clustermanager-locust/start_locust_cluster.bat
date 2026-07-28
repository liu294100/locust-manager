@echo off
setlocal enabledelayedexpansion

:: Default configuration
set DEFAULT_HOST=http://localhost:8080
set DEFAULT_WORKERS=4
set DEFAULT_LOCUST_FILE=locustfile.py
set DEFAULT_WEB_PORT=8089

:: Show help information
if "%~1"=="/?" goto :help
if "%~1"=="-h" goto :help
if "%~1"=="--help" goto :help

:: Initialize variables
set TARGET_HOST=%DEFAULT_HOST%
set WORKER_COUNT=%DEFAULT_WORKERS%
set LOCUST_FILE=%DEFAULT_LOCUST_FILE%
set WEB_PORT=%DEFAULT_WEB_PORT%

:: Parse arguments
:parse_loop
if "%~1"=="" goto :start_cluster

if "%~1"=="--host" set TARGET_HOST=%~2 & shift & shift & goto :parse_loop
if "%~1"=="-H" set TARGET_HOST=%~2 & shift & shift & goto :parse_loop
if "%~1"=="--workers" set WORKER_COUNT=%~2 & shift & shift & goto :parse_loop
if "%~1"=="-w" set WORKER_COUNT=%~2 & shift & shift & goto :parse_loop
if "%~1"=="--file" set LOCUST_FILE=%~2 & shift & shift & goto :parse_loop
if "%~1"=="-f" set LOCUST_FILE=%~2 & shift & shift & goto :parse_loop
if "%~1"=="--port" set WEB_PORT=%~2 & shift & shift & goto :parse_loop
if "%~1"=="-p" set WEB_PORT=%~2 & shift & shift & goto :parse_loop

shift
goto :parse_loop

:help
echo.
echo ========================================
echo    Locust Distributed Cluster Starter
echo ========================================
echo.
echo Usage:
echo   start_locust_cluster.bat [options]
echo.
echo Options:
echo   -H, --host HOST      Target host URL (default: %DEFAULT_HOST%)
echo   -w, --workers NUM    Number of worker processes (default: %DEFAULT_WORKERS%)
echo   -f, --file FILE      Locust script file (default: %DEFAULT_LOCUST_FILE%)
echo   -p, --port PORT      Web interface port (default: %DEFAULT_WEB_PORT%)
echo   -h, --help          Show this help message
echo.
echo Examples:
echo   start_locust_cluster.bat --host http://api.example.com --workers 4
echo   start_locust_cluster.bat -H http://test.com -w 2 -f my_test.py
echo.
goto :eof

:start_cluster
echo ========================================
echo    Starting Locust Distributed Cluster
echo ========================================
echo Target Host: %TARGET_HOST%
echo Worker Count: %WORKER_COUNT%
echo Locust File: %LOCUST_FILE%
echo Web Port: %WEB_PORT%
echo ========================================
echo.

:: Check if file exists
if not exist "%LOCUST_FILE%" (
    echo ERROR: Locust file '%LOCUST_FILE%' not found!
    pause
    exit /b 1
)

echo Step 1: Starting Master node...
start "Locust Master" cmd /k "locust -f %LOCUST_FILE% --master --host=%TARGET_HOST% --web-port=%WEB_PORT%"
timeout /t 3 >nul

echo Step 2: Starting %WORKER_COUNT% worker processes...
for /L %%i in (1,1,%WORKER_COUNT%) do (
    echo Starting Worker %%i...
    start "Locust Worker %%i" cmd /k "locust -f %LOCUST_FILE% --worker --master-host=localhost"
    if %%i neq %WORKER_COUNT% timeout /t 1 >nul
)

echo.
echo ========================================
echo Cluster started successfully!
echo Web Interface: http://localhost:%WEB_PORT%
echo Target Host: %TARGET_HOST%
echo Worker Count: %WORKER_COUNT%
echo ========================================
echo.
pause