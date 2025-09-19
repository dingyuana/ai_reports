#!/bin/bash

# Health Check Script for Docker Container
# This script performs comprehensive health checks for the grading system

set -e

# Configuration
HOST="${HEALTH_CHECK_HOST:-localhost}"
PORT="${HEALTH_CHECK_PORT:-8000}"
TIMEOUT="${HEALTH_CHECK_TIMEOUT:-10}"
VERBOSE="${HEALTH_CHECK_VERBOSE:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
    fi
}

warn() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
    fi
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
}

# Function to check if service is responding
check_basic_health() {
    log "Checking basic health endpoint..."
    
    if command -v curl >/dev/null 2>&1; then
        response=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "http://$HOST:$PORT/health" 2>/dev/null)
        if [ "$response" = "200" ]; then
            log "Basic health check passed"
            return 0
        else
            error "Basic health check failed with HTTP $response"
            return 1
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q --timeout="$TIMEOUT" --tries=1 --spider "http://$HOST:$PORT/health" 2>/dev/null; then
            log "Basic health check passed"
            return 0
        else
            error "Basic health check failed"
            return 1
        fi
    else
        # Fallback to Python if curl/wget not available
        python3 -c "
import requests
import sys
try:
    response = requests.get('http://$HOST:$PORT/health', timeout=$TIMEOUT)
    if response.status_code == 200:
        sys.exit(0)
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)
" 2>/dev/null
        
        if [ $? -eq 0 ]; then
            log "Basic health check passed"
            return 0
        else
            error "Basic health check failed"
            return 1
        fi
    fi
}

# Function to check detailed health
check_detailed_health() {
    log "Checking detailed health endpoint..."
    
    if command -v python3 >/dev/null 2>&1; then
        python3 -c "
import requests
import json
import sys

try:
    response = requests.get('http://$HOST:$PORT/api/health', timeout=$TIMEOUT)
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
" 2>/dev/null
        
        return $?
    else
        warn "Python3 not available, skipping detailed health check"
        return 0
    fi
}

# Function to check readiness
check_readiness() {
    log "Checking readiness endpoint..."
    
    if command -v python3 >/dev/null 2>&1; then
        python3 -c "
import requests
import sys

try:
    response = requests.get('http://$HOST:$PORT/api/health/ready', timeout=$TIMEOUT)
    if response.status_code == 200:
        print('Readiness check passed')
        sys.exit(0)
    else:
        print(f'Readiness check failed with HTTP {response.status_code}')
        sys.exit(1)
except Exception as e:
    print(f'Readiness check failed: {e}')
    sys.exit(1)
" 2>/dev/null
        
        return $?
    else
        warn "Python3 not available, skipping readiness check"
        return 0
    fi
}

# Function to check liveness
check_liveness() {
    log "Checking liveness endpoint..."
    
    if command -v curl >/dev/null 2>&1; then
        response=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "http://$HOST:$PORT/api/health/live" 2>/dev/null)
        if [ "$response" = "200" ]; then
            log "Liveness check passed"
            return 0
        else
            error "Liveness check failed with HTTP $response"
            return 1
        fi
    else
        # Fallback to basic health check
        return check_basic_health
    fi
}

# Main health check function
main_health_check() {
    local check_type="${1:-basic}"
    
    case "$check_type" in
        "basic")
            check_basic_health
            ;;
        "detailed")
            check_detailed_health
            ;;
        "ready"|"readiness")
            check_readiness
            ;;
        "live"|"liveness")
            check_liveness
            ;;
        "all")
            check_basic_health && check_detailed_health && check_readiness && check_liveness
            ;;
        *)
            error "Unknown check type: $check_type"
            echo "Available types: basic, detailed, ready, live, all"
            exit 1
            ;;
    esac
}

# Help function
show_help() {
    cat << EOF
Health Check Script for Grading System

Usage: $0 [OPTIONS] [CHECK_TYPE]

Check Types:
    basic       Basic health check (default)
    detailed    Detailed health check with system info
    ready       Readiness probe check
    live        Liveness probe check
    all         Run all health checks

Options:
    -h, --help          Show this help message
    -v, --verbose       Enable verbose output
    -H, --host          Host to check (default: localhost)
    -p, --port          Port to check (default: 8000)
    -t, --timeout       Request timeout in seconds (default: 10)

Environment Variables:
    HEALTH_CHECK_HOST       Host to check
    HEALTH_CHECK_PORT       Port to check
    HEALTH_CHECK_TIMEOUT    Request timeout
    HEALTH_CHECK_VERBOSE    Enable verbose output (true/false)

Examples:
    $0                      # Basic health check
    $0 detailed             # Detailed health check
    $0 -v all              # All checks with verbose output
    $0 -H app -p 8000 ready # Readiness check on specific host

Exit Codes:
    0   Health check passed
    1   Health check failed

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        -H|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -*)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
        *)
            # First non-option argument is the check type
            main_health_check "$1"
            exit $?
            ;;
    esac
done

# If no check type provided, run basic check
main_health_check "basic"
exit $?