"""
Vector Index - FAISS-based vector index for semantic search
"""
import json
import os
import logging
from typing import List, Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class VectorIndex:
    """FAISS vector index for fast similarity search"""

    def __init__(self, embedding_dim: int = 384):
        """
        Initialize vector index

        Args:
            embedding_dim: Dimension of embeddings (default: 384 for all-MiniLM-L6-v2)
        """
        self.embedding_dim = embedding_dim
        self._index = None
        self._id_map: List[str] = []
        self._metadata: Dict[str, Dict] = {}

    @property
    def index(self):
        """Lazy load FAISS index"""
        if self._index is None:
            try:
                import faiss
                # Use HNSW index for fast approximate search
                self._index = faiss.IndexHNSWFlat(self.embedding_dim, 32)
                self._index.hnsw.efSearch = 64  # Search parameter
                logger.info(f"Created FAISS HNSW index (dim={self.embedding_dim})")
            except ImportError:
                logger.error("faiss not installed. Run: pip install faiss-cpu or faiss-gpu")
                raise
        return self._index

    def add(self, ids: List[str], vectors: np.ndarray, metadata: List[Dict] = None):
        """
        Add vectors to index

        Args:
            ids: List of entity IDs
            vectors: numpy array of shape (n, embedding_dim)
            metadata: Optional list of metadata dicts
        """
        if len(ids) != len(vectors):
            raise ValueError(f"Length mismatch: {len(ids)} ids vs {len(vectors)} vectors")

        # Normalize vectors for cosine similarity
        import faiss
        faiss.normalize_L2(vectors)

        # Add to index
        self.index.add(vectors)

        # Update mappings
        for i, entity_id in enumerate(ids):
            self._id_map.append(entity_id)
            if metadata and i < len(metadata):
                self._metadata[entity_id] = metadata[i]

        logger.info(f"Added {len(ids)} vectors. Total: {len(self._id_map)}")

    def search(self, query_vector: np.ndarray, k: int = 10) -> List[Dict]:
        """
        Search for k nearest neighbors

        Args:
            query_vector: Query embedding (1D array)
            k: Number of results to return

        Returns:
            List of {id, score, metadata} dicts
        """
        if len(self._id_map) == 0:
            return []

        import faiss

        # Reshape and normalize query
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        faiss.normalize_L2(query_vector)

        # Search
        k = min(k, len(self._id_map))
        distances, indices = self.index.search(query_vector, k)

        # Build results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._id_map):
                continue

            entity_id = self._id_map[idx]
            # Convert L2 distance to cosine similarity score
            # For normalized vectors: cosine_sim = 1 - (L2_dist^2 / 2)
            score = float(1.0 - (dist * dist) / 2.0)
            score = max(0.0, min(1.0, score))  # Clamp to [0, 1]

            results.append({
                'id': entity_id,
                'score': score,
                'metadata': self._metadata.get(entity_id, {}),
            })

        return results

    def save(self, path: str):
        """Save index to disk"""
        import faiss
        os.makedirs(path, exist_ok=True)

        faiss.write_index(self.index, os.path.join(path, 'faiss.index'))

        with open(os.path.join(path, 'id_map.json'), 'w', encoding='utf-8') as f:
            json.dump(self._id_map, f)

        with open(os.path.join(path, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(self._metadata, f, ensure_ascii=False)

        logger.info(f"Saved index to {path} ({len(self._id_map)} vectors)")

    def load(self, path: str) -> bool:
        """Load index from disk"""
        index_file = os.path.join(path, 'faiss.index')
        id_map_file = os.path.join(path, 'id_map.json')
        metadata_file = os.path.join(path, 'metadata.json')

        if not os.path.exists(index_file):
            logger.warning(f"Index file not found: {index_file}")
            return False

        try:
            import faiss
            self._index = faiss.read_index(index_file)

            with open(id_map_file, 'r', encoding='utf-8') as f:
                self._id_map = json.load(f)

            if os.path.exists(metadata_file):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    self._metadata = json.load(f)

            logger.info(f"Loaded index from {path} ({len(self._id_map)} vectors)")
            return True
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False

    @property
    def size(self) -> int:
        """Get number of vectors in index"""
        return len(self._id_map)
