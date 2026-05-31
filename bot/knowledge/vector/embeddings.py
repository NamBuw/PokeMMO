"""
Embedding Generator - Create text embeddings for game entities
Uses sentence-transformers for semantic embeddings
"""
import logging
from typing import List, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for game knowledge entities"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding generator

        Args:
            model_name: Sentence-transformers model name
                        Options: all-MiniLM-L6-v2 (fast), all-mpnet-base-v2 (accurate)
        """
        self.model_name = model_name
        self._model = None
        self._embedding_dim = None

    @property
    def model(self):
        """Lazy load model"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                self._embedding_dim = self._model.get_sentence_embedding_dimension()
                logger.info(f"Model loaded. Embedding dim: {self._embedding_dim}")
            except ImportError:
                logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
                raise
        return self._model

    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension"""
        if self._embedding_dim is None:
            _ = self.model  # Trigger lazy load
        return self._embedding_dim

    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts to embeddings"""
        return self.model.encode(texts, show_progress_bar=False)

    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text to embedding"""
        return self.model.encode([text], show_progress_bar=False)[0]

    # ========== Entity Text Generators ==========

    def pokemon_to_text(self, pokemon: Dict) -> str:
        """Convert Pokemon data to text for embedding"""
        name = pokemon.get('name', 'Unknown')
        types = '/'.join(pokemon.get('types', []))
        abilities = ', '.join(pokemon.get('abilities', []))
        stats = pokemon.get('base_stats', pokemon.get('baseStats', {}))
        bst = pokemon.get('bst', sum(stats.values()) if stats else 0)

        parts = [
            f"{name} is a {types} type Pokemon",
            f"with abilities: {abilities}.",
            f"Base Stat Total: {bst}.",
        ]

        if stats:
            parts.append(
                f"Stats: HP {stats.get('hp', 0)}, "
                f"Atk {stats.get('atk', 0)}, "
                f"Def {stats.get('def', 0)}, "
                f"SpA {stats.get('spa', 0)}, "
                f"SpD {stats.get('spd', 0)}, "
                f"Spe {stats.get('spe', 0)}."
            )

        return ' '.join(parts)

    def move_to_text(self, move: Dict) -> str:
        """Convert Move data to text for embedding"""
        name = move.get('name', 'Unknown')
        move_type = move.get('type', move.get('move_type', 'Unknown'))
        category = move.get('category', 'Unknown')
        power = move.get('basePower', move.get('power', 0))

        if category == 'Status':
            return f"{name} is a {move_type} type Status move."
        return f"{name} is a {move_type} type {category} move with {power} base power."

    def ability_to_text(self, ability: Dict) -> str:
        """Convert Ability data to text for embedding"""
        name = ability.get('name', 'Unknown')
        effect = ability.get('effect', '')
        return f"{name}: {effect}"

    def item_to_text(self, item: Dict) -> str:
        """Convert Item data to text for embedding"""
        name = item.get('name', 'Unknown')
        effect = item.get('effect', item.get('description', ''))
        category = item.get('category', '')
        return f"{name} ({category}): {effect}"

    def strategy_to_text(self, team: Dict) -> str:
        """Convert team strategy to text for embedding"""
        weather = team.get('weather', 'Unknown')
        strategy = team.get('strategy', '')
        members = [m.get('name', '') for m in team.get('core_members', [])]
        member_str = ', '.join(members)

        return (
            f"{weather} team strategy: {strategy} "
            f"Core members: {member_str}."
        )

    def game_state_to_text(self, state: Dict) -> str:
        """Convert game state to text for context"""
        parts = []

        game_state = state.get('game_state', 'OVERWORLD')
        parts.append(f"Game state: {game_state}")

        if game_state == 'BATTLE':
            player = state.get('party', [{}])[0]
            enemy = state.get('enemy', {})

            if player:
                p_name = player.get('name', 'Unknown')
                p_hp = player.get('hp_percent', 100)
                p_types = '/'.join(player.get('types', []))
                parts.append(f"Player: {p_name} ({p_types}) HP: {p_hp}%")

                moves = player.get('moves', [])
                if moves:
                    move_str = ', '.join(
                        f"{m.get('name', '')} ({m.get('type', '')}, {m.get('category', '')})"
                        for m in moves
                    )
                    parts.append(f"Moves: {move_str}")

            if enemy:
                e_name = enemy.get('name', 'Unknown')
                e_hp = enemy.get('hp_percent', 100)
                e_types = '/'.join(enemy.get('types', []))
                parts.append(f"Enemy: {e_name} ({e_types}) HP: {e_hp}%")

        return ' '.join(parts)
