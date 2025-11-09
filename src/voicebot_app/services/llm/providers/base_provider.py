"""
Base Provider Interface with standardized property mapping support.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseProvider(ABC):
    """Base provider interface with standardized property mapping support."""
    
    @classmethod
    def get_expected_properties(cls) -> List[str]:
        """
        Get the list of expected properties for this provider.
        
        Returns:
            List of property names that this provider expects
        """
        return ["model", "api_key"]
    
    @classmethod
    def to_provider_format(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert standardized frontend config to provider-specific format.
        
        Args:
            config: Standardized configuration dictionary
            
        Returns:
            Provider-specific configuration dictionary
        """
        # Default implementation - no mapping needed for most providers
        return config.copy()
    
    @classmethod
    def from_provider_format(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert provider-specific config to standardized frontend format.
        
        Args:
            config: Provider-specific configuration dictionary
            
        Returns:
            Standardized configuration dictionary
        """
        # Default implementation - no mapping needed for most providers
        return config.copy()
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using the provider."""
        pass
    
    @abstractmethod
    async def generate_stream(self, prompt: str, **kwargs):
        """Stream text generation using the provider."""
        pass