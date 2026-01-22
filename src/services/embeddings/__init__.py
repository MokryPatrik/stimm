"""
Embeddings module - provides lightweight ONNX-based embedding models.

This module exports drop-in replacements for sentence_transformers models
that use ONNX Runtime instead of PyTorch, eliminating heavy dependencies.

Also supports OpenAI embeddings for offloading computation to the cloud.
"""

from .onnx_models import CrossEncoder, SentenceTransformer
from .openai_embeddings import OpenAIEmbeddings, get_embedder, is_openai_model

__all__ = [
    "SentenceTransformer",
    "CrossEncoder",
    "OpenAIEmbeddings",
    "get_embedder",
    "is_openai_model",
]
