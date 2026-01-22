"""
OpenAI Embeddings - API-based embedding generation.

This module provides an OpenAI-compatible embedding interface that offloads
computation to OpenAI's servers, reducing local CPU usage.
"""

import logging
import os
from typing import List, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)


class OpenAIEmbeddings:
    """
    OpenAI API-based embeddings.
    
    This class provides a SentenceTransformer-compatible interface but uses
    OpenAI's API for embedding generation.
    """

    # Model dimensions mapping
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        dimensions: Optional[int] = None,
    ):
        """
        Initialize the OpenAI embeddings client.

        Args:
            model_name: OpenAI embedding model name
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            dimensions: Optional output dimensions (for text-embedding-3-* models)
        """
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._dimensions = dimensions
        self._client = None
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY env var or pass api_key.")
        
        logger.info(f"Initialized OpenAI embeddings with model: {model_name}")

    @property
    def client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package is required. Install with: pip install openai")
        return self._client

    def encode(
        self,
        sentences: Union[str, List[str]],
        batch_size: int = 100,
        show_progress_bar: bool = False,
        convert_to_numpy: bool = True,
        normalize_embeddings: bool = False,
    ) -> np.ndarray:
        """
        Encode sentences into embeddings using OpenAI API.

        Args:
            sentences: Single sentence or list of sentences to encode
            batch_size: Batch size for API calls (max ~2048 for OpenAI)
            show_progress_bar: Whether to show progress bar (ignored)
            convert_to_numpy: Whether to return numpy array (always True)
            normalize_embeddings: Whether to L2-normalize embeddings

        Returns:
            numpy array of embeddings
        """
        # Handle single string input
        if isinstance(sentences, str):
            sentences = [sentences]

        if not sentences:
            return np.array([])

        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(sentences), batch_size):
            batch = sentences[i:i + batch_size]
            
            try:
                # Build request params
                params = {
                    "model": self.model_name,
                    "input": batch,
                }
                
                # Add dimensions for text-embedding-3-* models
                if self._dimensions and self.model_name.startswith("text-embedding-3"):
                    params["dimensions"] = self._dimensions
                
                response = self.client.embeddings.create(**params)
                
                # Extract embeddings from response
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
            except Exception as e:
                logger.error(f"Error encoding batch {i // batch_size + 1}: {e}")
                raise

        embeddings = np.array(all_embeddings, dtype=np.float32)

        # Normalize if requested
        if normalize_embeddings:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / np.clip(norms, a_min=1e-9, a_max=None)

        return embeddings

    def get_sentence_embedding_dimension(self) -> int:
        """
        Get the dimension of the sentence embeddings.

        Returns:
            Embedding dimension size
        """
        if self._dimensions:
            return self._dimensions
        return self.MODEL_DIMENSIONS.get(self.model_name, 1536)


def is_openai_model(model_name: str) -> bool:
    """Check if a model name refers to an OpenAI embedding model."""
    openai_prefixes = ["text-embedding-", "openai/"]
    return any(model_name.startswith(prefix) for prefix in openai_prefixes)


def get_embedder(model_name: str, api_key: Optional[str] = None, **kwargs):
    """
    Factory function to get the appropriate embedder based on model name.
    
    Args:
        model_name: Model name (OpenAI model or local ONNX model)
        api_key: API key for OpenAI embeddings (ignored for local models)
        **kwargs: Additional arguments passed to the embedder
        
    Returns:
        Embedder instance (OpenAIEmbeddings or SentenceTransformer)
    """
    if is_openai_model(model_name):
        # Strip "openai/" prefix if present
        if model_name.startswith("openai/"):
            model_name = model_name[7:]
        return OpenAIEmbeddings(model_name=model_name, api_key=api_key, **kwargs)
    else:
        from .onnx_models import SentenceTransformer
        # Don't pass api_key to local ONNX models
        return SentenceTransformer(model_name, **kwargs)
