#!/bin/bash

# Deployment Script for Grading System
# This script automates the deployment process

set -e

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
SSL_ENABLED="${SSL_ENABLED:-false}"
BACKUP_BEFORE_DEPLOY="${BACKUP_BEFORE_DEPLOY:-true}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"; }
error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"; }

# Pre-deployment checks
pre_deploy_checks() {
    log "Running pre-deployment checks..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check environment file
    if [ ! -f "$ENV_FILE" ]; then
        warn "Environment file not found, copying from example"
        cp .env.example "$ENV_FILE"
        error "Please configure $ENV_FILE with your settings"
        exit 1
    fi
    
    # Validate required environment variables
    source "$ENV_FILE"
    if [ -z "$AI_API_KEY" ] || [ -z "$ARK_API_KEY" ]; then
        error "Required API keys not set in $ENV_FILE"
        exit 1
    fi
    
    log "Pre-deployment checks passed"
}

# Backup existing data
backup_data() {
    if [ "$BACKUP_BEFORE_DEPLOY" = "true" ]; then
        log "Creating backup before deployment..."
        ./scripts/backup.sh || warn "Backup failed, continuing anyway"
    fi
}

# Deploy application
deploy() {
    log "Starting deployment..."
    
    # Build compose file list
    compose_files="-f $COMPOSE_FILE"
    
    if [ "$SSL_ENABLED" = "true" ]; then
        compose_files="$compose_files -f docker-compose.ssl.yml"
        log "SSL enabled, using HTTPS configuration"
    fi
    
    # Pull latest images
    log "Pulling latest images..."
    docker-compose $compose_files pull
    
    # Build application image
    log "Building application image..."
    docker-compose $compose_files build
    
    # Start services
    log "Starting services..."
    docker-compose $compose_files up -d
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 30
    
    # Health check
    if ./scripts/health-check.sh ready; then
        log "Deployment successful!"
    else
        error "Deployment failed - services not ready"
        exit 1
    fi
}

# Post-deployment tasks
post_deploy() {
    log "Running post-deployment tasks..."
    
    # Show service status
    docker-compose ps
    
    # Show logs
    log "Recent logs:"
    docker-compose logs --tail=20
    
    log "Deployment completed successfully!"
    log "Access the application at: http://localhost"
    if [ "$SSL_ENABLED" = "true" ]; then
        log "HTTPS access: https://localhost"
    fi
}

# Main deployment function
main() {
    log "Starting deployment process..."
    
    pre_deploy_checks
    backup_data
    deploy
    post_deploy
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ssl)
            SSL_ENABLED="true"
            shift
            ;;
        --no-backup)
            BACKUP_BEFORE_DEPLOY="false"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --ssl        Enable SSL/HTTPS"
            echo "  --no-backup  Skip backup before deployment"
            echo "  -h, --help   Show this help"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

main