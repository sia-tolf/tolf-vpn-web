const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const source = fs.readFileSync(
  path.join(root, "js/routing-rules.js"),
  "utf8"
);

function routingContext() {
  const context = {
    URL,
    routingRuleGroups: null,
    routingRulesValidation: null,
    profileSettings: null,
    t: key => key,
    console
  };

  vm.createContext(context);
  vm.runInContext(source, context);
  return context;
}

test("normalizes domains and pasted URLs", () => {
  const context = routingContext();

  assert.equal(
    context.normalizeRoutingDomain(" HTTPS://WWW.Revolut.com/help "),
    "www.revolut.com"
  );
  assert.equal(
    context.normalizeRoutingDomain("*.wise.com"),
    "wise.com"
  );
  assert.equal(
    context.normalizeRoutingDomain("https://münchen.de/path"),
    "xn--mnchen-3ya.de"
  );
});

test("rejects IP addresses and invalid host names", () => {
  const context = routingContext();

  for (const value of [
    "10.0.0.1",
    "localhost",
    "bad_domain.com",
    "https://example.com:8443",
    "https://user@example.com"
  ]) {
    assert.equal(context.normalizeRoutingDomain(value), null, value);
  }
});

test("loads a grouped routing policy without cross-exit duplicates", () => {
  const context = routingContext();

  context.setRoutingRules({
    riga: ["revolut.com", "wise.com"],
    moscow: ["wise.com", "yandex.ru"],
    usa: ["openai.com"]
  });

  const result = JSON.parse(JSON.stringify(
    context.getRoutingRulesSelection()
  ));

  assert.deepEqual(result, {
    riga: ["revolut.com", "wise.com"],
    moscow: ["yandex.ru"],
    usa: ["openai.com"]
  });
});

test("profile payload includes grouped routing rules", () => {
  const profileSettings = fs.readFileSync(
    path.join(root, "js/profile-settings.js"),
    "utf8"
  );
  const index = fs.readFileSync(path.join(root, "index.html"), "utf8");

  assert.match(profileSettings, /routingRules\s*$/m);
  assert.match(index, /id="routingRulesSection"/);
  assert.match(index, /js\/routing-rules\.js/);
});
