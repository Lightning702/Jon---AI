const test = require("node:test");
const assert = require("node:assert/strict");
const {clampPosition, dragPosition} = require("../electron/petPosition.cjs");

test("drag can cross the boundary before the pet center changes screens", () => {
  assert.deepEqual(dragPosition({x: 1980, y: 400}, {x: 50, y: 80}), {x: 1930, y: 320});
  assert.deepEqual(dragPosition({x: -300, y: 400}, {x: 50, y: 80}), {x: -350, y: 320});
});

test("release keeps the entire pet visible on negative-coordinate monitors", () => {
  assert.deepEqual(clampPosition({x: -1500, y: -500}, {width: 380, height: 400}, {x: -1280, y: -200, width: 1280, height: 1000}), {x: -1280, y: -200});
  assert.deepEqual(clampPosition({x: 100, y: 900}, {width: 380, height: 400}, {x: -1280, y: -200, width: 1280, height: 1000}), {x: -380, y: 400});
});
