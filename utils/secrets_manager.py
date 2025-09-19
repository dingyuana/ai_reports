"""
Secrets management utility for Docker secrets and environment variables
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def read_secret(secret_name: str, env_var_name: str, default: Optional[str] = None, required: bool = False) -> str:
    """
    Read secret from Docker secrets file or environment variable
    
    Args:
        secret_name: Name of the secret file (e.g., 'ai_api_key')
        env_var_name: Environment variable name (e.g., 'AI_API_KEY')
        default: Default value if neither secret nor env var is found
        required: Whether this secret is required
        
    Returns:
        Secret value
        
    Raises:
        ValueError: If required secret is not found
    """
    # First try to read from Docker secrets file
    secret_file_env = f"{env_var_name}_FILE"
    secret_file_path = os.getenv(secret_file_env)
    
    if secret_file_path and os.path.exists(secret_file_path):
        try:
            with open(secret_file_path, 'r') as f:
                secret_value = f.read().strip()
                logger.info(f"Successfully read secret from file: {secret_file_path}")
                return secret_value
        except Exception as e:
            logger.error(f"Failed to read secret from file {secret_file_path}: {e}")
    
    # Fallback to environment variable
    env_value = os.getenv(env_var_name)
    if env_value:
        logger.info(f"Using secret from environment variable: {env_var_name}")
        return env_value
    
    # Use default if provided
    if default is not None:
        logger.warning(f"Using default value for secret: {secret_name}")
        return default
    
    # Raise error if required
    if required:
        raise ValueError(f"Required secret '{secret_name}' not found in Docker secrets or environment variables")
    
    return ""

def get_ai_api_key() -> str:
    """Get AI API key from secrets or environment"""
    return read_secret("ai_api_key", "AI_API_KEY", required=True)

def get_ark_api_key() -> str:
    """Get ARK API key from secrets or environment"""
    return read_secret("ark_api_key", "ARK_API_KEY", required=True)

def get_secret_key() -> str:
    """Get application secret key from secrets or environment"""
    return read_secret("secret_key", "SECRET_KEY", default="default-secret-key-change-in-production")

def validate_secrets():
    """Validate that all required secrets are available"""
    try:
        get_ai_api_key()
        get_ark_api_key()
        logger.info("All required secrets validated successfully")
        return True
    except ValueError as e:
        logger.error(f"Secret validation failed: {e}")
        return False