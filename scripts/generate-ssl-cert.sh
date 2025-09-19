#!/bin/bash

# SSL Certificate Generation Script
# This script generates self-signed SSL certificates for development/testing

set -e

# Configuration
SSL_DIR="./ssl"
CERT_FILE="$SSL_DIR/cert.pem"
KEY_FILE="$SSL_DIR/key.pem"
DAYS=365
COUNTRY="CN"
STATE="Beijing"
CITY="Beijing"
ORG="Grading System"
OU="IT Department"
CN="localhost"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Function to generate self-signed certificate
generate_self_signed() {
    log "Generating self-signed SSL certificate..."
    
    # Create SSL directory
    mkdir -p "$SSL_DIR"
    
    # Generate private key
    openssl genrsa -out "$KEY_FILE" 2048
    
    # Generate certificate
    openssl req -new -x509 -key "$KEY_FILE" -out "$CERT_FILE" -days "$DAYS" -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$OU/CN=$CN"
    
    # Set proper permissions
    chmod 600 "$KEY_FILE"
    chmod 644 "$CERT_FILE"
    
    log "Self-signed certificate generated successfully"
    log "Certificate: $CERT_FILE"
    log "Private key: $KEY_FILE"
    log "Valid for: $DAYS days"
}

# Function to generate certificate with SAN (Subject Alternative Names)
generate_with_san() {
    log "Generating SSL certificate with Subject Alternative Names..."
    
    # Create SSL directory
    mkdir -p "$SSL_DIR"
    
    # Create config file for SAN
    cat > "$SSL_DIR/cert.conf" << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=$COUNTRY
ST=$STATE
L=$CITY
O=$ORG
OU=$OU
CN=$CN

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
DNS.3 = 127.0.0.1
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

    # Generate private key
    openssl genrsa -out "$KEY_FILE" 2048
    
    # Generate certificate signing request
    openssl req -new -key "$KEY_FILE" -out "$SSL_DIR/cert.csr" -config "$SSL_DIR/cert.conf"
    
    # Generate certificate
    openssl x509 -req -in "$SSL_DIR/cert.csr" -signkey "$KEY_FILE" -out "$CERT_FILE" -days "$DAYS" -extensions v3_req -extfile "$SSL_DIR/cert.conf"
    
    # Clean up
    rm "$SSL_DIR/cert.csr" "$SSL_DIR/cert.conf"
    
    # Set proper permissions
    chmod 600 "$KEY_FILE"
    chmod 644 "$CERT_FILE"
    
    log "Certificate with SAN generated successfully"
    log "Certificate: $CERT_FILE"
    log "Private key: $KEY_FILE"
    log "Valid for: $DAYS days"
}

# Function to verify certificate
verify_certificate() {
    if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
        error "Certificate files not found"
        return 1
    fi
    
    log "Verifying certificate..."
    
    # Check certificate validity
    openssl x509 -in "$CERT_FILE" -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After:|DNS:|IP Address:)"
    
    # Verify private key matches certificate
    cert_modulus=$(openssl x509 -noout -modulus -in "$CERT_FILE" | openssl md5)
    key_modulus=$(openssl rsa -noout -modulus -in "$KEY_FILE" | openssl md5)
    
    if [ "$cert_modulus" = "$key_modulus" ]; then
        log "Certificate and private key match"
    else
        error "Certificate and private key do not match"
        return 1
    fi
    
    log "Certificate verification completed"
}

# Function to show certificate info
show_info() {
    if [ ! -f "$CERT_FILE" ]; then
        error "Certificate file not found: $CERT_FILE"
        return 1
    fi
    
    log "Certificate information:"
    openssl x509 -in "$CERT_FILE" -text -noout
}

# Help function
show_help() {
    cat << EOF
SSL Certificate Generation Script

Usage: $0 [OPTIONS] COMMAND

Commands:
    generate        Generate self-signed certificate
    generate-san    Generate certificate with Subject Alternative Names
    verify          Verify existing certificate
    info            Show certificate information

Options:
    -h, --help      Show this help message
    -d, --days      Certificate validity in days (default: 365)
    -c, --cn        Common Name (default: localhost)
    --country       Country code (default: CN)
    --state         State (default: Beijing)
    --city          City (default: Beijing)
    --org           Organization (default: Grading System)

Examples:
    $0 generate                     # Generate basic self-signed certificate
    $0 generate-san                 # Generate certificate with SAN
    $0 -d 730 generate             # Generate certificate valid for 2 years
    $0 --cn example.com generate   # Generate certificate for example.com
    $0 verify                      # Verify existing certificate
    $0 info                        # Show certificate information

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--days)
            DAYS="$2"
            shift 2
            ;;
        -c|--cn)
            CN="$2"
            shift 2
            ;;
        --country)
            COUNTRY="$2"
            shift 2
            ;;
        --state)
            STATE="$2"
            shift 2
            ;;
        --city)
            CITY="$2"
            shift 2
            ;;
        --org)
            ORG="$2"
            shift 2
            ;;
        generate)
            generate_self_signed
            exit 0
            ;;
        generate-san)
            generate_with_san
            exit 0
            ;;
        verify)
            verify_certificate
            exit 0
            ;;
        info)
            show_info
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# If no command provided, show help
show_help
exit 1