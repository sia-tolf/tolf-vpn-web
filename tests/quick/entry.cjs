const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const source = fs.readFileSync(path.join(root, 'js/quick-entry.js'), 'utf8');
const hidden = new Set(['quickSetupCard', 'signedOutCard', 'invitationCard']);
const elements = {};
for (const id of hidden) {
  elements[id] = {
    classList: {
      contains: name => name === 'hidden' && hidden.has(id),
      toggle: (name, force) => {
        if (name !== 'hidden') return;
        if (force) hidden.add(id); else hidden.delete(id);
      }
    }
  };
}
const observers = [];
const context = {
  document: { getElementById: id => elements[id] },
  fetch: async () => ({ ok: true, json: async () => ({ version: 1 }) }),
  MutationObserver: class {
    constructor(callback) { observers.push(callback); }
    observe() {}
  }
};
vm.createContext(context);
vm.runInContext(source, context);

setImmediate(() => {
  assert.equal(hidden.has('quickSetupCard'), true);
  hidden.delete('signedOutCard');
  observers.forEach(callback => callback());
  assert.equal(hidden.has('quickSetupCard'), false);
  hidden.add('signedOutCard');
  observers.forEach(callback => callback());
  assert.equal(hidden.has('quickSetupCard'), true);
  console.log('PASS main page quick-setup entry visibility');
});
