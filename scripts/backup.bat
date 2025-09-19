@echo off
REM Docker Volume Backup Script for Windows
REM This script creates backups of all persistent Docker volumes

setlocal enabledelayedexpansion

REM Configuration
if "%BACKUP_DIR%"=="" set BACKUP_DIR=.\backups
if "%COMPOSE_PROJECT_NAME%"=="" set COMPOSE_PROJECT_NAME=docker-deployment

REM Get timestamp
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "TIMESTAMP=%dt:~0,4%%dt:~4,2%%dt:~6,2%_%dt:~8,2%%dt:~10,2%%dt:~12,2%"

echo [%date% %time%] Starting Docker volume backup process

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running
    exit /b 1
)

REM Create backup directory
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Create backup log
echo Backup started at %date% %time% > "%BACKUP_DIR%\backup_%TIMESTAMP%.log"

REM List of volumes to backup
set volumes=student_reports graded_reports output_data app_logs

REM Backup each volume
for %%v in (%volumes%) do (
    echo [%date% %time%] Backing up volume: %%v
    
    docker run --rm -v "%COMPOSE_PROJECT_NAME%_%%v:/data:ro" -v "%cd%\%BACKUP_DIR%:/backup" alpine:latest tar czf "/backup/%%v_%TIMESTAMP%.tar.gz" -C /data .
    
    if errorlevel 1 (
        echo ERROR: Failed to backup %%v
    ) else (
        echo Successfully backed up %%v
        echo %BACKUP_DIR%\%%v_%TIMESTAMP%.tar.gz >> "%BACKUP_DIR%\backup_%TIMESTAMP%.log"
    )
)

REM Create manifest file
(
echo {
echo     "timestamp": "%TIMESTAMP%",
echo     "date": "%date% %time%",
echo     "volumes": [
echo         "student_reports",
echo         "graded_reports", 
echo         "output_data",
echo         "app_logs"
echo     ],
echo     "backup_dir": "%BACKUP_DIR%",
echo     "compose_project": "%COMPOSE_PROJECT_NAME%"
echo }
) > "%BACKUP_DIR%\manifest_%TIMESTAMP%.json"

echo [%date% %time%] Backup process completed. Manifest created: %BACKUP_DIR%\manifest_%TIMESTAMP%.json

REM Clean up old backups (keep last 7 days)
forfiles /p "%BACKUP_DIR%" /m *.tar.gz /d -7 /c "cmd /c del @path" 2>nul
forfiles /p "%BACKUP_DIR%" /m *.log /d -7 /c "cmd /c del @path" 2>nul
forfiles /p "%BACKUP_DIR%" /m manifest_*.json /d -7 /c "cmd /c del @path" 2>nul

echo [%date% %time%] Old backups cleaned up (kept last 7 days)
echo Backup completed successfully!