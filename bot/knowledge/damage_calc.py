import os
import json
import math

class DamageCalculator:
    def __init__(self, data_dir='/home/namnx/pokemmo_crawler/data'):
        self.data_dir = data_dir
        self.species = {}
        self.moves = {}
        self.natures = {}
        self.type_matrix = {}
        self.load_databases()

    def load_databases(self):
        """Load all exported JSON database files."""
        try:
            with open(os.path.join(self.data_dir, 'species.json'), 'r', encoding='utf-8') as f:
                for s in json.load(f):
                    self.species[s['id']] = s
                    
            with open(os.path.join(self.data_dir, 'moves.json'), 'r', encoding='utf-8') as f:
                for m in json.load(f):
                    self.moves[m['id']] = m
                    
            with open(os.path.join(self.data_dir, 'natures.json'), 'r', encoding='utf-8') as f:
                for n in json.load(f):
                    self.natures[n['id']] = n
                    
            with open(os.path.join(self.data_dir, 'type_matrix.json'), 'r', encoding='utf-8') as f:
                self.type_matrix = json.load(f)
                
            print(f"Successfully loaded database: {len(self.species)} Pokémon, {len(self.moves)} moves.")
        except Exception as e:
            print(f"Error loading databases: {e}")

    def to_id(self, name):
        """Convert a string name into a standardized lowercase ID."""
        import re
        return re.sub(r'[^a-z0-9]', '', name.lower())

    def get_type_multiplier(self, move_type, defender_types):
        """Lookup type matchup multiplier against single/dual types."""
        multiplier = 1.0
        move_type = move_type.capitalize()
        if move_type not in self.type_matrix:
            return multiplier
            
        for def_type in defender_types:
            def_type = def_type.capitalize()
            if def_type in self.type_matrix[move_type]:
                multiplier *= self.type_matrix[move_type][def_type]
        return multiplier

    def calculate_stat(self, stat_name, base, iv=31, ev=0, level=50, nature_mod=1.0):
        """Calculate actual in-game stat based on formula."""
        if stat_name == 'hp':
            # Shedinja hack
            if base == 1:
                return 1
            return math.floor(((2 * base + iv + math.floor(ev / 4)) * level) / 100) + level + 10
        else:
            calc_val = math.floor(((2 * base + iv + math.floor(ev / 4)) * level) / 100) + 5
            return math.floor(calc_val * nature_mod)

    def get_nature_multiplier(self, nature_name, stat_name):
        """Get the nature modifier multiplier (+10% or -10% or neutral)."""
        nature_id = self.to_id(nature_name)
        if nature_id not in self.natures:
            return 1.0
        nat = self.natures[nature_id]
        if nat['plus'] == stat_name:
            return 1.1
        if nat['minus'] == stat_name:
            return 0.9
        return 1.0

    def calculate_damage(self, attacker_name, defender_name, move_name, 
                         attacker_lvl=50, attacker_nature='Serious', attacker_evs=None, attacker_ivs=None,
                         defender_nature='Serious', defender_evs=None, defender_ivs=None,
                         is_crit=False, weather='Normal', attacker_item=None):
        """
        Calculate damage rolls using Gen 8 PokeMMO mechanics.
        """
        # 1. Resolve species and move
        atk_id = self.to_id(attacker_name)
        def_id = self.to_id(defender_name)
        move_id = self.to_id(move_name)

        if atk_id not in self.species or def_id not in self.species:
            raise ValueError(f"Pokémon name '{attacker_name}' or '{defender_name}' not found.")
        if move_id not in self.moves:
            raise ValueError(f"Move '{move_name}' not found.")

        atk_spec = self.species[atk_id]
        def_spec = self.species[def_id]
        move = self.moves[move_id]

        # Standardize inputs
        attacker_evs = attacker_evs or {}
        attacker_ivs = attacker_ivs or {}
        defender_evs = defender_evs or {}
        defender_ivs = defender_ivs or {}

        # 2. Determine Move Category & Stats
        category = move['category']
        move_type = move['type']
        base_power = move['basePower']

        if category == 'Status':
            return {
                'description': f"{move['name']} is a Status move (does no damage).",
                'damageRolls': [0],
                'minDamage': 0,
                'maxDamage': 0
            }

        # 3. Calculate Attacker Offense & Defender Defense Stats
        if category == 'Physical':
            atk_stat_name = 'atk'
            def_stat_name = 'def'
        else: # Special
            atk_stat_name = 'spa'
            def_stat_name = 'spd'

        # Fetch Base stats
        atk_base = atk_spec['baseStats'][atk_stat_name]
        def_base = def_spec['baseStats'][def_stat_name]
        def_hp_base = def_spec['baseStats']['hp']

        # Get Nature Mods
        atk_nature_mod = self.get_nature_multiplier(attacker_nature, atk_stat_name)
        def_nature_mod = self.get_nature_multiplier(defender_nature, def_stat_name)

        # Calculate final stats
        offense = self.calculate_stat(
            atk_stat_name, atk_base, 
            iv=attacker_ivs.get(atk_stat_name, 31), 
            ev=attacker_evs.get(atk_stat_name, 0), 
            level=attacker_lvl, 
            nature_mod=atk_nature_mod
        )
        
        defense = self.calculate_stat(
            def_stat_name, def_base, 
            iv=defender_ivs.get(def_stat_name, 31), 
            ev=defender_evs.get(def_stat_name, 0), 
            level=attacker_lvl,  # Assume defender is same level
            nature_mod=def_nature_mod
        )
        
        defender_max_hp = self.calculate_stat(
            'hp', def_hp_base, 
            iv=defender_ivs.get('hp', 31), 
            ev=defender_evs.get('hp', 0), 
            level=attacker_lvl
        )

        # 4. Item and Ability Modifiers
        # Life Orb: 1.3x, Choice Band/Specs: 1.5x
        item_mod = 1.0
        if attacker_item == 'Life Orb':
            item_mod = 1.3
        elif attacker_item == 'Choice Band' and category == 'Physical':
            item_mod = 1.5
        elif attacker_item == 'Choice Specs' and category == 'Special':
            item_mod = 1.5

        # 5. Core Damage Formula
        # Damage = (((2 * L / 5 + 2) * BP * A / D) / 50) + 2
        level_part = (2 * attacker_lvl / 5) + 2
        base_damage = math.floor(math.floor(level_part * base_power * offense / defense) / 50) + 2

        # 6. Apply Modifiers
        # Weather
        weather_mod = 1.0
        if weather == 'Sun' and move_type == 'Fire':
            weather_mod = 1.5
        elif weather == 'Sun' and move_type == 'Water':
            weather_mod = 0.5
        elif weather == 'Rain' and move_type == 'Water':
            weather_mod = 1.5
        elif weather == 'Rain' and move_type == 'Fire':
            weather_mod = 0.5

        # Critical Hit
        crit_mod = 1.5 if is_crit else 1.0

        # STAB (Same Type Attack Bonus)
        stab_mod = 1.0
        if move_type in atk_spec['types']:
            stab_mod = 1.5

        # Type Matchup Multiplier
        type_mod = self.get_type_multiplier(move_type, def_spec['types'])

        # 7. Generate 16 Damage Rolls
        rolls = []
        random_factors = [85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100]
        
        for rf in random_factors:
            # Apply random roll
            r_dmg = math.floor(base_damage * rf / 100)
            
            # Apply multipliers
            final_dmg = r_dmg
            final_dmg = math.floor(final_dmg * weather_mod)
            final_dmg = math.floor(final_dmg * crit_mod)
            final_dmg = math.floor(final_dmg * stab_mod)
            final_dmg = math.floor(final_dmg * type_mod)
            final_dmg = math.floor(final_dmg * item_mod)
            
            # Damage can't be negative, and must be at least 1 if type matchup is not immune
            if final_dmg <= 0 and type_mod > 0:
                final_dmg = 1
                
            rolls.append(final_dmg)

        min_dmg = rolls[0]
        max_dmg = rolls[-1]
        
        min_pct = (min_dmg / defender_max_hp) * 100
        max_pct = (max_dmg / defender_max_hp) * 100

        desc = f"{attacker_lvl} {attacker_nature} {attacker_name} {move['name']} vs. {defender_name}: {min_dmg}-{max_dmg} ({min_pct:.1f}% - {max_pct:.1f}%)"
        
        return {
            'description': desc,
            'damageRolls': rolls,
            'minDamage': min_dmg,
            'maxDamage': max_dmg,
            'defenderMaxHP': defender_max_hp,
            'percentages': {
                'minPercent': f"{min_pct:.1f}%",
                'maxPercent': f"{max_pct:.1f}%"
            }
        }

if __name__ == '__main__':
    # Simple test run
    calc = DamageCalculator()
    res = calc.calculate_damage('Alakazam', 'Mew', 'Psychic', attacker_lvl=50)
    print("\nTest native Python calculation:")
    print(res['description'])
    print(res['damageRolls'])
