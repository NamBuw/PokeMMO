const fs = require('fs');
const path = require('path');
const { Dex } = require('./pokemmo-calc/calc/node_modules/@pkmn/dex');

const OUTPUT_DIR = path.join(__dirname, 'data');
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

async function exportLearnsets() {
  console.log('--- Starting PokeMMO Level-Up Learnsets Exporter ---');
  
  const learnsetsData = {};
  
  // Get all species IDs from the Pokemon Showdown database
  const speciesList = Object.keys(Dex.data.Species);
  console.log(`Processing learnsets for ${speciesList.length} Pokémon forms and species...`);

  let processedCount = 0;
  for (const specId of speciesList) {
    try {
      const spec = Dex.species.get(specId);
      if (!spec || !spec.exists) continue;

      const learnsetObj = await Dex.learnsets.get(specId);
      if (learnsetObj && learnsetObj.learnset) {
        const gen5LvlMoves = [];
        const gen8LvlMoves = [];
        
        for (const [moveId, methods] of Object.entries(learnsetObj.learnset)) {
          // Resolve standard move name from ID
          const moveInfo = Dex.moves.get(moveId);
          const moveName = moveInfo ? moveInfo.name : moveId;
          
          for (const method of methods) {
            // Gen 5 level up moves (PokeMMO base species learnset)
            if (method.startsWith('5L')) {
              gen5LvlMoves.push({
                level: parseInt(method.substring(2)),
                move: moveName
              });
            }
            // Gen 8 level up moves (PokeMMO updated battle moves learnset)
            if (method.startsWith('8L')) {
              gen8LvlMoves.push({
                level: parseInt(method.substring(2)),
                move: moveName
              });
            }
          }
        }
        
        // Only save if there are level-up moves (exclude special forms without level-up data)
        if (gen5LvlMoves.length > 0 || gen8LvlMoves.length > 0) {
          // Sort moves by level learned
          gen5LvlMoves.sort((a, b) => a.level - b.level);
          gen8LvlMoves.sort((a, b) => a.level - b.level);
          
          learnsetsData[spec.name] = {
            gen5: gen5LvlMoves,
            gen8: gen8LvlMoves
          };
        }
      }
    } catch (err) {
      console.error(`Error loading learnset for ${specId}:`, err);
    }
    
    processedCount++;
    if (processedCount % 100 === 0) {
      console.log(`  -> Processed ${processedCount} / ${speciesList.length} Pokémon...`);
    }
  }

  const outputPath = path.join(OUTPUT_DIR, 'learnsets.json');
  fs.writeFileSync(
    outputPath,
    JSON.stringify(learnsetsData, null, 2),
    'utf-8'
  );
  
  console.log(`Saved level-up learnsets to ${outputPath}`);
  console.log('--- Learnsets Exporter Completed Successfully! ---');
}

exportLearnsets();
