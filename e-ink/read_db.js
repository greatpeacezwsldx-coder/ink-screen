const fs = require('fs');

const buffer = fs.readFileSync('photos.db');

const magic = buffer.toString('hex', 0, 16);
console.log('Magic:', magic);

const pageSize = buffer.readUInt16BE(16);
console.log('Page Size:', pageSize);

const version = buffer.readUInt16BE(18);
console.log('Version:', version);

const pageCount = buffer.readUInt32BE(28);
console.log('Page Count:', pageCount);

const firstFreePage = buffer.readUInt32BE(32);
console.log('First Free Page:', firstFreePage);

const totalFreeBytes = buffer.readUInt32BE(36);
console.log('Total Free Bytes:', totalFreeBytes);

const schemaCookie = buffer.readUInt32BE(40);
console.log('Schema Cookie:', schemaCookie);

const schemaFormat = buffer.readUInt32BE(44);
console.log('Schema Format:', schemaFormat);

const defaultCacheSize = buffer.readUInt32BE(48);
console.log('Default Cache Size:', defaultCacheSize);

const databaseText = buffer.toString('utf8', 64, 64 + 20);
console.log('Database Text:', databaseText);

const pages = [];
for (let i = 0; i < Math.min(pageCount, 5); i++) {
  const offset = i * pageSize;
  const pageHeader = buffer.readUInt8(offset);
  const pageType = ['index', 'table', 'leaf index', 'leaf table', 'overflow'][pageHeader] || 'unknown';
  const firstCellOffset = buffer.readUInt16BE(offset + 8);
  const cellCount = buffer.readUInt16BE(offset + 3);
  
  pages.push({
    index: i,
    type: pageType,
    cells: cellCount,
    firstCellOffset: firstCellOffset
  });
}

console.log('\nPages:', JSON.stringify(pages, null, 2));

function extractSQL(buffer, pageSize) {
  const sqls = [];
  for (let i = 0; i < Math.min(pageCount, 10); i++) {
    const offset = i * pageSize + 100;
    const text = buffer.toString('utf8', offset, offset + 500);
    const match = text.match(/CREATE TABLE[^;]+;/);
    if (match) {
      sqls.push(match[0]);
    }
  }
  return sqls;
}

const tables = extractSQL(buffer, pageSize);
console.log('\nTables Found:', tables.length);
tables.forEach((sql, i) => {
  console.log(`\nTable ${i + 1}:\n`, sql);
});