const fs = require('fs');
const path = require('path');

const ABILITIES_PATH = path.join(__dirname, 'data', 'abilities.json');
const SRC_ABILITIES_PATH = path.join(__dirname, 'pokemmo-data', 'data', 'abilities-data.json');
const MASTER_PATH = path.join(__dirname, 'data', 'pokemmo_complete_database.json');

console.log('--- Appending Actual In-Battle Effects to Abilities ---');

try {
  if (!fs.existsSync(ABILITIES_PATH)) {
    console.error(`File data/abilities.json not found!`);
    process.exit(1);
  }
  if (!fs.existsSync(SRC_ABILITIES_PATH)) {
    console.error(`Source abilities-data.json not found at ${SRC_ABILITIES_PATH}`);
    process.exit(1);
  }

  // 1. Read existing compiled abilities and the source detailed database
  const compiledAbilities = JSON.parse(fs.readFileSync(ABILITIES_PATH, 'utf-8'));
  const sourceDetailed = JSON.parse(fs.readFileSync(SRC_ABILITIES_PATH, 'utf-8'));

  // 2. Map and update with in-battle effects
  let updatedCount = 0;
  const updatedAbilities = compiledAbilities.map(ab => {
    // Standardize key lookup
    const abId = ab.id.toLowerCase();
    
    // Check direct matching or dashed matching (e.g. "airlock" vs "air-lock" or "speedboost" vs "speed-boost")
    let match = sourceDetailed[abId];
    
    if (!match) {
      // Try to find by inserting dashes
      const dashedId = abId.replace(/([a-z])([a-z]+)/g, (m, g1, g2) => {
        // Simple fuzzy match if needed, but let's do direct keys from sourceDetailed
        return m;
      });
      
      // Let's search keys fuzzy
      const matchedKey = Object.keys(sourceDetailed).find(k => k.replace(/[^a-z]/g, '') === abId.replace(/[^a-z]/g, ''));
      if (matchedKey) {
        match = sourceDetailed[matchedKey];
      }
    }

    if (match && match.effect) {
      updatedCount++;
      return {
        id: ab.id,
        name: ab.name,
        effect: match.effect
      };
    }

    // Default if no effect matched
    return {
      id: ab.id,
      name: ab.name,
      effect: "No description available."
    };
  });

  // 3. Overwrite abilities.json
  fs.writeFileSync(
    ABILITIES_PATH,
    JSON.stringify(updatedAbilities, null, 2),
    'utf-8'
  );
  console.log(`Successfully updated ${updatedCount} / ${compiledAbilities.length} abilities with active battle effects in data/abilities.json!`);

  // 4. Update the consolidated master database
  if (fs.existsSync(MASTER_PATH)) {
    const masterDb = JSON.parse(fs.readFileSync(MASTER_PATH, 'utf-8'));
    masterDb.abilities = updatedAbilities;
    
    fs.writeFileSync(
      MASTER_PATH,
      JSON.stringify(masterDb, null, 2),
      'utf-8'
    );
    console.log('Successfully consolidated new abilities descriptions into master pokemmo_complete_database.json!');
  }

} catch (err) {
  console.error('Error updating abilities:', err);
}
