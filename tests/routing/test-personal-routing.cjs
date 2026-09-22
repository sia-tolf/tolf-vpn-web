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

test("routing preferences use their own API instead of the profile payload", () => {
  const profileSettings = fs.readFileSync(
    path.join(root, "js/profile-settings.js"),
    "utf8"
  );
  const index = fs.readFileSync(path.join(root, "index.html"), "utf8");

  assert.doesNotMatch(profileSettings, /routingRules\s*$/m);
  assert.match(index, /id="routingRulesSection"/);
  assert.match(index, /js\/routing-rules\.js/);
  assert.match(index, /js\/routing-policy\.js/);
  assert.match(index, /id="routingPolicySave"/);
});

test("comma list adds normalized separate domains and deduplicates the batch", () => {
  const c = routingContext();
  const input = {value:" delfi.lv, EXAMPLE.com, delfi.lv, ",setAttribute(){},focus(){}};
  assert.equal(c.addRoutingDomain("moscow", input), true);
  assert.deepEqual(Array.from(c.getRoutingRulesSelection().moscow), ["delfi.lv","example.com"]);
});

test("invalid or conflicting batch preserves all existing rules and input", () => {
  const c = routingContext();
  c.setRoutingRules({riga:["example.com"]});
  for (const value of ["delfi.lv, bad domain", "delfi.lv, example.com"]) {
    const input = {value,setAttribute(){},focus(){}};
    assert.equal(c.addRoutingDomain("moscow", input), false);
    assert.equal(input.value, value);
    assert.deepEqual(Array.from(c.getRoutingRulesSelection().moscow), []);
  }
});

test("batch limit is checked before adding any domains", () => {
  const c = routingContext();
  c.setRoutingRules({moscow:Array.from({length:199},(_,i)=>"site"+i+".test")});
  assert.equal(c.addRoutingDomain("moscow", {value:"one.test,two.test",setAttribute(){},focus(){}}), false);
  assert.equal(c.getRoutingRulesSelection().moscow.length, 199);
});

test("save with open editor includes the complete comma list", () => {
  const c = routingContext();
  const input = {value:"delfi.lv, example.com",closest:()=>({dataset:{exit:"moscow"}})};
  c.routingRuleGroups = {querySelector:()=>input,replaceChildren(){}};
  c.renderRoutingRules = ()=>{};
  assert.deepEqual(Array.from(c.getRoutingRulesSelection().moscow), ["delfi.lv","example.com"]);
});
