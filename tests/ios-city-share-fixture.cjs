// Synthetic share IDs for UI routing tests; never published as product links.
const ids = {moscow:{ru:'a'.repeat(32),en:'c'.repeat(32),lv:'e'.repeat(32)},
             riga:{ru:'b'.repeat(32),en:'d'.repeat(32),lv:'f'.repeat(32)}};
function withShares(source) {
 return source.replace(/const CITY_SHARES = \{[\s\S]*?\n  \};/, 'const CITY_SHARES = '+JSON.stringify(ids)+';');
}
module.exports = {ids, withShares};
