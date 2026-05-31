const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, 'data');

console.log('--- Consolidation Script: Building Complete Master Database ---');

try {
  const species = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'species.json'), 'utf-8'));
  const moves = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'moves.json'), 'utf-8'));
  const items = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'items.json'), 'utf-8'));
  const abilities = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'abilities.json'), 'utf-8'));
  const natures = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'natures.json'), 'utf-8'));
  const typeMatrix = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'type_matrix.json'), 'utf-8'));
  const learnsets = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'learnsets.json'), 'utf-8'));
  const recommendedTeams = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'recommended_teams.json'), 'utf-8'));
  const levelCaps = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'level_caps.json'), 'utf-8'));

  const masterDb = {
    species,
    moves,
    items,
    abilities,
    natures,
    type_matrix: typeMatrix,
    learnsets,
    recommended_teams: recommendedTeams,
    level_caps: levelCaps
  };

  const outputPath = path.join(DATA_DIR, 'pokemmo_complete_database.json');
  fs.writeFileSync(
    outputPath,
    JSON.stringify(masterDb, null, 2),
    'utf-8'
  );

  console.log(`Successfully consolidated all datasets into Master Database!`);
  console.log(`Output saved to: ${outputPath}`);
} catch (err) {
  console.error('Error during master database consolidation:', err);
}
