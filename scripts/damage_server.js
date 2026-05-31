const express = require('express');
const { Generations, calculate, Pokemon, Move, Field } = require('./pokemmo-calc/calc/dist/index');

const app = express();
app.use(express.json());

// Main calculation endpoint
app.post('/calculate', (req, res) => {
  try {
    const { genNum = 5, attacker, defender, moveName, fieldOptions } = req.body;

    if (!attacker || !attacker.name) {
      return res.status(400).json({ error: 'Attacker object with a valid name is required.' });
    }
    if (!defender || !defender.name) {
      return res.status(400).json({ error: 'Defender object with a valid name is required.' });
    }
    if (!moveName) {
      return res.status(400).json({ error: 'moveName is required.' });
    }

    const gen = Generations.get(genNum);
    
    // Instantiate Pokemon, Move and Field using Smogon definitions
    const attackerPkmn = new Pokemon(gen, attacker.name, attacker.options || {});
    const defenderPkmn = new Pokemon(gen, defender.name, defender.options || {});
    const moveObj = new Move(gen, moveName, moveObjOptions(req.body.moveOptions));
    const fieldObj = new Field(fieldOptions || {});

    // Compute Damage!
    const result = calculate(gen, attackerPkmn, defenderPkmn, moveObj, fieldObj);

    // Prepare a clean, informative response for the LLM agent
    const rolls = result.damage || [0];
    const minRoll = typeof rolls === 'number' ? rolls : rolls[0];
    const maxRoll = typeof rolls === 'number' ? rolls : rolls[rolls.length - 1];
    
    const response = {
      description: result.desc(),
      damageRolls: rolls,
      minDamage: minRoll,
      maxDamage: maxRoll,
      defenderMaxHP: defenderPkmn.maxHP(),
      percentages: {
        minPercent: ((minRoll / defenderPkmn.maxHP()) * 100).toFixed(1) + '%',
        maxPercent: ((maxRoll / defenderPkmn.maxHP()) * 100).toFixed(1) + '%'
      }
    };

    res.json(response);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: error.message });
  }
});

function moveObjOptions(options) {
  if (!options) return {};
  // Handles custom move overrides like critical hits or base power overrides
  return {
    useMax: options.useMax || false,
    isCrit: options.isCrit || false,
    hits: options.hits || undefined
  };
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`PokeMMO Damage API Server running on port ${PORT}`);
});
