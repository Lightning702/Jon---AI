const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

function setup(handler) {
  const messages = [], busy = [], calls = [], streams = new Map(), storage = new Map();
  let unload;
  const window = { addEventListener: (name, callback) => { unload = callback; } };
  const context = {
    window, document: { hidden: false }, AbortController, TextDecoder, setTimeout,
    localStorage: { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: (key) => storage.delete(key) },
    fetch: async (url, options = {}) => {
      calls.push({ url, options });
      const response = handler && handler(url, options);
      if (response) return response;
      return {
        ok: true,
        body: new ReadableStream({
          start(controller) {
            streams.set(url, controller);
            options.signal.addEventListener("abort", () => controller.error(new DOMException("Aborted", "AbortError")), { once: true });
          },
        }),
      };
    },
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../electron/petHarness.js"), "utf8"), context);
  const bridge = window.createPetHarness({ base: "/api", say: (text) => messages.push(text), state: () => {}, busy: (value) => busy.push(value), isBusy: () => false });
  return {
    bridge, messages, busy, calls, storage,
    emit: (url, data) => streams.get(url).enqueue(new TextEncoder().encode("data: " + JSON.stringify(data) + "\n\n")),
    close: () => unload(),
  };
}

const tick = () => new Promise((resolve) => setImmediate(resolve));

test("MiniJon approves exactly the displayed task and resets after completion", async () => {
  const env = setup((url) => url === "/api/harness/message" ? { ok: true, json: async () => ({ text: "Erlaubt" }) } : null);
  const following = env.bridge.follow("task1");
  await tick();
  env.emit("/api/harness/tasks/task1/events", { type: "snapshot", task: { id: "task1", status: "waiting_approval", goal: "Test", step: 2, changes: [], pending: { id: "approval7", args: { command: "npm test", cwd: "C:/project" } } } });
  await tick();
  assert(env.messages.some((text) => text.includes("npm test") && text.includes("C:/project")));
  assert.equal(await env.bridge.command("/ja"), true);
  const sent = env.calls.find((call) => call.url === "/api/harness/message");
  assert.equal(JSON.parse(sent.options.body).text, "/erlauben task1 approval7");
  env.emit("/api/harness/tasks/task1/events", { type: "snapshot", task: { id: "task1", status: "done", goal: "Test", step: 3, changes: [], summary: "Geprüft", pending: null } });
  await tick();
  assert.equal(env.bridge.active(), false);
  assert.equal(env.busy.at(-1), false);
  assert.equal(env.storage.has("mini_jon_task"), false);
  env.close();
  await following;
});

test("Failed cancellation keeps the running task visible", async () => {
  const env = setup((url) => url.endsWith("/cancel") ? { ok: false, status: 503 } : null);
  const following = env.bridge.follow("task2");
  await tick();
  await env.bridge.cancel();
  assert.equal(env.bridge.active(), true);
  assert.equal(env.busy.at(-1), true);
  assert(env.messages.some((text) => text.includes("Stopp nicht bestätigt")));
  env.close();
  await following;
});

test("Missing restored task releases MiniJon instead of leaving it busy", async () => {
  const env = setup((url) => url.includes("/tasks/missing/") ? { ok: false, status: 404 } : null);
  await env.bridge.follow("missing");
  assert.equal(env.bridge.active(), false);
  assert.equal(env.busy.at(-1), false);
  assert(env.messages.some((text) => text.includes("nicht mehr verfügbar")));
  env.close();
});
