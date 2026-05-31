"""
Knowledge Graph Builder
Builds a NetworkX graph from JSON game data
"""
import json
import os
import logging
from typing import Dict, Any

import networkx as nx

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """Build knowledge graph from game data JSON files"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.graph = nx.DiGraph()
        self.data: Dict[str, Any] = {}

    def build(self) -> nx.DiGraph:
        """Build complete knowledge graph"""
        logger.info("Loading game data...")
        self._load_all_data()

        logger.info("Building knowledge graph...")
        self._build_type_nodes()
        self._build_ability_nodes()
        self._build_move_nodes()
        self._build_item_nodes()
        self._build_pokemon_nodes()
        self._build_location_nodes()
        self._build_learnset_edges()
        self._build_location_edges()
        self._build_type_effectiveness_edges()
        self._build_item_drop_edges()
        self._build_team_edges()

        logger.info(
            f"Knowledge graph built: "
            f"{self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges"
        )
        return self.graph

    def _load_json(self, filename: str) -> Any:
        """Load a JSON file"""
        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_all_data(self):
        """Load all game data files"""
        try:
            self.data['species'] = {p['id']: p for p in self._load_json('species.json')}
            logger.info(f"  Loaded species: {len(self.data['species'])}")
        except Exception as e:
            logger.error(f"  Failed to load species: {e}")
            self.data['species'] = {}

        try:
            self.data['moves'] = {m['id']: m for m in self._load_json('moves.json')}
            logger.info(f"  Loaded moves: {len(self.data['moves'])}")
        except Exception as e:
            logger.error(f"  Failed to load moves: {e}")
            self.data['moves'] = {}

        try:
            self.data['abilities'] = {a['id']: a for a in self._load_json('abilities.json')}
            logger.info(f"  Loaded abilities: {len(self.data['abilities'])}")
        except Exception as e:
            logger.error(f"  Failed to load abilities: {e}")
            self.data['abilities'] = {}

        try:
            self.data['type_matrix'] = self._load_json('type_matrix.json')
            logger.info(f"  Loaded type_matrix")
        except Exception as e:
            logger.error(f"  Failed to load type_matrix: {e}")
            self.data['type_matrix'] = {}

        try:
            self.data['locations'] = self._load_json('location_data.json')
            logger.info(f"  Loaded locations: {len(self.data['locations'])}")
        except Exception as e:
            logger.error(f"  Failed to load locations: {e}")
            self.data['locations'] = {}

        try:
            self.data['learnsets'] = self._load_json('learnsets.json')
            logger.info(f"  Loaded learnsets: {len(self.data['learnsets'])}")
        except Exception as e:
            logger.error(f"  Failed to load learnsets: {e}")
            self.data['learnsets'] = {}

        try:
            self.data['held_items'] = {i['name']: i for i in self._load_json('held_items.json')}
            logger.info(f"  Loaded held_items: {len(self.data['held_items'])}")
        except Exception as e:
            logger.error(f"  Failed to load held_items: {e}")
            self.data['held_items'] = {}

        try:
            self.data['recommended_teams'] = self._load_json('recommended_teams.json')
            logger.info(f"  Loaded recommended_teams: {len(self.data['recommended_teams'])}")
        except Exception as e:
            logger.error(f"  Failed to load recommended_teams: {e}")
            self.data['recommended_teams'] = []

    def _build_type_nodes(self):
        """Create type nodes from type_matrix keys"""
        type_matrix = self.data.get('type_matrix', {})
        types = set(type_matrix.keys())
        for inner in type_matrix.values():
            types.update(inner.keys())

        for type_name in types:
            self.graph.add_node(
                f"type_{type_name.lower()}",
                node_type="type",
                name=type_name,
            )
        logger.info(f"  Built {len(types)} type nodes")

    def _build_ability_nodes(self):
        """Create ability nodes from abilities.json"""
        for ability_id, ability in self.data.get('abilities', {}).items():
            self.graph.add_node(
                f"ability_{ability_id}",
                node_type="ability",
                name=ability['name'],
                effect=ability.get('effect', ''),
            )
        logger.info(f"  Built {len(self.data.get('abilities', {}))} ability nodes")

    def _build_move_nodes(self):
        """Create move nodes from moves.json"""
        for move_id, move in self.data.get('moves', {}).items():
            self.graph.add_node(
                f"move_{move_id}",
                node_type="move",
                name=move['name'],
                move_type=move['type'],
                category=move['category'],
                power=move.get('basePower', 0),
                flags=move.get('flags', {}),
            )
            # Move -> Type edge
            type_node = f"type_{move['type'].lower()}"
            if type_node in self.graph:
                self.graph.add_edge(
                    f"move_{move_id}",
                    type_node,
                    relation="has_type",
                )
        logger.info(f"  Built {len(self.data.get('moves', {}))} move nodes")

    def _build_item_nodes(self):
        """Create item nodes from held_items"""
        for name, item in self.data.get('held_items', {}).items():
            item_id = name.lower().replace(' ', '_')
            self.graph.add_node(
                f"item_{item_id}",
                node_type="item",
                name=name,
                category="held",
                effect=item.get('effect', ''),
                price=item.get('price', ''),
            )
        logger.info(f"  Built {len(self.data.get('held_items', {}))} item nodes")

    def _build_pokemon_nodes(self):
        """Create Pokemon nodes from species.json"""
        for species_id, species in self.data.get('species', {}).items():
            bst = sum(species['baseStats'].values())
            self.graph.add_node(
                f"pokemon_{species_id}",
                node_type="pokemon",
                name=species['name'],
                types=species['types'],
                base_stats=species['baseStats'],
                bst=bst,
                abilities=species['abilities'],
                weightkg=species.get('weightkg', 0),
                nfe=species.get('nfe', False),
            )

            # Pokemon -> Type edges
            for i, type_name in enumerate(species['types']):
                type_node = f"type_{type_name.lower()}"
                if type_node in self.graph:
                    self.graph.add_edge(
                        f"pokemon_{species_id}",
                        type_node,
                        relation="has_type",
                        slot=i + 1,
                    )

            # Pokemon -> Ability edges
            for i, ability_name in enumerate(species['abilities']):
                ability_id = ability_name.lower().replace(' ', '_')
                ability_node = f"ability_{ability_id}"
                if ability_node in self.graph:
                    self.graph.add_edge(
                        f"pokemon_{species_id}",
                        ability_node,
                        relation="has_ability",
                        slot=i + 1,
                    )
        logger.info(f"  Built {len(self.data.get('species', {}))} Pokemon nodes")

    def _build_location_nodes(self):
        """Create location nodes from location_data.json"""
        for loc_key, loc_data in self.data.get('locations', {}).items():
            self.graph.add_node(
                f"location_{loc_key.lower()}",
                node_type="location",
                name=loc_data.get('name', loc_key),
                region=loc_data.get('region', ''),
            )
        logger.info(f"  Built {len(self.data.get('locations', {}))} location nodes")

    def _build_learnset_edges(self):
        """Create Pokemon -> Move edges from learnsets.json"""
        learnsets = self.data.get('learnsets', {})
        species = self.data.get('species', {})

        # Build name -> id mapping
        name_to_id = {s['name'].lower(): sid for sid, s in species.items()}

        edge_count = 0
        for pokemon_name, gens in learnsets.items():
            pokemon_id = name_to_id.get(pokemon_name.lower())
            if not pokemon_id:
                continue

            pokemon_node = f"pokemon_{pokemon_id}"
            if pokemon_node not in self.graph:
                continue

            for gen_data in gens.values():
                for entry in gen_data:
                    move_name = entry.get('move', '')
                    move_id = move_name.lower().replace(' ', '_')
                    move_node = f"move_{move_id}"

                    if move_node in self.graph:
                        self.graph.add_edge(
                            pokemon_node,
                            move_node,
                            relation="learns",
                            level=entry.get('level', 0),
                            method="level_up" if entry.get('level', 0) > 0 else "evolution",
                        )
                        edge_count += 1

        logger.info(f"  Built {edge_count} learnset edges")

    def _build_location_edges(self):
        """Create Pokemon -> Location edges from location_data.json"""
        locations = self.data.get('locations', {})
        edge_count = 0

        for loc_key, loc_data in locations.items():
            loc_node = f"location_{loc_key.lower()}"
            if loc_node not in self.graph:
                continue

            for encounter in loc_data.get('encounters', []):
                pokemon_id = encounter.get('pokemon', '')
                pokemon_node = f"pokemon_{pokemon_id}"

                if pokemon_node in self.graph:
                    self.graph.add_edge(
                        pokemon_node,
                        loc_node,
                        relation="found_at",
                        min_level=encounter.get('min_level', 0),
                        max_level=encounter.get('max_level', 0),
                        rarity=encounter.get('rarity', ''),
                        encounter_type=encounter.get('type', ''),
                        time=encounter.get('time', 'ALL'),
                    )
                    edge_count += 1

        logger.info(f"  Built {edge_count} location edges")

    def _build_type_effectiveness_edges(self):
        """Create Type -> Type effectiveness edges from type_matrix.json"""
        type_matrix = self.data.get('type_matrix', {})
        edge_count = 0

        for attack_type, defenders in type_matrix.items():
            attack_node = f"type_{attack_type.lower()}"
            if attack_node not in self.graph:
                continue

            for defend_type, multiplier in defenders.items():
                defend_node = f"type_{defend_type.lower()}"
                if defend_node not in self.graph:
                    continue

                if multiplier == 0:
                    relation = "immune"
                elif multiplier > 1:
                    relation = "super_effective"
                elif multiplier < 1:
                    relation = "not_effective"
                else:
                    continue  # Skip normal effectiveness

                self.graph.add_edge(
                    attack_node,
                    defend_node,
                    relation=relation,
                    multiplier=multiplier,
                )
                edge_count += 1

        logger.info(f"  Built {edge_count} type effectiveness edges")

    def _build_item_drop_edges(self):
        """Create Pokemon -> Item edges for wild drops"""
        species = self.data.get('species', {})
        name_to_id = {s['name'].lower(): sid for sid, s in species.items()}
        edge_count = 0

        for item_name, item_data in self.data.get('held_items', {}).items():
            item_id = item_name.lower().replace(' ', '_')
            item_node = f"item_{item_id}"

            if item_node not in self.graph:
                continue

            for dropper_name in item_data.get('wild_drops', []):
                pokemon_id = name_to_id.get(dropper_name.lower())
                if pokemon_id:
                    pokemon_node = f"pokemon_{pokemon_id}"
                    if pokemon_node in self.graph:
                        self.graph.add_edge(
                            pokemon_node,
                            item_node,
                            relation="drops",
                        )
                        edge_count += 1

        logger.info(f"  Built {edge_count} item drop edges")

    def _build_team_edges(self):
        """Create strategy nodes and team edges from recommended_teams.json"""
        teams = self.data.get('recommended_teams', [])
        species = self.data.get('species', {})
        name_to_id = {s['name'].lower(): sid for sid, s in species.items()}
        edge_count = 0

        for i, team in enumerate(teams):
            weather = team.get('weather', 'Unknown')
            strategy_node = f"strategy_{weather.lower()}_{i}"

            self.graph.add_node(
                strategy_node,
                node_type="strategy",
                weather=weather,
                vietnamese_name=team.get('vietnamese_name', ''),
                strategy=team.get('strategy', ''),
            )

            for member in team.get('core_members', []):
                pokemon_name = member.get('name', '')
                pokemon_id = name_to_id.get(pokemon_name.lower())
                if pokemon_id:
                    pokemon_node = f"pokemon_{pokemon_id}"
                    if pokemon_node in self.graph:
                        self.graph.add_edge(
                            strategy_node,
                            pokemon_node,
                            relation="team_member",
                            role=member.get('role', ''),
                            nature=member.get('nature', ''),
                            evs=member.get('evs', {}),
                            moves=member.get('moves', []),
                        )
                        edge_count += 1

        logger.info(f"  Built {len(teams)} team strategies with {edge_count} edges")
