const fs = require('fs');
const path = require('path');
const { Generations } = require('./pokemmo-calc/calc/dist/index');

const OUTPUT_DIR = path.join(__dirname, 'data');
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// We use Generation 5 (Black/White) because PokeMMO's species and movesets are capped at Gen 5
const gen = Generations.get(5);

console.log('--- Starting PokeMMO Gen 1-5 Exporter ---');

// 1. Export Pokémon Species
const speciesList = [];
for (const spec of gen.species) {
  speciesList.push({
    id: spec.id,
    name: spec.name,
    baseStats: {
      hp: spec.baseStats.hp,
      atk: spec.baseStats.atk,
      def: spec.baseStats.def,
      spa: spec.baseStats.spa,
      spd: spec.baseStats.spd,
      spe: spec.baseStats.spe
    },
    types: spec.types,
    weightkg: spec.weightkg,
    nfe: spec.nfe || false,
    abilities: spec.abilities ? Object.values(spec.abilities) : [],
    gender: spec.gender || 'N'
  });
}
fs.writeFileSync(
  path.join(OUTPUT_DIR, 'species.json'),
  JSON.stringify(speciesList, null, 2),
  'utf-8'
);
console.log(`Saved ${speciesList.length} Pokémon species to data/species.json`);

// 2. Export Moves
const movesList = [];
for (const move of gen.moves) {
  movesList.push({
    id: move.id,
    name: move.name,
    type: move.type,
    category: move.category,
    basePower: move.basePower,
    flags: move.flags || {}
  });
}
fs.writeFileSync(
  path.join(OUTPUT_DIR, 'moves.json'),
  JSON.stringify(movesList, null, 2),
  'utf-8'
);
console.log(`Saved ${movesList.length} moves to data/moves.json`);

// 3. Export Items
const itemsList = [];
for (const item of gen.items) {
  itemsList.push({
    id: item.id,
    name: item.name
  });
}
fs.writeFileSync(
  path.join(OUTPUT_DIR, 'items.json'),
  JSON.stringify(itemsList, null, 2),
  'utf-8'
);
console.log(`Saved ${itemsList.length} items to data/items.json`);

// 4. Export Abilities
const abilitiesList = [];
for (const ability of gen.abilities) {
  abilitiesList.push({
    id: ability.id,
    name: ability.name
  });
}
fs.writeFileSync(
  path.join(OUTPUT_DIR, 'abilities.json'),
  JSON.stringify(abilitiesList, null, 2),
  'utf-8'
);
console.log(`Saved ${abilitiesList.length} abilities to data/abilities.json`);

// 5. Export Natures (25 natures)
const naturesList = [];
const naturesKeys = [
  'adamant', 'bashful', 'bold', 'brave', 'calm',
  'careful', 'docile', 'gentle', 'hardy', 'hasty',
  'impish', 'jolly', 'lax', 'lonely', 'mild',
  'modest', 'naive', 'naughty', 'quiet', 'quirky',
  'rash', 'relaxed', 'sassy', 'serious', 'timid'
];

for (const natId of naturesKeys) {
  const nat = gen.natures.get(natId);
  if (nat) {
    naturesList.push({
      id: nat.id,
      name: nat.name,
      plus: nat.plus || null,
      minus: nat.minus || null
    });
  }
}
fs.writeFileSync(
  path.join(OUTPUT_DIR, 'natures.json'),
  JSON.stringify(naturesList, null, 2),
  'utf-8'
);
console.log(`Saved ${naturesList.length} natures to data/natures.json`);

// 6. Export Typing Matchup Matrix (18x18)
const typeKeys = [
  'Normal', 'Fire', 'Water', 'Electric', 'Grass', 'Ice',
  'Fighting', 'Poison', 'Ground', 'Flying', 'Psychic', 'Bug',
  'Rock', 'Ghost', 'Dragon', 'Dark', 'Steel', '???'
];

const typeMatrix = {};
for (const typeVal of typeKeys) {
  const typeObj = gen.types.get(typeVal.toLowerCase());
  if (typeObj) {
    typeMatrix[typeObj.name] = typeObj.effectiveness;
  }
}
fs.writeFileSync(
  path.join(OUTPUT_DIR, 'type_matrix.json'),
  JSON.stringify(typeMatrix, null, 2),
  'utf-8'
);
console.log(`Saved Type Matchup Matrix to data/type_matrix.json`);

// 7. Save Consolidated complete database
const completeDatabase = {
  species: speciesList,
  moves: movesList,
  items: itemsList,
  abilities: abilitiesList,
  natures: naturesList,
  type_matrix: typeMatrix
};
fs.writeFileSync(
  path.join(OUTPUT_DIR, 'pokemmo_complete_database.json'),
  JSON.stringify(completeDatabase, null, 2),
  'utf-8'
);
console.log('Saved consolidated Master Database to data/pokemmo_complete_database.json');
console.log('--- PokeMMO Exporter Completed Successfully! ---');
