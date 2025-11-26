"""
Environment detection and service configuration for dual-mode operation.
Handles localhost vs container name resolution for different services.
"""

import os
import socket
from typing import Dict, Optional


class EnvironmentConfig:
    """Configuration manager for dual-mode operation (local vs Docker)"""
    
    def __init__(self):
        self._is_docker = self._detect_docker_environment()
        self._setup_service_urls()
    
    def _detect_docker_environment(self) -> bool:
        """Detect if running inside a Docker container"""
        # Check for .dockerenv file (most reliable indicator)
        if os.path.exists('/.dockerenv'):
            return True
        
        # Check for Docker-specific environment variables that indicate container
        docker_env_vars = [
            'DOCKER_CONTAINER',
            'COMPOSE_SERVICE_NAME',
            'DOCKER_SERVICE_NAME'
        ]
        
        for var in docker_env_vars:
            if os.getenv(var):
                return True
        
        # Additional Docker-specific file checks
        docker_files = [
            '/run/.containerenv',  # podman
            '/.dockerenv'  # already checked above, but for completeness
        ]
        
        for file_path in docker_files:
            if os.path.exists(file_path):
                return True
        
        # Check if running in a container by examining process tree
        # This is a more reliable method than just checking for Docker socket
        try:
            with open('/proc/1/cgroup', 'r') as f:
                cgroup_content = f.read()
                # Check for Docker-specific patterns in cgroup
                if any(pattern in cgroup_content for pattern in [
                    'docker', 'lxc', 'kubepods', 'containerd'
                ]):
                    return True
        except (FileNotFoundError, PermissionError):
            pass
        
        # DO NOT check for Docker socket existence - it can exist on host machines
        # This was the main issue causing false positives
        return False
    
    def _setup_service_urls(self):
        """Setup service URLs based on environment"""
        base_host = "localhost" if not self._is_docker else "voicebot-app"
        base_port = "8001"
        
        # VoiceBot API URL
        self.voicebot_api_url = f"http://{base_host}:{base_port}"
        
        # LiveKit URLs
        livekit_host = "localhost" if not self._is_docker else "livekit"
        self.livekit_url = f"ws://{livekit_host}:7880"
        self.livekit_api_url = f"http://{livekit_host}:7880"
        
        # Database URLs
        db_host = "localhost" if not self._is_docker else "postgres"
        self.database_url = f"postgresql://voicebot_user:voicebot_password@{db_host}:5432/voicebot"
        
        # Qdrant URL
        qdrant_host = "localhost" if not self._is_docker else "qdrant"
        self.qdrant_url = f"http://{qdrant_host}:6333"
        
        # Redis URL
        redis_host = "localhost" if not self._is_docker else "redis"
        self.redis_url = os.getenv("REDIS_URL", f"redis://{redis_host}:6379")
        
        # Frontend URL
        front_host = "localhost" if not self._is_docker else "voicebot-app-front"
        self.frontend_url = f"http://{front_host}:3000"
    
    def get_service_config(self, service_name: str) -> Dict[str, str]:
        """Get configuration for a specific service"""
        configs = {
            "voicebot": {
                "api_url": self.voicebot_api_url,
                "health_url": f"{self.voicebot_api_url}/health"
            },
            "livekit": {
                "ws_url": self.livekit_url,
                "api_url": self.livekit_api_url
            },
            "database": {
                "url": self.database_url
            },
            "qdrant": {
                "url": self.qdrant_url
            },
            "redis": {
                "url": self.redis_url
            },
            "frontend": {
                "url": self.frontend_url
            }
        }
        
        return configs.get(service_name, {})
    
    def get_all_configs(self) -> Dict[str, Dict[str, str]]:
        """Get all service configurations"""
        return {
            "voicebot": self.get_service_config("voicebot"),
            "livekit": self.get_service_config("livekit"), 
            "database": self.get_service_config("database"),
            "qdrant": self.get_service_config("qdrant"),
            "redis": self.get_service_config("redis"),
            "frontend": self.get_service_config("frontend"),
            "metadata": {
                "is_docker": self._is_docker,
                "environment": "docker" if self._is_docker else "local"
            }
        }
    
    @property
    def is_docker(self) -> bool:
        """Check if running in Docker environment"""
        return self._is_docker
    
    @property
    def environment_type(self) -> str:
        """Get environment type as string"""
        return "docker" if self._is_docker else "local"
    
    def __str__(self) -> str:
        """String representation showing environment and key URLs"""
        config = self.get_all_configs()
        return f"Environment: {config['metadata']['environment']}\n" + \
               f"VoiceBot API: {config['voicebot']['api_url']}\n" + \
               f"LiveKit: {config['livekit']['ws_url']}"


# Global configuration instance
config = EnvironmentConfig()


def get_environment_config() -> EnvironmentConfig:
    """Get the global environment configuration instance"""
    return config


def is_running_in_docker() -> bool:
    """Check if currently running in Docker"""
    return config.is_docker


def get_service_url(service_name: str, fallback: Optional[str] = None) -> str:
    """Get URL for a service, with optional fallback"""
    service_config = config.get_service_config(service_name)
    
    # Look for URL in different possible keys
    url_keys = ["url", "api_url", "ws_url"]
    for key in url_keys:
        if key in service_config:
            return service_config[key]
    
    # Return fallback if no URL found
    return fallback or f"Unknown service: {service_name}"


# Convenience functions for common services
def get_livekit_url() -> str:
    """Get LiveKit WebSocket URL"""
    return config.livekit_url


def get_voicebot_api_url() -> str:
    """Get VoiceBot API URL"""
    return config.voicebot_api_url


def get_database_url() -> str:
    """Get database connection URL"""
    return config.database_url


def get_redis_url() -> str:
    """Get Redis connection URL"""
    return config.redis_url


def get_qdrant_url() -> str:
    """Get Qdrant connection URL"""
    return config.qdrant_url