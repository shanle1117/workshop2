"""
Semantic search module using sentence-transformers for better query matching.
"""
import os
from typing import List, Dict, Tuple, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not available. Install with: pip install sentence-transformers")


class SemanticSearch:
    """
    Semantic search using sentence-transformers for better query matching.
    Uses pre-trained models to encode text into dense vectors and find similar content.
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize semantic search with a sentence transformer model.
        
        Args:
            model_name: Name of the sentence transformer model to use.
                       Default: 'all-MiniLM-L6-v2' (lightweight and fast)
                       Alternatives: 'all-mpnet-base-v2' (more accurate but slower)
        """
        self.model = None
        self.model_name = model_name
        self.embeddings_cache = {}
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                # Silent loading - no verbose output
                import logging
                logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
                import warnings
                warnings.filterwarnings('ignore')
                self.model = SentenceTransformer(model_name)
            except Exception as e:
                self.model = None
        else:
            # Only show warning if explicitly needed
            pass
    
    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Encode texts into dense vectors.
        
        Args:
            texts: List of text strings to encode
            batch_size: Batch size for encoding
            
        Returns:
            numpy array of embeddings (shape: [len(texts), embedding_dim])
        """
        if not self.model:
            raise RuntimeError("Model not loaded. Semantic search unavailable.")
        
        # Use cache if available
        if isinstance(texts, str):
            texts = [texts]
        
        # Check cache
        uncached_texts = []
        uncached_indices = []
        embeddings = []
        
        for i, text in enumerate(texts):
            if text in self.embeddings_cache:
                embeddings.append(self.embeddings_cache[text])
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Encode uncached texts
        if uncached_texts:
            new_embeddings = self.model.encode(
                uncached_texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            # Cache new embeddings
            for text, embedding in zip(uncached_texts, new_embeddings):
                self.embeddings_cache[text] = embedding
        
        # Combine cached and new embeddings
        if embeddings:
            result = np.array(embeddings)
            if uncached_texts:
                # Insert new embeddings at correct positions
                final_result = np.zeros((len(texts), new_embeddings.shape[1]))
                cached_idx = 0
                uncached_idx = 0
                for i in range(len(texts)):
                    if i in uncached_indices:
                        final_result[i] = new_embeddings[uncached_idx]
                        uncached_idx += 1
                    else:
                        final_result[i] = result[cached_idx]
                        cached_idx += 1
                return final_result
            return result
        else:
            return new_embeddings
    
    def find_similar(
        self,
        query: str,
        texts: List[str],
        top_k: int = 5,
        threshold: float = 0.0
    ) -> List[Tuple[str, float]]:
        """
        Find most similar texts to a query.
        
        Args:
            query: Query text
            texts: List of texts to search in
            top_k: Number of top results to return
            threshold: Minimum similarity score threshold
            
        Returns:
            List of tuples (text, similarity_score) sorted by similarity
        """
        if not self.model or not texts:
            return []
        
        # Encode query and texts
        query_embedding = self.encode([query])[0]
        text_embeddings = self.encode(texts)
        
        # Calculate cosine similarity
        similarities = np.dot(text_embeddings, query_embedding) / (
            np.linalg.norm(text_embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # Get top-k results
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score >= threshold:
                results.append((texts[idx], score))
        
        return results
    
    def find_similar_with_metadata(
        self,
        query: str,
        items: List[Dict],
        text_field: str = 'text',
        top_k: int = 5,
        threshold: float = 0.0
    ) -> List[Tuple[Dict, float]]:
        """
        Find most similar items with metadata.
        
        Args:
            query: Query text
            items: List of dictionaries containing text and metadata
            text_field: Field name in items that contains the text to search
            top_k: Number of top results to return
            threshold: Minimum similarity score threshold
            
        Returns:
            List of tuples (item_dict, similarity_score) sorted by similarity
        """
        if not self.model or not items:
            return []
        
        texts = [item.get(text_field, '') for item in items]
        results = self.find_similar(query, texts, top_k, threshold)
        
        # Map back to original items
        text_to_item = {item.get(text_field, ''): item for item in items}
        return [(text_to_item[text], score) for text, score in results]
    
    def is_available(self) -> bool:
        """Check if semantic search is available"""
        return self.model is not None


# Global instance
_semantic_search_instance = None


def get_semantic_search(model_name: str = 'all-MiniLM-L6-v2') -> SemanticSearch:
    """Get or create global semantic search instance"""
    global _semantic_search_instance
    if _semantic_search_instance is None:
        _semantic_search_instance = SemanticSearch(model_name)
    return _semantic_search_instance

