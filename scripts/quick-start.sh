#!/bin/bash

# Quick Start Script for Grading System Docker Deployment
# This script provides a one-command setup for the entire system

set -e

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

# Configuration
ENABLE_SSL="${ENABLE_SSL:-false}"
ENABLE_MONITORING="${ENABLE_MONITORING:-false}"
SKIP_CHECKS="${SKIP_CHECKS:-false}"

# Banner
show_banner() {
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                  实验报告自动批阅系统                        ║
║                Docker 快速部署脚本                          ║
╚══════════════════════════════════════════════════════════════╝
EOF
}

# Check prerequisites
check_prerequisites() {
    if [ "$SKIP_CHECKS" = "true" ]; then
        warn "Skipping prerequisite checks"
        return 0
    fi
    
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        info "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        info "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    log "Prerequisites check passed"
}

# Setup environment
setup_environment() {
    log "Setting up environment..."
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        log "Creating .env file from template..."
        cp .env.example .env
        
        warn "Please edit .env file and configure your API keys:"
        warn "  - AI_API_KEY: Your AI service API key"
        warn "  - ARK_API_KEY: Your ARK model API key"
        
        read -p "Press Enter to continue after configuring .env file..."
    fi
    
    # Validate required environment variables
    source .env
    if [ -z "$AI_API_KEY" ] || [ "$AI_API_KEY" = "your_ai_api_key_here" ]; then
        error "AI_API_KEY is not configured in .env file"
        exit 1
    fi
    
    if [ -z "$ARK_API_KEY" ] || [ "$ARK_API_KEY" = "your_ark_api_key_here" ]; then
        error "ARK_API_KEY is not configured in .env file"
        exit 1
    fi
    
    # Create necessary directories
    log "Creating directories..."
    mkdir -p student_reports graded_reports output logs temp ssl backups
    
    log "Environment setup completed"
}

# Setup SSL if enabled
setup_ssl() {
    if [ "$ENABLE_SSL" = "true" ]; then
        log "Setting up SSL certificates..."
        
        if [ ! -f ssl/cert.pem ] || [ ! -f ssl/key.pem ]; then
            log "Generating self-signed SSL certificate..."
            ./scripts/generate-ssl-cert.sh generate-san
        else
            log "SSL certificates already exist"
        fi
    fi
}

# Build and start services
start_services() {
    log "Building and starting services..."
    
    # Build compose file list
    compose_files="-f docker-compose.yml"
    
    if [ "$ENABLE_SSL" = "true" ]; then
        compose_files="$compose_files -f docker-compose.ssl.yml"
        log "SSL enabled"
    fi
    
    if [ "$ENABLE_MONITORING" = "true" ]; then
        compose_files="$compose_files -f docker-compose.monitoring.yml"
        log "Monitoring enabled"
    fi
    
    # Pull images
    log "Pulling Docker images..."
    docker-compose $compose_files pull
    
    # Build application
    log "Building application..."
    docker-compose $compose_files build
    
    # Start services
    log "Starting services..."
    docker-compose $compose_files up -d
    
    log "Services started successfully"
}

# Wait for services to be ready
wait_for_services() {
    log "Waiting for services to be ready..."
    
    # Wait for application to start
    local retries=0
    local max_retries=30
    
    while [ $retries -lt $max_retries ]; do
        if ./scripts/health-check.sh basic &> /dev/null; then
            log "Application is ready"
            break
        fi
        
        retries=$((retries + 1))
        info "Waiting for application... ($retries/$max_retries)"
        sleep 10
    done
    
    if [ $retries -eq $max_retries ]; then
        error "Application failed to start within expected time"
        log "Checking service status..."
        docker-compose ps
        log "Recent logs:"
        docker-compose logs --tail=20
        exit 1
    fi
}

# Run health checks
run_health_checks() {
    log "Running comprehensive health checks..."
    
    if ./scripts/health-check.sh all; then
        log "All health checks passed"
    else
        warn "Some health checks failed, but services are running"
        log "Check the logs for more details: docker-compose logs"
    fi
}

# Show access information
show_access_info() {
    log "Deployment completed successfully!"
    
    echo
    info "Access Information:"
    echo "  📱 Web Application: http://localhost"
    
    if [ "$ENABLE_SSL" = "true" ]; then
        echo "  🔒 HTTPS Access: https://localhost"
    fi
    
    if [ "$ENABLE_MONITORING" = "true" ]; then
        echo "  📊 Grafana Dashboard: http://localhost:3000 (admin/admin)"
        echo "  📈 Prometheus: http://localhost:9090"
        echo "  🚨 Alertmanager: http://localhost:9093"
    fi
    
    echo
    info "Useful Commands:"
    echo "  📋 Check status: docker-compose ps"
    echo "  📝 View logs: docker-compose logs -f"
    echo "  🔍 Health check: ./scripts/health-check.sh all"
    echo "  🛑 Stop services: docker-compose down"
    echo "  💾 Backup data: ./scripts/backup.sh"
    
    echo
    info "Documentation:"
    echo "  📖 Deployment Guide: DEPLOYMENT.md"
    echo "  🔧 Configuration: .env file"
    echo "  🆘 Troubleshooting: DEPLOYMENT.md#故障排除"
}

# Cleanup on failure
cleanup_on_failure() {
    error "Deployment failed. Cleaning up..."
    docker-compose down -v 2>/dev/null || true
    exit 1
}

# Main function
main() {
    show_banner
    
    # Set trap for cleanup on failure
    trap cleanup_on_failure ERR
    
    check_prerequisites
    setup_environment
    setup_ssl
    start_services
    wait_for_services
    run_health_checks
    show_access_info
}

# Help function
show_help() {
    cat << EOF
Quick Start Script for Grading System

Usage: $0 [OPTIONS]

Options:
    --ssl               Enable SSL/HTTPS support
    --monitoring        Enable monitoring stack (Prometheus, Grafana, etc.)
    --skip-checks       Skip prerequisite checks
    -h, --help          Show this help message

Environment Variables:
    ENABLE_SSL          Enable SSL (true/false)
    ENABLE_MONITORING   Enable monitoring (true/false)
    SKIP_CHECKS         Skip checks (true/false)

Examples:
    $0                          # Basic deployment
    $0 --ssl                    # Deployment with SSL
    $0 --ssl --monitoring       # Full deployment with monitoring
    ENABLE_SSL=true $0          # Using environment variable

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ssl)
            ENABLE_SSL="true"
            shift
            ;;
        --monitoring)
            ENABLE_MONITORING="true"
            shift
            ;;
        --skip-checks)
            SKIP_CHECKS="true"
            shift
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

# Run main function
main