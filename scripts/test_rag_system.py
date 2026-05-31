"""
Test RAG System - Demonstrate Knowledge Graph + Vector Search capabilities
"""
import sys
import os
import json
import time
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.knowledge.graph.builder import KnowledgeGraphBuilder
from bot.knowledge.graph.queries import GraphQueries
from bot.knowledge.vector.embeddings import EmbeddingGenerator
from bot.knowledge.vector.index import VectorIndex

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class RAGSystem:
    """Combined Knowledge Graph + Vector Search RAG System"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.graph = None
        self.graph_queries = None
        self.embedder = None
        self.vector_index = None

    def initialize(self):
        """Initialize all components"""
        logger.info("Initializing RAG System...")

        # Build Knowledge Graph
        logger.info("1. Building Knowledge Graph...")
        builder = KnowledgeGraphBuilder(self.data_dir)
        self.graph = builder.build()
        self.graph_queries = GraphQueries(self.graph)

        # Load Vector Index
        logger.info("2. Loading Vector Index...")
        self.embedder = EmbeddingGenerator(model_name="all-MiniLM-L6-v2")
        self.vector_index = VectorIndex(embedding_dim=self.embedder.embedding_dim)

        index_dir = os.path.join(self.data_dir, 'vector_index')
        if os.path.exists(os.path.join(index_dir, 'faiss.index')):
            self.vector_index.load(index_dir)
            logger.info(f"   Loaded vector index: {self.vector_index.size} vectors")
        else:
            logger.warning("   Vector index not found!")

        logger.info("RAG System initialized!")

    def query(self, question: str, top_k: int = 5) -> dict:
        """
        Answer a question using RAG

        Args:
            question: User question
            top_k: Number of results to return

        Returns:
            Dict with answer and sources
        """
        start_time = time.time()

        # 1. Try graph queries first (fast, structured)
        graph_results = self._query_graph(question)

        # 2. Vector search (semantic)
        vector_results = self._query_vector(question, top_k)

        # 3. Combine results
        combined = self._combine_results(graph_results, vector_results)

        query_time = time.time() - start_time

        return {
            'question': question,
            'graph_results': graph_results,
            'vector_results': vector_results,
            'combined': combined,
            'query_time_ms': query_time * 1000,
        }

    def _query_graph(self, question: str) -> dict:
        """Try to answer using graph queries"""
        question_lower = question.lower()
        results = {}

        # Check for Pokemon queries
        pokemon_keywords = ['pokemon', 'who is', 'tell me about', 'stats', 'info']
        if any(kw in question_lower for kw in pokemon_keywords):
            # Extract Pokemon name (simple heuristic)
            for node_id, data in self.graph.nodes(data=True):
                if data.get('node_type') == 'pokemon':
                    name = data.get('name', '').lower()
                    if name in question_lower:
                        results['pokemon_info'] = self.graph_queries.get_pokemon_info(data['name'])
                        break

        # Check for type queries
        type_keywords = ['type', 'effective', 'weakness', 'matchup', 'super effective']
        if any(kw in question_lower for kw in type_keywords):
            types = ['normal', 'fire', 'water', 'electric', 'grass', 'ice',
                     'fighting', 'poison', 'ground', 'flying', 'psychic',
                     'bug', 'rock', 'ghost', 'dragon', 'dark', 'steel', 'fairy']
            for type_name in types:
                if type_name in question_lower:
                    results['type_matchup'] = self.graph_queries.get_type_matchups(type_name.capitalize())
                    break

        # Check for move queries
        move_keywords = ['move', 'attack', 'best', 'power']
        if any(kw in question_lower for kw in move_keywords):
            types = ['normal', 'fire', 'water', 'electric', 'grass', 'ice',
                     'fighting', 'poison', 'ground', 'flying', 'psychic',
                     'bug', 'rock', 'ghost', 'dragon', 'dark', 'steel', 'fairy']
            for type_name in types:
                if type_name in question_lower:
                    category = None
                    if 'physical' in question_lower:
                        category = 'Physical'
                    elif 'special' in question_lower:
                        category = 'Special'
                    elif 'status' in question_lower:
                        category = 'Status'

                    results['best_moves'] = self.graph_queries.get_best_moves_for_type(
                        type_name.capitalize(), category
                    )
                    break

        # Check for counter queries
        counter_keywords = ['counter', 'beat', 'defeat', 'against', 'how to beat']
        if any(kw in question_lower for kw in counter_keywords):
            for node_id, data in self.graph.nodes(data=True):
                if data.get('node_type') == 'pokemon':
                    name = data.get('name', '').lower()
                    if name in question_lower:
                        results['counters'] = self.graph_queries.get_pokemon_counters(data['name'])
                        break

        # Check for location queries
        location_keywords = ['where', 'find', 'location', 'catch']
        if any(kw in question_lower for kw in location_keywords):
            for node_id, data in self.graph.nodes(data=True):
                if data.get('node_type') == 'pokemon':
                    name = data.get('name', '').lower()
                    if name in question_lower:
                        results['locations'] = self.graph_queries.get_pokemon_locations(data['name'])
                        break

        # Check for team/strategy queries
        team_keywords = ['team', 'rain', 'sun', 'sand', 'hail', 'weather', 'strategy']
        if any(kw in question_lower for kw in team_keywords):
            for weather in ['Rain', 'Sun', 'Sand', 'Hail']:
                if weather.lower() in question_lower:
                    results['team_strategy'] = self.graph_queries.get_weather_team(weather)
                    break

        return results

    def _query_vector(self, question: str, top_k: int) -> list:
        """Semantic search using vector index"""
        if not self.vector_index or self.vector_index.size == 0:
            return []

        query_embedding = self.embedder.encode_single(question)
        results = self.vector_index.search(query_embedding, k=top_k)

        # Enrich with graph data
        enriched = []
        for result in results:
            entity_id = result['id']
            if entity_id in self.graph:
                node_data = dict(self.graph.nodes[entity_id])
                enriched.append({
                    'id': entity_id,
                    'score': result['score'],
                    'type': node_data.get('node_type', ''),
                    'name': node_data.get('name', ''),
                    'data': node_data,
                })

        return enriched

    def _combine_results(self, graph_results: dict, vector_results: list) -> list:
        """Combine and rank results from both sources"""
        combined = []

        # Add graph results (high priority)
        for key, value in graph_results.items():
            combined.append({
                'source': 'graph',
                'type': key,
                'data': value,
                'relevance': 1.0,  # Graph results are exact matches
            })

        # Add vector results (lower priority)
        for result in vector_results:
            combined.append({
                'source': 'vector',
                'type': result['type'],
                'name': result['name'],
                'score': result['score'],
                'data': result['data'],
                'relevance': result['score'],
            })

        # Sort by relevance
        combined.sort(key=lambda x: x.get('relevance', 0), reverse=True)

        return combined[:10]  # Return top 10


def main():
    """Test the RAG system with various queries"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

    # Initialize RAG system
    rag = RAGSystem(data_dir)
    rag.initialize()

    logger.info("\n" + "=" * 70)
    logger.info("TESTING RAG SYSTEM")
    logger.info("=" * 70)

    # Test queries
    test_queries = [
        # Pokemon info queries
        "Tell me about Garchomp",
        "What are Garchomp's stats?",
        "Who is Dragonite?",

        # Type effectiveness queries
        "What is Dragon type super effective against?",
        "What are Fire type weaknesses?",
        "Show me Ground type matchups",

        # Move queries
        "Best Fire type physical moves",
        "Show me high power Electric moves",
        "What are the strongest Water moves?",

        # Counter queries
        "How to beat Garchomp?",
        "What counters Dragonite?",
        "How to defeat Tyranitar?",

        # Location queries
        "Where can I find Gible?",
        "Location of Bagon",
        "Where to catch Dratini?",

        # Team strategy queries
        "Show me Rain team strategy",
        "What is a good Sun team?",
        "Sand team composition",

        # General queries
        "Best competitive Pokemon",
        "Pokemon with highest attack",
        "Popular held items in competitive",
    ]

    for i, query in enumerate(test_queries, 1):
        logger.info(f"\n{'─' * 70}")
        logger.info(f"Query {i}: {query}")
        logger.info(f"{'─' * 70}")

        result = rag.query(query)

        # Show graph results
        if result['graph_results']:
            logger.info("\n📊 Graph Results:")
            for key, value in result['graph_results'].items():
                if key == 'pokemon_info':
                    logger.info(f"  Pokemon: {value['name']}")
                    logger.info(f"    Types: {'/'.join(value['types'])}")
                    logger.info(f"    BST: {value['bst']}")
                    logger.info(f"    Abilities: {', '.join(value['abilities'])}")
                    if value.get('moves'):
                        logger.info(f"    Moves: {len(value['moves'])} moves")
                    if value.get('locations'):
                        logger.info(f"    Locations: {len(value['locations'])} locations")

                elif key == 'type_matchup':
                    offensive = value.get('offensive', {})
                    logger.info(f"  Type: {value['type']}")
                    logger.info(f"    Super Effective: {', '.join(offensive.get('super_effective_against', []))}")
                    defensive = value.get('defensive', {})
                    logger.info(f"    Weak to: {', '.join(defensive.get('weak_to', []))}")

                elif key == 'best_moves':
                    logger.info(f"  Best Moves:")
                    for m in value[:3]:
                        logger.info(f"    - {m['name']} (Power: {m['power']})")

                elif key == 'counters':
                    logger.info(f"  Counters:")
                    for c in value[:3]:
                        logger.info(f"    - {c['name']} ({'/'.join(c['types'])}) BST:{c['bst']}")

                elif key == 'locations':
                    logger.info(f"  Locations:")
                    for loc in value[:3]:
                        logger.info(f"    - {loc['location']} ({loc['region']})")

                elif key == 'team_strategy':
                    logger.info(f"  Team: {value['weather']}")
                    logger.info(f"    Members: {', '.join(m['name'] for m in value['members'])}")

        # Show vector results
        if result['vector_results']:
            logger.info("\n🔍 Vector Search Results:")
            for v in result['vector_results'][:3]:
                logger.info(f"  - {v['name']} ({v['type']}) Score: {v['score']:.3f}")

        logger.info(f"\n⏱️  Query time: {result['query_time_ms']:.2f}ms")

    # Summary statistics
    logger.info("\n" + "=" * 70)
    logger.info("RAG SYSTEM STATISTICS")
    logger.info("=" * 70)
    logger.info(f"Knowledge Graph: {rag.graph.number_of_nodes()} nodes, {rag.graph.number_of_edges()} edges")
    logger.info(f"Vector Index: {rag.vector_index.size} vectors")

    node_types = {}
    for _, data in rag.graph.nodes(data=True):
        nt = data.get('node_type', 'unknown')
        node_types[nt] = node_types.get(nt, 0) + 1

    logger.info("Node types:")
    for nt, count in node_types.items():
        logger.info(f"  - {nt}: {count}")


if __name__ == '__main__':
    main()
