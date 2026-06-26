"""
Nova Ecosystem Environment Detection Module

Provides standardized environment detection across all services.
Ensures consistent behavior between production and local development environments.
"""

import os
from enum import Enum


class Environment(Enum):
    """Environment types supported by Nova Ecosystem"""
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    LOCAL = "local"


def get_environment() -> Environment:
    """
    Determine current environment with clear hierarchy.

    Returns:
        Environment: The detected environment type

    Environment Detection Logic:
        1. NOVA_ENV environment variable (explicit override)
        2. GCP Cloud Run indicators (K_SERVICE + GOOGLE_CLOUD_PROJECT)
        3. Default to local development
    """
    # Check explicit environment override
    nova_env = os.getenv('NOVA_ENV', '').lower()
    if nova_env == 'production':
        return Environment.PRODUCTION
    elif nova_env == 'development':
        return Environment.DEVELOPMENT
    elif nova_env == 'local':
        return Environment.LOCAL

    # Check for GCP Cloud Run environment
    if os.getenv('GOOGLE_CLOUD_PROJECT') and os.getenv('K_SERVICE'):
        return Environment.PRODUCTION

    # Default to local development
    return Environment.LOCAL


def get_sdk_import_path() -> str:
    """
    Get the appropriate SDK import path based on environment.

    Returns:
        str: Import path for AgentSDK
    """
    env = get_environment()

    if env == Environment.PRODUCTION:
        return "shared.packages.agent_sdk.agent_sdk"
    else:
        return "local_development.services.mocks.mock_agent_sdk"


def is_production() -> bool:
    """Check if running in production environment"""
    return get_environment() == Environment.PRODUCTION


def is_local_development() -> bool:
    """Check if running in local development environment"""
    return get_environment() in [Environment.LOCAL, Environment.DEVELOPMENT]


def get_config_file_path() -> str:
    """
    Get the appropriate configuration file path based on environment.

    Returns:
        str: Path to environment-specific configuration file
    """
    env = get_environment()
    base_path = ".nova-config"

    if env == Environment.PRODUCTION:
        return f"{base_path}/production.env"
    elif env == Environment.DEVELOPMENT:
        return f"{base_path}/development.env"
    else:
        return f"{base_path}/local.env"


def get_environment_info() -> dict:
    """
    Get comprehensive environment information for debugging.

    Returns:
        dict: Environment information including detection details
    """
    env = get_environment()

    return {
        "environment": env.value,
        "is_production": is_production(),
        "is_local_development": is_local_development(),
        "sdk_import_path": get_sdk_import_path(),
        "config_file_path": get_config_file_path(),
        "detection_details": {
            "NOVA_ENV": os.getenv('NOVA_ENV'),
            "GOOGLE_CLOUD_PROJECT": os.getenv('GOOGLE_CLOUD_PROJECT'),
            "K_SERVICE": os.getenv('K_SERVICE'),
            "detected_from": _get_detection_source()
        }
    }


def _get_detection_source() -> str:
    """Internal helper to identify how environment was detected"""
    if os.getenv('NOVA_ENV'):
        return "NOVA_ENV environment variable"
    elif os.getenv('GOOGLE_CLOUD_PROJECT') and os.getenv('K_SERVICE'):
        return "GCP Cloud Run indicators"
    else:
        return "default (local development)"


# For backward compatibility, provide the old function name
def get_nova_environment() -> Environment:
    """Alias for get_environment() for backward compatibility"""
    return get_environment()
