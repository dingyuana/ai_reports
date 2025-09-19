@echo off
REM Health Check Script for Docker Container (Windows)
REM This script performs comprehensive health checks for the grading system

setlocal enabledelayedexpansion

REM Configuration
if "%HEALTH_CHECK_HOST%"=="" set HEALTH_CHECK_HOST=localhost
if "%HEALTH_CHECK_PORT%"=="" set HEALTH_CHECK_PORT=8000
if "%HEALTH_CHECK_TIMEOUT%"=="" set HEALTH_CHECK_TIMEOUT=10
if "%HEALTH_CHECK_VERBOSE%"=="" set HEALTH_CHECK_VERBOSE=false

set HOST=%HEALTH_CHECK_HOST%
set PORT=%HEALTH_CHECK_PORT%
set TIMEOUT=%HEALTH_CHECK_TIMEOUT%
set VERBOSE=%HEALTH_CHECK_VERBOSE%

if "%1"=="" goto basic_check
if "%1"=="help" goto show_help
if "%1"=="-h" goto show_help
if "%1"=="--help" goto show_help

goto %1

:basic_check
if "%VERBOSE%"=="true" echo [%date% %time%] Checking basic health endpoint...

REM Try using curl first
curl --version >nul 2>&1
if not errorlevel 1 (
    for /f %%i in ('curl -s -o nul -w "%%{http_code}" --max-time %TIMEOUT% "http://%HOST%:%PORT%/health" 2^>nul') do set response=%%i
    if "!response!"=="200" (
        if "%VERBOSE%"=="true" echo [%date% %time%] Basic health check passed
        exit /b 0
    ) else (
        echo ERROR: Basic health check failed with HTTP !response!
        exit /b 1
    )
)

REM Fallback to Python if curl not available
python --version >nul 2>&1
if not errorlevel 1 (
    python -c "import requests; import sys; response = requests.get('http://%HOST%:%PORT%/health', timeout=%TIMEOUT%); sys.exit(0 if response.status_code == 200 else 1)" 2>nul
    if not errorlevel 1 (
        if "%VERBOSE%"=="true" echo [%date% %time%] Basic health check passed
        exit /b 0
    ) else (
        echo ERROR: Basic health check failed
        exit /b 1
    )
)

echo ERROR: Neither curl nor Python available for health check
exit /b 1

:detailed
if "%VERBOSE%"=="true" echo [%date% %time%] Checking detailed health endpoint...

python --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Python not available, skipping detailed health check
    exit /b 0
)

python -c "
import requests
import json
import sys

try:
    response = requests.get('http://%HOST%:%PORT%/api/health', timeout=%TIMEOUT%)
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'healthy':
            print('Detailed health check passed')
            sys.exit(0)
        else:
            print('Detailed health check failed: unhealthy status')
            sys.exit(1)
    else:
        print(f'Detailed health check failed with HTTP {response.status_code}')
        sys.exit(1)
except Exception as e:
    print(f'Detailed health check failed: {e}')
    sys.exit(1)
" 2>nul

exit /b %errorlevel%

:ready
:readiness
if "%VERBOSE%"=="true" echo [%date% %time%] Checking readiness endpoint...

python --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Python not available, skipping readiness check
    exit /b 0
)

python -c "
import requests
import sys

try:
    response = requests.get('http://%HOST%:%PORT%/api/health/ready', timeout=%TIMEOUT%)
    if response.status_code == 200:
        print('Readiness check passed')
        sys.exit(0)
    else:
        print(f'Readiness check failed with HTTP {response.status_code}')
        sys.exit(1)
except Exception as e:
    print(f'Readiness check failed: {e}')
    sys.exit(1)
" 2>nul

exit /b %errorlevel%

:live
:liveness
if "%VERBOSE%"=="true" echo [%date% %time%] Checking liveness endpoint...

REM Try using curl first
curl --version >nul 2>&1
if not errorlevel 1 (
    for /f %%i in ('curl -s -o nul -w "%%{http_code}" --max-time %TIMEOUT% "http://%HOST%:%PORT%/api/health/live" 2^>nul') do set response=%%i
    if "!response!"=="200" (
        if "%VERBOSE%"=="true" echo [%date% %time%] Liveness check passed
        exit /b 0
    ) else (
        echo ERROR: Liveness check failed with HTTP !response!
        exit /b 1
    )
)

REM Fallback to basic check
goto basic_check

:all
call :basic_check
if errorlevel 1 exit /b 1

call :detailed
if errorlevel 1 exit /b 1

call :readiness
if errorlevel 1 exit /b 1

call :liveness
if errorlevel 1 exit /b 1

echo All health checks passed
exit /b 0

:show_help
echo Health Check Script for Grading System (Windows)
echo.
echo Usage: %0 [CHECK_TYPE]
echo.
echo Check Types:
echo     basic       Basic health check (default)
echo     detailed    Detailed health check with system info
echo     ready       Readiness probe check
echo     live        Liveness probe check
echo     all         Run all health checks
echo.
echo Environment Variables:
echo     HEALTH_CHECK_HOST       Host to check (default: localhost)
echo     HEALTH_CHECK_PORT       Port to check (default: 8000)
echo     HEALTH_CHECK_TIMEOUT    Request timeout (default: 10)
echo     HEALTH_CHECK_VERBOSE    Enable verbose output (true/false)
echo.
echo Examples:
echo     %0                      # Basic health check
echo     %0 detailed             # Detailed health check
echo     %0 all                  # All checks
echo.
echo Exit Codes:
echo     0   Health check passed
echo     1   Health check failed
echo.
goto :eof