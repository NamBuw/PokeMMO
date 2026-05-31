import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class BattleIntelligence:
    def __init__(self, damage_calc, queries):
        """
        Args:
            damage_calc: DamageCalculator instance
            queries: GraphQueries instance
        """
        self.damage_calc = damage_calc
        self.queries = queries

        # Ability-based move immunities mapping
        # Ability ID -> list of move types (lowercase) that are completely neutralized
        self.ability_immunities = {
            "levitate": ["ground"],
            "flashfire": ["fire"],
            "waterabsorb": ["water"],
            "stormdrain": ["water"],
            "dryskin": ["water"],
            "voltabsorb": ["electric"],
            "lightningrod": ["electric"],
            "motordrive": ["electric"],
            "sapsipper": ["grass"],
        }

    def to_id(self, name: str) -> str:
        import re
        return re.sub(r'[^a-z0-9]', '', name.lower())

    def check_choice_lock(self, party_member: dict, last_used_move: str = None) -> List[dict]:
        """
        Checks if the Pokemon is choice-locked into a single move due to holding Choice items.
        Returns a filtered list of moves that are allowed to be used.
        """
        moves = party_member.get("moves", [])
        held_item = (party_member.get("item") or "").lower().replace(" ", "")

        # If holding Choice Band, Choice Specs, or Choice Scarf
        is_choice_item = "choiceband" in held_item or "choicespecs" in held_item or "choicescarf" in held_item

        if is_choice_item and last_used_move:
            last_used_id = self.to_id(last_used_move)
            # Find the locked move in the list
            locked_move = next((m for m in moves if self.to_id(m.get("name", "")) == last_used_id), None)
            if locked_move:
                logger.info(f"🔒 Choice-Lock detected! Locked into move: {locked_move.get('name')}")
                return [locked_move]

        return moves

    def filter_immune_moves(self, attacker_moves: List[dict], defender_name: str) -> List[dict]:
        """
        Filters out moves that are completely immune due to the defender's standard abilities.
        """
        defender_info = self.queries.get_pokemon_info(defender_name)
        if not defender_info:
            return attacker_moves

        # Retrieve defender possible abilities
        abilities = [self.to_id(a) for a in defender_info.get("abilities", [])]
        
        filtered_moves = []
        for move in attacker_moves:
            move_type = move.get("type", "").lower()
            is_immune = False
            
            # Check ability immunities
            for ability in abilities:
                if ability in self.ability_immunities:
                    if move_type in self.ability_immunities[ability]:
                        logger.info(f"🚫 Move {move.get('name')} filtered out due to enemy ability: {ability}")
                        is_immune = True
                        break
            
            # Wonder Guard check (Shedinja only takes damage from Super Effective moves)
            if "wonderguard" in abilities:
                # Find type multipliers against defender
                def_types = defender_info.get("types", [])
                mult = self.damage_calc.get_type_multiplier(move_type, def_types)
                if mult <= 1.0 and move.get("category") != "Status":
                    logger.info(f"🚫 Move {move.get('name')} filtered out due to Wonder Guard (Not Super Effective)")
                    is_immune = True
            
            if not is_immune:
                filtered_moves.append(move)

        return filtered_moves

    def get_defender_possible_moves(self, defender_name: str, defender_level: int = 50) -> List[dict]:
        """
        Predicts defender's possible moves based on their learnsets and level.
        Returns a list of moves they could use against us.
        """
        info = self.queries.get_pokemon_info(defender_name)
        if not info:
            return []

        # Filter level-up moves up to the defender's level
        possible_moves = []
        for m in info.get("moves", []):
            if m.get("method") == "level_up" and m.get("level", 0) <= defender_level:
                possible_moves.append(m)

        # Sort by level descending and take top 4 highest power moves
        possible_moves.sort(key=lambda x: (x.get("power", 0) or 0), reverse=True)
        return possible_moves[:4]

    def evaluate_survival(self, party_member: dict, defender_name: str, defender_level: int = 50) -> dict:
        """
        Evaluates our active Pokemon's survival probability against the defender's highest potential damage.
        Returns a status dictionary.
        """
        cur_hp = party_member.get("hp", 100) # Current absolute HP
        max_hp = party_member.get("max_hp", 100) # Max HP
        hp_percent = party_member.get("hp_percent", 100.0)

        # Predict defender moves
        enemy_moves = self.get_defender_possible_moves(defender_name, defender_level)
        if not enemy_moves:
            # Fallback if no moves found (assume a generic 80 power physical move of the enemy's primary type)
            info = self.queries.get_pokemon_info(defender_name)
            primary_type = info.get("types", ["Normal"])[0] if info else "Normal"
            enemy_moves = [{"name": "Standard Attack", "type": primary_type, "category": "Physical", "power": 80}]

        max_incoming_damage = 0
        killer_move = None

        for move in enemy_moves:
            try:
                # Calculate damage rolls
                dmg = self.damage_calc.calculate_damage(
                    attacker_name=defender_name,
                    defender_name=party_member.get("name"),
                    move_name=move.get("name"),
                    attacker_lvl=defender_level,
                    # Assume serious/neutral stats for calculation safety
                )
                
                if dmg and dmg.get("maxDamage", 0) > max_incoming_damage:
                    max_incoming_damage = dmg.get("maxDamage", 0)
                    killer_move = move.get("name")
            except Exception:
                # Simple approximation fallback: HP% * (power / 100) * type effectiveness
                pass

        # If absolute HP not provided, calculate from max_hp & percent
        current_hp_abs = cur_hp if "hp" in party_member else int(max_hp * (hp_percent / 100.0))
        
        # Danger evaluation
        is_endangered = current_hp_abs <= max_incoming_damage
        hp_state = "SAFE"
        
        if is_endangered:
            hp_state = "CRITICAL"
            reason = f"Đối thủ có thể hạ gục bằng {killer_move} (Max dmg: {max_incoming_damage} vs HP: {current_hp_abs})"
        elif hp_percent < 40.0:
            hp_state = "WARNING"
            reason = f"Máu dưới 40% ({hp_percent:.1f}%), cần chú ý hồi máu."
        else:
            reason = "Máu ở trạng thái an toàn."

        return {
            "status": hp_state,
            "is_endangered": is_endangered,
            "max_incoming_damage": max_incoming_damage,
            "killer_move": killer_move,
            "reason": reason
        }

    def recommend_switch(self, party: List[dict], defender_name: str) -> Optional[dict]:
        """
        Scans reserve party members and recommends the best switch candidate to resist the defender.
        """
        defender_info = self.queries.get_pokemon_info(defender_name)
        if not defender_info or len(party) <= 1:
            return None

        def_types = defender_info.get("types", [])
        
        best_candidate = None
        best_resistance_score = 999.0 # Lower is better (multipliers)

        # Loop from index 1 (reserve members only)
        for i in range(1, len(party)):
            member = party[i]
            # Skip fainted members
            if member.get("hp_percent", 100.0) <= 0:
                continue

            member_info = self.queries.get_pokemon_info(member.get("name"))
            if not member_info:
                continue

            member_types = member_info.get("types", [])
            
            # Calculate combined type resistance score against defender's offensive types
            resistance_score = 1.0
            for dt in def_types:
                # Get type matchups (Attacking system)
                matchups = self.queries.get_type_matchups(dt)
                if matchups:
                    # Check if the ally resists dt
                    for mt in member_types:
                        # How dt affects mt
                        mult = self.damage_calc.get_type_multiplier(dt, [mt])
                        resistance_score *= mult

            if resistance_score < best_resistance_score:
                best_resistance_score = resistance_score
                best_candidate = {
                    "slot": i + 1, # 1-indexed slot
                    "name": member.get("name"),
                    "resistance_score": resistance_score,
                    "vietnamese_description": f"Chống chịu hệ của đối thủ rất tốt ({resistance_score:.2f}x)"
                }

        # Only recommend if the candidate provides actual resistance (< 1.0)
        if best_candidate and best_resistance_score < 1.0:
            return best_candidate
        
        # Otherwise recommend the healthy member with highest BST
        reserve_healthy = [
            (i + 1, m) for i, m in enumerate(party[1:]) if m.get("hp_percent", 100.0) > 40.0
        ]
        if reserve_healthy:
            # Sort by BST
            reserve_healthy.sort(key=lambda x: self.queries.get_pokemon_info(x[1].get("name")).get("bst", 0) if self.queries.get_pokemon_info(x[1].get("name")) else 0, reverse=True)
            slot, pkmn = reserve_healthy[0]
            return {
                "slot": slot,
                "name": pkmn.get("name"),
                "resistance_score": 1.0,
                "vietnamese_description": f"Pokemon khỏe mạnh nhất dự phòng ({pkmn.get('name')})"
            }

        return None
