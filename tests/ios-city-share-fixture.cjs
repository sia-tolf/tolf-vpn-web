// Synthetic share IDs for UI routing tests; never published as product links.
const ids = {moscow:'a'.repeat(32), riga:'b'.repeat(32),us:'c'.repeat(32)};
function withShares(source) {
 return source.replace(/const CITY_SHARES = \{[\s\S]*?\n  \};/, 'const CITY_SHARES = '+JSON.stringify(ids)+';');
}
module.exports = {ids, withShares};
