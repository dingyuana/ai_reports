#!/bin/bash

# Docker Volume Restore Script
# This script restores Docker volumes from backup files

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
COMPOSE_PROJECT="${COMPOSE_PROJECT_NAME:-docker-deployment}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Function to list available backups
list_backups() {
    log "Available backups in $BACKUP_DIR:"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        error "Backup directory does not exist: $BACKUP_DIR"
        return 1
    fi
    
    # Find manifest files and extract timestamps
    find "$BACKUP_DIR" -name "manifest_*.json" -type f | sort -r | while read -r manifest; do
        if [ -f "$manifest" ]; then
            timestamp=$(basename "$manifest" | sed 's/manifest_\(.*\)\.json/\1/')
            date_info=$(jq -r '.date // "Unknown"' "$manifest" 2>/dev/null || echo "Unknown")
            volumes=$(jq -r '.volumes | join(", ")' "$manifest" 2>/dev/null || echo "Unknown")
            
            echo "  Timestamp: $timestamp"
            echo "  Date: $date_info"
            echo "  Volumes: $volumes"
            echo "  ---"
        fi
    done
}

# Function to restore a single volume
restore_volume() {
    local volume_name=$1
    local timestamp=$2
    local backup_file="${BACKUP_DIR}/${volume_name}_${timestamp}.tar.gz"
    
    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        return 1
    fi
    
    log "Restoring volume: $volume_name from $backup_file"
    
    # Stop containers using this volume
    warn "Stopping containers that might be using volume: ${COMPOSE_PROJECT}_${volume_name}"
    docker-compose down 2>/dev/null || true
    
    # Remove existing volume (with confirmation)
    if docker volume ls -q | grep -q "^${COMPOSE_PROJECT}_${volume_name}$"; then
        warn "Volume ${COMPOSE_PROJECT}_${volume_name} exists and will be replaced"
        read -p "Are you sure you want to replace the existing volume? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error "Restore cancelled by user"
            return 1
        fi
        
        docker volume rm "${COMPOSE_PROJECT}_${volume_name}" || {
            error "Failed to remove existing volume. It might be in use."
            return 1
        }
    fi
    
    # Create new volume
    docker volume create "${COMPOSE_PROJECT}_${volume_name}"
    
    # Restore data to volume
    docker run --rm \
        -v "${COMPOSE_PROJECT}_${volume_name}:/data" \
        -v "$(pwd)/${BACKUP_DIR}:/backup:ro" \
        alpine:latest \
        tar xzf "/backup/$(basename "$backup_file")" -C /data
    
    if [ $? -eq 0 ]; then
        log "Successfully restored $volume_name"
        return 0
    else
        error "Failed to restore $volume_name"
        return 1
    fi
}

# Function to restore all volumes from a timestamp
restore_all_volumes() {
    local timestamp=$1
    local manifest_file="${BACKUP_DIR}/manifest_${timestamp}.json"
    
    if [ ! -f "$manifest_file" ]; then
        error "Manifest file not found: $manifest_file"
        return 1
    fi
    
    log "Restoring all volumes from timestamp: $timestamp"
    
    # Read volumes from manifest
    volumes=$(jq -r '.volumes[]' "$manifest_file" 2>/dev/null)
    
    if [ -z "$volumes" ]; then
        error "No volumes found in manifest file"
        return 1
    fi
    
    # Restore each volume
    while IFS= read -r volume; do
        restore_volume "$volume" "$timestamp"
    done <<< "$volumes"
    
    log "All volumes restored from timestamp: $timestamp"
}

# Function to verify backup integrity
verify_backup() {
    local timestamp=$1
    local manifest_file="${BACKUP_DIR}/manifest_${timestamp}.json"
    
    if [ ! -f "$manifest_file" ]; then
        error "Manifest file not found: $manifest_file"
        return 1
    fi
    
    log "Verifying backup integrity for timestamp: $timestamp"
    
    # Check if all backup files exist
    volumes=$(jq -r '.volumes[]' "$manifest_file" 2>/dev/null)
    missing_files=()
    
    while IFS= read -r volume; do
        backup_file="${BACKUP_DIR}/${volume}_${timestamp}.tar.gz"
        if [ ! -f "$backup_file" ]; then
            missing_files+=("$backup_file")
        else
            # Test if tar file is valid
            if ! tar -tzf "$backup_file" >/dev/null 2>&1; then
                error "Corrupted backup file: $backup_file"
                return 1
            fi
        fi
    done <<< "$volumes"
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        error "Missing backup files:"
        printf '%s\n' "${missing_files[@]}"
        return 1
    fi
    
    log "Backup integrity verified successfully"
    return 0
}

# Help function
show_help() {
    cat << EOF
Docker Volume Restore Script

Usage: $0 [OPTIONS] COMMAND [ARGS]

Commands:
    list                                List available backups
    restore-all TIMESTAMP              Restore all volumes from a backup timestamp
    restore-volume VOLUME TIMESTAMP    Restore a specific volume from backup
    verify TIMESTAMP                   Verify backup integrity

Options:
    -h, --help          Show this help message
    -d, --backup-dir    Backup directory (default: ./backups)
    -p, --project       Docker Compose project name (default: docker-deployment)

Environment Variables:
    BACKUP_DIR          Backup directory path
    COMPOSE_PROJECT_NAME Docker Compose project name

Examples:
    $0 list                                    # List available backups
    $0 restore-all 20231201_143022            # Restore all volumes
    $0 restore-volume student_reports 20231201_143022  # Restore specific volume
    $0 verify 20231201_143022                  # Verify backup integrity

EOF
}

# Main function
main() {
    local command=$1
    shift
    
    case $command in
        list)
            list_backups
            ;;
        restore-all)
            if [ $# -ne 1 ]; then
                error "restore-all requires a timestamp argument"
                show_help
                exit 1
            fi
            restore_all_volumes "$1"
            ;;
        restore-volume)
            if [ $# -ne 2 ]; then
                error "restore-volume requires volume name and timestamp arguments"
                show_help
                exit 1
            fi
            restore_volume "$1" "$2"
            ;;
        verify)
            if [ $# -ne 1 ]; then
                error "verify requires a timestamp argument"
                show_help
                exit 1
            fi
            verify_backup "$1"
            ;;
        *)
            error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        -p|--project)
            COMPOSE_PROJECT="$2"
            shift 2
            ;;
        -*)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
        *)
            # First non-option argument is the command
            main "$@"
            exit $?
            ;;
    esac
done

# If no command provided, show help
show_help
exit 1