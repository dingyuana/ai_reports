@echo off
REM Docker Volume Restore Script for Windows
REM This script restores Docker volumes from backup files

setlocal enabledelayedexpansion

REM Configuration
if "%BACKUP_DIR%"=="" set BACKUP_DIR=.\backups
if "%COMPOSE_PROJECT_NAME%"=="" set COMPOSE_PROJECT_NAME=docker-deployment

if "%1"=="" goto show_help
if "%1"=="help" goto show_help
if "%1"=="-h" goto show_help
if "%1"=="--help" goto show_help

goto %1

:list
echo Available backups in %BACKUP_DIR%:
if not exist "%BACKUP_DIR%" (
    echo ERROR: Backup directory does not exist: %BACKUP_DIR%
    exit /b 1
)

for %%f in ("%BACKUP_DIR%\manifest_*.json") do (
    if exist "%%f" (
        set "manifest=%%f"
        for /f "tokens=2 delims=_." %%t in ("%%~nf") do set "timestamp=%%t"
        echo   Timestamp: !timestamp!
        echo   Manifest: %%f
        echo   ---
    )
)
goto :eof

:restore-all
if "%2"=="" (
    echo ERROR: restore-all requires a timestamp argument
    goto show_help
)

set "timestamp=%2"
set "manifest_file=%BACKUP_DIR%\manifest_%timestamp%.json"

if not exist "%manifest_file%" (
    echo ERROR: Manifest file not found: %manifest_file%
    exit /b 1
)

echo [%date% %time%] Restoring all volumes from timestamp: %timestamp%

REM Stop containers
echo Stopping containers...
docker-compose down 2>nul

REM Restore each volume
set volumes=student_reports graded_reports output_data app_logs

for %%v in (%volumes%) do (
    call :restore_volume %%v %timestamp%
)

echo [%date% %time%] All volumes restored from timestamp: %timestamp%
goto :eof

:restore-volume
if "%2"=="" (
    echo ERROR: restore-volume requires volume name and timestamp arguments
    goto show_help
)

set "volume_name=%1"
set "timestamp=%2"
set "backup_file=%BACKUP_DIR%\%volume_name%_%timestamp%.tar.gz"

if not exist "%backup_file%" (
    echo ERROR: Backup file not found: %backup_file%
    exit /b 1
)

echo [%date% %time%] Restoring volume: %volume_name% from %backup_file%

REM Stop containers
docker-compose down 2>nul

REM Remove existing volume
docker volume rm "%COMPOSE_PROJECT_NAME%_%volume_name%" 2>nul

REM Create new volume
docker volume create "%COMPOSE_PROJECT_NAME%_%volume_name%"

REM Restore data to volume
docker run --rm -v "%COMPOSE_PROJECT_NAME%_%volume_name%:/data" -v "%cd%\%BACKUP_DIR%:/backup:ro" alpine:latest tar xzf "/backup/%volume_name%_%timestamp%.tar.gz" -C /data

if errorlevel 1 (
    echo ERROR: Failed to restore %volume_name%
    exit /b 1
) else (
    echo Successfully restored %volume_name%
)
goto :eof

:verify
if "%2"=="" (
    echo ERROR: verify requires a timestamp argument
    goto show_help
)

set "timestamp=%2"
set "manifest_file=%BACKUP_DIR%\manifest_%timestamp%.json"

if not exist "%manifest_file%" (
    echo ERROR: Manifest file not found: %manifest_file%
    exit /b 1
)

echo [%date% %time%] Verifying backup integrity for timestamp: %timestamp%

set volumes=student_reports graded_reports output_data app_logs
set error_found=0

for %%v in (%volumes%) do (
    set "backup_file=%BACKUP_DIR%\%%v_%timestamp%.tar.gz"
    if not exist "!backup_file!" (
        echo ERROR: Missing backup file: !backup_file!
        set error_found=1
    )
)

if %error_found%==1 (
    echo Backup integrity check failed
    exit /b 1
) else (
    echo Backup integrity verified successfully
)
goto :eof

:show_help
echo Docker Volume Restore Script for Windows
echo.
echo Usage: %0 COMMAND [ARGS]
echo.
echo Commands:
echo     list                                List available backups
echo     restore-all TIMESTAMP              Restore all volumes from a backup timestamp
echo     restore-volume VOLUME TIMESTAMP    Restore a specific volume from backup
echo     verify TIMESTAMP                   Verify backup integrity
echo.
echo Environment Variables:
echo     BACKUP_DIR          Backup directory path (default: .\backups)
echo     COMPOSE_PROJECT_NAME Docker Compose project name (default: docker-deployment)
echo.
echo Examples:
echo     %0 list
echo     %0 restore-all 20231201_143022
echo     %0 restore-volume student_reports 20231201_143022
echo     %0 verify 20231201_143022
echo.
goto :eof