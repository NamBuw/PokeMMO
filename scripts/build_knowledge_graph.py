"""
Build Knowledge Graph from PokeMMO game data
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Build and test Knowledge Graph"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

    logger.info(f"Data directory: {data_dir}")
    logger.info("=" * 60)

    # Build Knowledge Graph
    logger.info("Building Knowledge Graph...")
    start_time = time.time()

    builder = KnowledgeGraphBuilder(data_dir)
    graph = builder.build()

    build_time = time.time() - start_time
    logger.info(f"Knowledge Graph built in {build_time:.2f} seconds")
    logger.info(f"Nodes: {graph.number_of_nodes()}")
    logger.info(f"Edges: {graph.number_of_edges()}")
    logger.info("=" * 60)

    # Initialize queries
    queries = GraphQueries(graph)

    # Test queries
    logger.info("\n--- Testing Knowledge Graph Queries ---\n")

    # Test 1: Pokemon info
    logger.info("Test 1: Get Pokemon info (Garchomp)")
    garchomp = queries.get_pokemon_info("Garchomp")
    if garchomp:
        logger.info(f"  Name: {garchomp['name']}")
        logger.info(f"  Types: {garchomp['types']}")
        logger.info(f"  BST: {garchomp['bst']}")
        logger.info(f"  Abilities: {garchomp['abilities']}")
        logger.info(f"  Moves: {len(garchomp.get('moves', []))} moves")
        logger.info(f"  Locations: {len(garchomp.get('locations', []))} locations")
    else:
        logger.warning("  Garchomp not found!")

    # Test 2: Type matchups
    logger.info("\nTest 2: Type matchups (Dragon)")
    dragon_matchups = queries.get_type_matchups("Dragon")
    if dragon_matchups:
        offensive = dragon_matchups.get('offensive', {})
        logger.info(f"  Super Effective against: {offensive.get('super_effective_against', [])}")
        defensive = dragon_matchups.get('defensive', {})
        logger.info(f"  Weak to: {defensive.get('weak_to', [])}")

    # Test 3: Pokemon counters
    logger.info("\nTest 3: Find counters for Garchomp")
    counters = queries.get_pokemon_counters("Garchomp")
    if counters:
        logger.info(f"  Found {len(counters)} counters:")
        for c in counters[:5]:
            logger.info(f"    - {c['name']} ({'/'.join(c['types'])}) BST:{c['bst']}")

    # Test 4: Best moves by type
    logger.info("\nTest 4: Best Ground moves")
    ground_moves = queries.get_best_moves_for_type("Ground", "Physical")
    if ground_moves:
        logger.info(f"  Top 5 Ground Physical moves:")
        for m in ground_moves[:5]:
            logger.info(f"    - {m['name']} (Power: {m['power']})")

    # Test 5: Location search
    logger.info("\nTest 5: Pokemon locations (Gible)")
    gible_locations = queries.get_pokemon_locations("Gible")
    if gible_locations:
        logger.info(f"  Gible found at:")
        for loc in gible_locations:
            logger.info(f"    - {loc['location']} ({loc['region']}) Lv.{loc['min_level']}-{loc['max_level']}")

    # Test 6: Weather team
    logger.info("\nTest 6: Rain team strategy")
    rain_team = queries.get_weather_team("Rain")
    if rain_team:
        logger.info(f"  Weather: {rain_team['weather']}")
        logger.info(f"  Strategy: {rain_team['strategy'][:100]}...")
        logger.info(f"  Members:")
        for member in rain_team['members']:
            logger.info(f"    - {member['name']} ({member['role']})")

    # Test 7: Farming locations
    logger.info("\nTest 7: Farming locations for Fire types (Lv20-30)")
    farming = queries.find_farming_location(
        target_type="Fire",
        min_level=20,
        max_level=30,
        region="Kanto"
    )
    if farming:
        logger.info(f"  Found {len(farming)} locations:")
        for loc in farming[:3]:
            logger.info(f"    - {loc['location']} ({loc['region']})")
            for enc in loc['encounters'][:2]:
                logger.info(f"      {enc['name']} Lv.{enc.get('min_level')}-{enc.get('max_level')}")

    logger.info("\n" + "=" * 60)
    logger.info("Knowledge Graph tests completed!")

    # Save graph stats
    stats = {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "build_time_seconds": build_time,
        "node_types": {},
    }

    for _, data in graph.nodes(data=True):
        node_type = data.get('node_type', 'unknown')
        stats['node_types'][node_type] = stats['node_types'].get(node_type, 0) + 1

    stats_file = os.path.join(data_dir, 'knowledge_graph_stats.json')
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    logger.info(f"Stats saved to {stats_file}")


if __name__ == '__main__':
    main()
