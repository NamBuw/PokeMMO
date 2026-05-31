"""
Graph Queries - Common query patterns for the knowledge graph
"""
import logging
from typing import List, Dict, Optional, Any

import networkx as nx

logger = logging.getLogger(__name__)


class GraphQueries:
    """Query interface for the knowledge graph"""

    def __init__(self, graph: nx.DiGraph):
        self.graph = graph

    # ========== POKEMON QUERIES ==========

    def get_pokemon_info(self, pokemon_name: str) -> Optional[Dict]:
        """Get complete Pokemon information"""
        pokemon_node = self._find_pokemon_node(pokemon_name)
        if not pokemon_node:
            return None

        node_data = dict(self.graph.nodes[pokemon_node])

        # Get moves
        moves = self._get_pokemon_moves(pokemon_node)

        # Get locations
        locations = self._get_pokemon_locations(pokemon_node)

        # Get items it drops
        drops = self._get_pokemon_drops(pokemon_node)

        return {
            **node_data,
            'moves': moves,
            'locations': locations,
            'drops': drops,
        }

    def get_pokemon_moves(self, pokemon_name: str) -> List[Dict]:
        """Get all moves a Pokemon can learn"""
        pokemon_node = self._find_pokemon_node(pokemon_name)
        if not pokemon_node:
            return []
        return self._get_pokemon_moves(pokemon_node)

    def get_pokemon_locations(self, pokemon_name: str) -> List[Dict]:
        """Get all locations where a Pokemon can be found"""
        pokemon_node = self._find_pokemon_node(pokemon_name)
        if not pokemon_node:
            return []
        return self._get_pokemon_locations(pokemon_node)

    def get_pokemon_counters(self, pokemon_name: str) -> List[Dict]:
        """Find Pokemon that counter the given Pokemon"""
        pokemon_node = self._find_pokemon_node(pokemon_name)
        if not pokemon_node:
            return []

        node = self.graph.nodes[pokemon_node]
        pokemon_types = node.get('types', [])

        # Find types super effective against this Pokemon
        counter_types = set()
        for type_name in pokemon_types:
            type_node = f"type_{type_name.lower()}"
            for source, _, data in self.graph.in_edges(type_node, data=True):
                if data.get('relation') == 'super_effective':
                    counter_type = self.graph.nodes[source].get('name', '')
                    counter_types.add(counter_type)

        # Find Pokemon with those types
        counters = []
        for counter_type in counter_types:
            type_node = f"type_{counter_type.lower()}"
            for source, _, data in self.graph.in_edges(type_node, data=True):
                if data.get('relation') == 'has_type' and 'pokemon' in source:
                    pkmn = dict(self.graph.nodes[source])
                    if pkmn.get('bst', 0) >= 400:  # Only competitive Pokemon
                        counters.append({
                            'name': pkmn['name'],
                            'types': pkmn.get('types', []),
                            'bst': pkmn.get('bst', 0),
                            'counter_type': counter_type,
                        })

        # Deduplicate and sort by BST
        seen = set()
        unique_counters = []
        for c in counters:
            if c['name'] not in seen:
                seen.add(c['name'])
                unique_counters.append(c)

        unique_counters.sort(key=lambda x: x['bst'], reverse=True)
        return unique_counters[:10]

    # ========== MOVE QUERIES ==========

    def get_move_info(self, move_name: str) -> Optional[Dict]:
        """Get complete move information"""
        move_node = self._find_move_node(move_name)
        if not move_node:
            return None

        node_data = dict(self.graph.nodes[move_node])

        # Find Pokemon that learn this move
        learners = []
        for source, _, data in self.graph.in_edges(move_node, data=True):
            if data.get('relation') == 'learns':
                pkmn = dict(self.graph.nodes[source])
                learners.append({
                    'name': pkmn.get('name', ''),
                    'level': data.get('level', 0),
                    'method': data.get('method', ''),
                })

        node_data['learners'] = learners
        return node_data

    def get_best_moves_for_type(self, move_type: str, category: str = None) -> List[Dict]:
        """Get best moves of a given type, optionally filtered by category"""
        type_node = f"type_{move_type.lower()}"
        if type_node not in self.graph:
            return []

        moves = []
        for source, _, data in self.graph.in_edges(type_node, data=True):
            if data.get('relation') == 'has_type':
                move_node = self.graph.nodes[source]
                if move_node.get('node_type') == 'move':
                    if category and move_node.get('category') != category:
                        continue
                    moves.append({
                        'name': move_node.get('name', ''),
                        'type': move_node.get('move_type', ''),
                        'category': move_node.get('category', ''),
                        'power': move_node.get('power', 0),
                    })

        moves.sort(key=lambda x: x['power'], reverse=True)
        return moves[:10]

    # ========== TYPE QUERIES ==========

    def get_type_matchups(self, type_name: str) -> Dict:
        """Get type effectiveness for a given type"""
        type_node = f"type_{type_name.lower()}"
        if type_node not in self.graph:
            return {}

        super_effective = []
        not_effective = []
        immune = []

        # Attacking matchups
        for _, target, data in self.graph.out_edges(type_node, data=True):
            relation = data.get('relation')
            target_name = self.graph.nodes[target].get('name', '')

            if relation == 'super_effective':
                super_effective.append(target_name)
            elif relation == 'not_effective':
                not_effective.append(target_name)
            elif relation == 'immune':
                immune.append(target_name)

        # Defensive matchups (what is super effective against this type)
        weak_to = []
        resists = []

        for source, _, data in self.graph.in_edges(type_node, data=True):
            relation = data.get('relation')
            source_name = self.graph.nodes[source].get('name', '')

            if relation == 'super_effective':
                weak_to.append(source_name)
            elif relation == 'not_effective':
                resists.append(source_name)

        return {
            'type': type_name,
            'offensive': {
                'super_effective_against': super_effective,
                'not_effective_against': not_effective,
                'immune': immune,
            },
            'defensive': {
                'weak_to': weak_to,
                'resists': resists,
            }
        }

    # ========== LOCATION QUERIES ==========

    def get_location_pokemon(self, location_name: str) -> List[Dict]:
        """Get all Pokemon found at a location"""
        loc_node = self._find_location_node(location_name)
        if not loc_node:
            return []

        pokemon_list = []
        for source, _, data in self.graph.in_edges(loc_node, data=True):
            if data.get('relation') == 'found_at':
                pkmn = dict(self.graph.nodes[source])
                pokemon_list.append({
                    'name': pkmn.get('name', ''),
                    'types': pkmn.get('types', []),
                    'min_level': data.get('min_level', 0),
                    'max_level': data.get('max_level', 0),
                    'rarity': data.get('rarity', ''),
                })

        return pokemon_list

    def find_farming_location(self, target_type: str = None, min_level: int = 0,
                               max_level: int = 100, region: str = None) -> List[Dict]:
        """Find optimal farming locations"""
        locations = []

        for node_id, node_data in self.graph.nodes(data=True):
            if node_data.get('node_type') != 'location':
                continue

            if region and node_data.get('region', '').upper() != region.upper():
                continue

            loc_pokemon = self.get_location_pokemon(node_data.get('name', ''))
            if not loc_pokemon:
                continue

            # Filter by level range
            valid_encounters = [
                p for p in loc_pokemon
                if min_level <= p['min_level'] <= max_level
                or min_level <= p['max_level'] <= max_level
            ]

            if not valid_encounters:
                continue

            # Filter by type if specified
            if target_type:
                valid_encounters = [
                    p for p in valid_encounters
                    if target_type in p.get('types', [])
                ]

            if valid_encounters:
                locations.append({
                    'location': node_data.get('name', ''),
                    'region': node_data.get('region', ''),
                    'encounters': valid_encounters,
                    'encounter_count': len(valid_encounters),
                })

        locations.sort(key=lambda x: x['encounter_count'], reverse=True)
        return locations[:5]

    # ========== STRATEGY QUERIES ==========

    def get_weather_team(self, weather: str) -> Optional[Dict]:
        """Get recommended team for a weather strategy"""
        for node_id, node_data in self.graph.nodes(data=True):
            if node_data.get('node_type') == 'strategy':
                if node_data.get('weather', '').lower() == weather.lower():
                    # Get team members
                    members = []
                    for _, target, data in self.graph.out_edges(node_id, data=True):
                        if data.get('relation') == 'team_member':
                            pkmn = dict(self.graph.nodes[target])
                            members.append({
                                'name': pkmn.get('name', ''),
                                'types': pkmn.get('types', []),
                                'role': data.get('role', ''),
                                'moves': data.get('moves', []),
                                'nature': data.get('nature', ''),
                                'evs': data.get('evs', {}),
                            })

                    return {
                        'weather': node_data.get('weather', ''),
                        'vietnamese_name': node_data.get('vietnamese_name', ''),
                        'strategy': node_data.get('strategy', ''),
                        'members': members,
                    }

        return None

    # ========== INTERNAL HELPERS ==========

    def _find_pokemon_node(self, name: str) -> Optional[str]:
        """Find Pokemon node by name (case-insensitive)"""
        name_lower = name.lower().replace(' ', '').replace('-', '')
        for node_id, data in self.graph.nodes(data=True):
            if data.get('node_type') == 'pokemon':
                node_name = data.get('name', '').lower().replace(' ', '').replace('-', '')
                if node_name == name_lower or node_id == f"pokemon_{name_lower}":
                    return node_id
        return None

    def _find_move_node(self, name: str) -> Optional[str]:
        """Find Move node by name (case-insensitive)"""
        name_lower = name.lower().replace(' ', '').replace('-', '')
        for node_id, data in self.graph.nodes(data=True):
            if data.get('node_type') == 'move':
                node_name = data.get('name', '').lower().replace(' ', '').replace('-', '')
                if node_name == name_lower or node_id == f"move_{name_lower}":
                    return node_id
        return None

    def _find_item_node(self, name: str) -> Optional[str]:
        """Find Item node by name (case-insensitive)"""
        name_lower = name.lower().replace(' ', '_').replace('-', '_')
        for node_id, data in self.graph.nodes(data=True):
            if data.get('node_type') == 'item':
                node_name = data.get('name', '').lower().replace(' ', '_').replace('-', '_')
                if node_name == name_lower or node_id == f"item_{name_lower}":
                    return node_id
        return None

    def _find_location_node(self, name: str) -> Optional[str]:
        """Find Location node by name (case-insensitive)"""
        name_lower = name.lower().replace(' ', '_')
        for node_id, data in self.graph.nodes(data=True):
            if data.get('node_type') == 'location':
                node_name = data.get('name', '').lower().replace(' ', '_')
                if node_name == name_lower or node_id == f"location_{name_lower}":
                    return node_id
        return None

    def _get_pokemon_moves(self, pokemon_node: str) -> List[Dict]:
        """Get all moves for a Pokemon node"""
        moves = []
        for _, target, data in self.graph.out_edges(pokemon_node, data=True):
            if data.get('relation') == 'learns':
                move = dict(self.graph.nodes[target])
                moves.append({
                    'name': move.get('name', ''),
                    'type': move.get('move_type', ''),
                    'category': move.get('category', ''),
                    'power': move.get('power', 0),
                    'level': data.get('level', 0),
                    'method': data.get('method', ''),
                })

        moves.sort(key=lambda x: x['level'], reverse=True)
        return moves

    def _get_pokemon_locations(self, pokemon_node: str) -> List[Dict]:
        """Get all locations for a Pokemon node"""
        locations = []
        for _, target, data in self.graph.out_edges(pokemon_node, data=True):
            if data.get('relation') == 'found_at':
                loc = dict(self.graph.nodes[target])
                locations.append({
                    'location': loc.get('name', ''),
                    'region': loc.get('region', ''),
                    'min_level': data.get('min_level', 0),
                    'max_level': data.get('max_level', 0),
                    'rarity': data.get('rarity', ''),
                })

        return locations

    def _get_pokemon_drops(self, pokemon_node: str) -> List[Dict]:
        """Get items dropped by a Pokemon"""
        drops = []
        for _, target, data in self.graph.out_edges(pokemon_node, data=True):
            if data.get('relation') == 'drops':
                item = dict(self.graph.nodes[target])
                drops.append({
                    'name': item.get('name', ''),
                    'effect': item.get('effect', ''),
                })

        return drops
