#!/bin/bash

# Update Script for Grading System
# This script handles application updates with zero-downtime

set -e

# Configuration
COMPOSE_FILE="docker-compose.yml"
BACKUP_BEFORE_UPDATE="${BACKUP_BEFORE_UPDATE:-true}"
HEALTH_CHECK_RETRIES="${HEALTH_CHECK_RETRIES:-5}"
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-10}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"; }
error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"; }
info() { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"; }

# Check if services are running
check_services_running() {
    if ! docker-compose ps | grep -q "Up"; then
        error "No services are currently running"
        exit 1
    fi
}

# Create backup before update
create_backup() {
    if [ "$BACKUP_BEFORE_UPDATE" = "true" ]; then
        log "Creating backup before update..."
        ./scripts/backup.sh || {
            error "Backup failed"
            exit 1
        }
    fi
}

# Pull latest images
pull_images() {
    log "Pulling latest images..."
    docker-compose pull
}

# Build new application image
build_image() {
    log "Building new application image..."
    docker-compose build --no-cache app
}

# Perform rolling update
rolling_update() {
    log "Performing rolling update..."
    
    # Update services one by one
    services=$(docker-compose config --services)
    
    for service in $services; do
        log "Updating service: $service"
        
        # Recreate service
        docker-compose up -d --no-deps --force-recreate "$service"
        
        # Wait for service to be healthy
        wait_for_health "$service"
    done
}

# Wait for service health
wait_for_health() {
    local service=$1
    local retries=0
    
    log "Waiting for $service to be healthy..."
    
    while [ $retries -lt $HEALTH_CHECK_RETRIES ]; do
        if docker-compose ps "$service" | grep -q "healthy\|Up"; then
            log "$service is healthy"
            return 0
        fi
        
        retries=$((retries + 1))
        warn "Health check attempt $retries/$HEALTH_CHECK_RETRIES for $service"
        sleep $HEALTH_CHECK_INTERVAL
    done
    
    error "$service failed to become healthy"
    return 1
}

# Verify update success
verify_update() {
    log "Verifying update..."
    
    # Check all services are running
    if ! docker-compose ps | grep -q "Up"; then
        error "Some services are not running after update"
        return 1
    fi
    
    # Run health checks
    if ./scripts/health-check.sh all; then
        log "Update verification successful"
        return 0
    else
        error "Update verification failed"
        return 1
    fi
}

# Rollback function
rollback() {
    error "Update failed, initiating rollback..."
    
    # Get latest backup
    latest_backup=$(ls -t backups/manifest_*.json 2>/dev/null | head -1)
    
    if [ -n "$latest_backup" ]; then
        timestamp=$(basename "$latest_backup" | sed 's/manifest_\(.*\)\.json/\1/')
        warn "Rolling back to backup: $timestamp"
        
        # Stop current services
        docker-compose down
        
        # Restore from backup
        ./scripts/restore.sh restore-all "$timestamp"
        
        # Start services
        docker-compose up -d
        
        if verify_update; then
            warn "Rollback completed successfully"
        else
            error "Rollback failed - manual intervention required"
            exit 1
        fi
    else
        error "No backup found for rollback - manual intervention required"
        exit 1
    fi
}

# Clean up old images
cleanup() {
    log "Cleaning up old Docker images..."
    docker image prune -f
    docker system prune -f --volumes=false
}

# Main update function
main() {
    log "Starting update process..."
    
    # Pre-update checks
    check_services_running
    
    # Create backup
    create_backup
    
    # Pull and build
    pull_images
    build_image
    
    # Perform update
    if rolling_update && verify_update; then
        log "Update completed successfully!"
        cleanup
        
        # Show status
        info "Service status:"
        docker-compose ps
        
        info "Recent logs:"
        docker-compose logs --tail=10
        
    else
        rollback
    fi
}

# Show help
show_help() {
    cat << EOF
Update Script for Grading System

Usage: $0 [OPTIONS]

Options:
    --no-backup         Skip backup before update
    --retries N         Number of health check retries (default: 5)
    --interval N        Health check interval in seconds (default: 10)
    -h, --help          Show this help

Environment Variables:
    BACKUP_BEFORE_UPDATE    Create backup before update (default: true)
    HEALTH_CHECK_RETRIES    Number of health check retries
    HEALTH_CHECK_INTERVAL   Health check interval in seconds

Examples:
    $0                      # Standard update with backup
    $0 --no-backup         # Update without backup
    $0 --retries 10        # Update with more health check retries

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-backup)
            BACKUP_BEFORE_UPDATE="false"
            shift
            ;;
        --retries)
            HEALTH_CHECK_RETRIES="$2"
            shift 2
            ;;
        --interval)
            HEALTH_CHECK_INTERVAL="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

main