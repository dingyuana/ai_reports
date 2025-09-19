@echo off
REM SSL Certificate Generation Script for Windows
REM This script generates self-signed SSL certificates for development/testing

setlocal enabledelayedexpansion

REM Configuration
set SSL_DIR=.\ssl
set CERT_FILE=%SSL_DIR%\cert.pem
set KEY_FILE=%SSL_DIR%\key.pem
set DAYS=365
set COUNTRY=CN
set STATE=Beijing
set CITY=Beijing
set ORG=Grading System
set OU=IT Department
set CN=localhost

if "%1"=="" goto show_help
if "%1"=="help" goto show_help
if "%1"=="-h" goto show_help
if "%1"=="--help" goto show_help

goto %1

:generate
echo [%date% %time%] Generating self-signed SSL certificate...

REM Check if OpenSSL is available
openssl version >nul 2>&1
if errorlevel 1 (
    echo ERROR: OpenSSL is not installed or not in PATH
    echo Please install OpenSSL from https://slproweb.com/products/Win32OpenSSL.html
    exit /b 1
)

REM Create SSL directory
if not exist "%SSL_DIR%" mkdir "%SSL_DIR%"

REM Generate private key
openssl genrsa -out "%KEY_FILE%" 2048
if errorlevel 1 (
    echo ERROR: Failed to generate private key
    exit /b 1
)

REM Generate certificate
openssl req -new -x509 -key "%KEY_FILE%" -out "%CERT_FILE%" -days %DAYS% -subj "/C=%COUNTRY%/ST=%STATE%/L=%CITY%/O=%ORG%/OU=%OU%/CN=%CN%"
if errorlevel 1 (
    echo ERROR: Failed to generate certificate
    exit /b 1
)

echo [%date% %time%] Self-signed certificate generated successfully
echo Certificate: %CERT_FILE%
echo Private key: %KEY_FILE%
echo Valid for: %DAYS% days
goto :eof

:generate-san
echo [%date% %time%] Generating SSL certificate with Subject Alternative Names...

REM Check if OpenSSL is available
openssl version >nul 2>&1
if errorlevel 1 (
    echo ERROR: OpenSSL is not installed or not in PATH
    echo Please install OpenSSL from https://slproweb.com/products/Win32OpenSSL.html
    exit /b 1
)

REM Create SSL directory
if not exist "%SSL_DIR%" mkdir "%SSL_DIR%"

REM Create config file for SAN
(
echo [req]
echo default_bits = 2048
echo prompt = no
echo default_md = sha256
echo distinguished_name = dn
echo req_extensions = v3_req
echo.
echo [dn]
echo C=%COUNTRY%
echo ST=%STATE%
echo L=%CITY%
echo O=%ORG%
echo OU=%OU%
echo CN=%CN%
echo.
echo [v3_req]
echo basicConstraints = CA:FALSE
echo keyUsage = nonRepudiation, digitalSignature, keyEncipherment
echo subjectAltName = @alt_names
echo.
echo [alt_names]
echo DNS.1 = localhost
echo DNS.2 = *.localhost
echo DNS.3 = 127.0.0.1
echo IP.1 = 127.0.0.1
echo IP.2 = ::1
) > "%SSL_DIR%\cert.conf"

REM Generate private key
openssl genrsa -out "%KEY_FILE%" 2048
if errorlevel 1 (
    echo ERROR: Failed to generate private key
    exit /b 1
)

REM Generate certificate signing request
openssl req -new -key "%KEY_FILE%" -out "%SSL_DIR%\cert.csr" -config "%SSL_DIR%\cert.conf"
if errorlevel 1 (
    echo ERROR: Failed to generate certificate signing request
    exit /b 1
)

REM Generate certificate
openssl x509 -req -in "%SSL_DIR%\cert.csr" -signkey "%KEY_FILE%" -out "%CERT_FILE%" -days %DAYS% -extensions v3_req -extfile "%SSL_DIR%\cert.conf"
if errorlevel 1 (
    echo ERROR: Failed to generate certificate
    exit /b 1
)

REM Clean up
del "%SSL_DIR%\cert.csr" "%SSL_DIR%\cert.conf"

echo [%date% %time%] Certificate with SAN generated successfully
echo Certificate: %CERT_FILE%
echo Private key: %KEY_FILE%
echo Valid for: %DAYS% days
goto :eof

:verify
if not exist "%CERT_FILE%" (
    echo ERROR: Certificate file not found: %CERT_FILE%
    exit /b 1
)

if not exist "%KEY_FILE%" (
    echo ERROR: Private key file not found: %KEY_FILE%
    exit /b 1
)

echo [%date% %time%] Verifying certificate...

REM Check certificate validity
openssl x509 -in "%CERT_FILE%" -text -noout | findstr /C:"Subject:" /C:"Issuer:" /C:"Not Before:" /C:"Not After:" /C:"DNS:" /C:"IP Address:"

echo [%date% %time%] Certificate verification completed
goto :eof

:info
if not exist "%CERT_FILE%" (
    echo ERROR: Certificate file not found: %CERT_FILE%
    exit /b 1
)

echo [%date% %time%] Certificate information:
openssl x509 -in "%CERT_FILE%" -text -noout
goto :eof

:show_help
echo SSL Certificate Generation Script for Windows
echo.
echo Usage: %0 COMMAND
echo.
echo Commands:
echo     generate        Generate self-signed certificate
echo     generate-san    Generate certificate with Subject Alternative Names
echo     verify          Verify existing certificate
echo     info            Show certificate information
echo.
echo Examples:
echo     %0 generate                     # Generate basic self-signed certificate
echo     %0 generate-san                 # Generate certificate with SAN
echo     %0 verify                      # Verify existing certificate
echo     %0 info                        # Show certificate information
echo.
echo Note: This script requires OpenSSL to be installed and available in PATH
echo Download from: https://slproweb.com/products/Win32OpenSSL.html
echo.
goto :eof