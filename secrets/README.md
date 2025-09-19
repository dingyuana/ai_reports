# Secrets Management

This directory contains sensitive configuration files for Docker secrets.

## Setup Instructions

1. Create the secret files:
   ```bash
   echo "your_ai_api_key_here" > secrets/ai_api_key.txt
   echo "your_ark_api_key_here" > secrets/ark_api_key.txt
   echo "your_secret_key_here" > secrets/secret_key.txt
   ```

2. Set proper permissions:
   ```bash
   chmod 600 secrets/*.txt
   ```

3. Use with Docker Compose:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
   ```

## Security Notes

- Never commit actual secret files to version control
- Use proper file permissions (600) for secret files
- In production, consider using external secret management systems
- Rotate secrets regularly

## Alternative: External Secret Management

For production environments, consider using:
- Docker Swarm secrets
- Kubernetes secrets
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager