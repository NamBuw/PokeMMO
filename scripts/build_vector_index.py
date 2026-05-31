"""
Build Vector Index for semantic search over game knowledge
"""
import sys
import os
import json
import time
import logging
import pickle

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.knowledge.graph.builder import KnowledgeGraphBuilder
from bot.knowledge.vector.embeddings import EmbeddingGenerator
from bot.knowledge.vector.index import VectorIndex

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Build Vector Index from Knowledge Graph"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    index_dir = os.path.join(data_dir, 'vector_index')

    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Index directory: {index_dir}")
    logger.info("=" * 60)

    # Build Knowledge Graph first
    logger.info("Building Knowledge Graph...")
    builder = KnowledgeGraphBuilder(data_dir)
    graph = builder.build()

    # Initialize embedding generator
    logger.info("\nLoading embedding model...")
    embedder = EmbeddingGenerator(model_name="all-MiniLM-L6-v2")
    logger.info(f"Embedding dimension: {embedder.embedding_dim}")

    # Initialize vector index
    vector_index = VectorIndex(embedding_dim=embedder.embedding_dim)

    # Collect all entities to embed
    logger.info("\nCollecting entities to embed...")
    entities = []

    for node_id, node_data in graph.nodes(data=True):
        node_type = node_data.get('node_type', '')

        if node_type == 'pokemon':
            text = embedder.pokemon_to_text(node_data)
            entities.append({
                'id': node_id,
                'type': 'pokemon',
                'name': node_data.get('name', ''),
                'text': text,
            })
        elif node_type == 'move':
            text = embedder.move_to_text(node_data)
            entities.append({
                'id': node_id,
                'type': 'move',
                'name': node_data.get('name', ''),
                'text': text,
            })
        elif node_type == 'ability':
            text = embedder.ability_to_text(node_data)
            entities.append({
                'id': node_id,
                'type': 'ability',
                'name': node_data.get('name', ''),
                'text': text,
            })
        elif node_type == 'item':
            text = embedder.item_to_text(node_data)
            entities.append({
                'id': node_id,
                'type': 'item',
                'name': node_data.get('name', ''),
                'text': text,
            })

    logger.info(f"Found {len(entities)} entities to embed")

    # Generate embeddings in batches
    logger.info("\nGenerating embeddings...")
    start_time = time.time()

    batch_size = 100
    all_ids = []
    all_vectors = []
    all_metadata = []

    for i in range(0, len(entities), batch_size):
        batch = entities[i:i + batch_size]
        texts = [e['text'] for e in batch]

        # Generate embeddings
        vectors = embedder.encode(texts)

        # Collect results
        for j, entity in enumerate(batch):
            all_ids.append(entity['id'])
            all_vectors.append(vectors[j])
            all_metadata.append({
                'type': entity['type'],
                'name': entity['name'],
            })

        logger.info(f"  Processed {min(i + batch_size, len(entities))}/{len(entities)} entities")

    # Convert to numpy array
    import numpy as np
    all_vectors = np.array(all_vectors)

    # Add to index
    logger.info("\nAdding vectors to index...")
    vector_index.add(all_ids, all_vectors, all_metadata)

    embedding_time = time.time() - start_time
    logger.info(f"Embeddings generated in {embedding_time:.2f} seconds")

    # Save index
    logger.info(f"\nSaving index to {index_dir}...")
    os.makedirs(index_dir, exist_ok=True)
    vector_index.save(index_dir)

    # Save entity mapping
    entity_map_file = os.path.join(index_dir, 'entity_map.json')
    with open(entity_map_file, 'w', encoding='utf-8') as f:
        json.dump(all_metadata, f, ensure_ascii=False, indent=2)

    logger.info(f"Index saved. Total vectors: {vector_index.size}")

    # Test search
    logger.info("\n" + "=" * 60)
    logger.info("Testing semantic search...")

    test_queries = [
        "Best Pokemon for competitive battling",
        "How to catch rare Pokemon",
        "Fire type moves with high power",
        "Pokemon that learn Earthquake",
        "Best held items for Garchomp",
    ]

    for query in test_queries:
        logger.info(f"\nQuery: '{query}'")
        results = vector_index.search(embedder.encode_single(query), k=3)

        for result in results:
            entity_id = result['id']
            score = result['score']
            metadata = result['metadata']
            logger.info(f"  - {metadata.get('name', entity_id)} ({metadata.get('type', '')}) Score: {score:.3f}")

    logger.info("\n" + "=" * 60)
    logger.info("Vector index build completed!")

    # Save stats
    stats = {
        "total_vectors": vector_index.size,
        "embedding_dim": embedder.embedding_dim,
        "embedding_time_seconds": embedding_time,
        "entity_counts": {},
    }

    for entity in all_metadata:
        entity_type = entity['type']
        stats['entity_counts'][entity_type] = stats['entity_counts'].get(entity_type, 0) + 1

    stats_file = os.path.join(index_dir, 'index_stats.json')
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    logger.info(f"Stats saved to {stats_file}")


if __name__ == '__main__':
    main()
