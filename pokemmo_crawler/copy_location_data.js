const fs = require('fs');
const path = require('path');

const SRC_PATH = path.join(__dirname, 'pokemmo-data', 'data', 'location-data.json');
const DEST_PATH = path.join(__dirname, 'data', 'location_data.json');
const MASTER_PATH = path.join(__dirname, 'data', 'pokemmo_complete_database.json');

console.log('--- Copying and Consolidating Location/Encounter Database ---');

try {
  if (!fs.existsSync(SRC_PATH)) {
    console.error(`Source location-data.json not found at ${SRC_PATH}`);
    process.exit(1);
  }

  // 1. Copy file to output directory
  fs.copyFileSync(SRC_PATH, DEST_PATH);
  console.log(`Copied complete wild encounter database to: ${DEST_PATH}`);

  // 2. Read the master database
  if (!fs.existsSync(MASTER_PATH)) {
    console.error('Master database not found. Run append_to_master.js first.');
    process.exit(1);
  }

  const masterDb = JSON.parse(fs.readFileSync(MASTER_PATH, 'utf-8'));
  const locationData = JSON.parse(fs.readFileSync(DEST_PATH, 'utf-8'));

  // 3. Append locations
  masterDb.locations = locationData;

  // 4. Save updated master database
  fs.writeFileSync(
    MASTER_PATH,
    JSON.stringify(masterDb, null, 2),
    'utf-8'
  );

  console.log(`Successfully integrated Kanto, Johto, Hoenn, Sinnoh, and Unova wild encounters into Master Database!`);
  console.log(`Master Database rows increased to support complete map exploration.`);
} catch (err) {
  console.error('Error during location consolidation:', err);
}
