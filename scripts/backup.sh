#!/bin/bash

# Docker Volume Backup Script
# This script creates backups of all persistent Docker volumes

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
COMPOSE_PROJECT="${COMPOSE_PROJECT_NAME:-docker-deployment}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Function to backup a volume
backup_volume() {
    local volume_name=$1
    local backup_name="${volume_name}_${TIMESTAMP}.tar.gz"
    local backup_path="${BACKUP_DIR}/${backup_name}"
    
    log "Backing up volume: $volume_name"
    
    # Create a temporary container to access the volume
    docker run --rm \
        -v "${COMPOSE_PROJECT}_${volume_name}:/data:ro" \
        -v "$(pwd)/${BACKUP_DIR}:/backup" \
        alpine:latest \
        tar czf "/backup/${backup_name}" -C /data .
    
    if [ $? -eq 0 ]; then
        log "Successfully backed up $volume_name to $backup_path"
        echo "$backup_path" >> "${BACKUP_DIR}/backup_${TIMESTAMP}.log"
    else
        error "Failed to backup $volume_name"
        return 1
    fi
}

# Main backup function
main() {
    log "Starting Docker volume backup process"
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running"
        exit 1
    fi
    
    # List of volumes to backup
    volumes=(
        "student_reports"
        "graded_reports"
        "output_data"
        "app_logs"
    )
    
    # Create backup log
    echo "Backup started at $(date)" > "${BACKUP_DIR}/backup_${TIMESTAMP}.log"
    
    # Backup each volume
    for volume in "${volumes[@]}"; do
        backup_volume "$volume"
    done
    
    # Create a manifest file
    cat > "${BACKUP_DIR}/manifest_${TIMESTAMP}.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "date": "$(date -Iseconds)",
    "volumes": [
        $(printf '"%s",' "${volumes[@]}" | sed 's/,$//')
    ],
    "backup_dir": "$BACKUP_DIR",
    "compose_project": "$COMPOSE_PROJECT"
}
EOF
    
    log "Backup process completed. Manifest created: ${BACKUP_DIR}/manifest_${TIMESTAMP}.json"
    
    # Clean up old backups (keep last 7 days)
    find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "manifest_*.json" -mtime +7 -delete 2>/dev/null || true
    
    log "Old backups cleaned up (kept last 7 days)"
}

# Help function
show_help() {
    cat << EOF
Docker Volume Backup Script

Usage: $0 [OPTIONS]

Options:
    -h, --help          Show this help message
    -d, --backup-dir    Backup directory (default: ./backups)
    -p, --project       Docker Compose project name (default: docker-deployment)

Environment Variables:
    BACKUP_DIR          Backup directory path
    COMPOSE_PROJECT_NAME Docker Compose project name

Examples:
    $0                                  # Basic backup
    $0 -d /path/to/backups             # Custom backup directory
    $0 -p myproject                     # Custom project name
    BACKUP_DIR=/backups $0              # Using environment variable

EOF
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
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function
main