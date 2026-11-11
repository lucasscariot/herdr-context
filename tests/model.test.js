import assert from "node:assert/strict";
import { test } from "node:test";
import { band, currentReading, highestReading, percentLabel, sessionName } from "../mods/context-agents/model.js";

test("thresholds are based on exact usage and never clamp over 100%", () => {
  for (const [value, expected] of [[0, "green"], [79.999, "green"], [80, "orange"], [99.999, "orange"], [100, "red"], [145, "red"], [null, "unknown"], [-1, "unknown"], [NaN, "unknown"], [Infinity, "unknown"]]) assert.equal(band(value), expected);
  assert.equal(percentLabel(79.999), "79.9%");
  assert.equal(percentLabel(145.06), "145%");
});

test("a tab uses its worst agent and incomplete coverage cannot look green", () => {
  assert.equal(highestReading([{ percent: 35 }, { percent: 110 }]).percent, 110);
  assert.equal(highestReading([{ percent: 35 }, null]).percent, null);
  assert.equal(highestReading([{ percent: 85 }, null]).percent, 85);
  assert.equal(highestReading([{ percent: 85 }, null]).unknown, 1);
  assert.equal(highestReading([]), null);
});

test("readings expire and cannot leak across reused terminals or changed sessions", () => {
  const terminal = { address: "t1", title: "Task", app: "claude-code", foreground: { pid: 10 } };
  const value = { percent: 45, identity: { title: "Task", app: "claude-code", pid: 10 } };
  const snapshot = { collectedAt: 1000, terminals: { t1: value } };
  assert.equal(currentReading(terminal, snapshot, 2000), value);
  assert.equal(currentReading(terminal, snapshot, 37000), null);
  assert.equal(currentReading(terminal, snapshot, 900), null);
  assert.equal(currentReading({ ...terminal, title: "Another session" }, snapshot, 2000), null);
  assert.equal(currentReading({ ...terminal, foreground: { pid: 11 } }, snapshot, 2000), null);
  assert.equal(currentReading({ ...terminal, app: "cursor" }, snapshot, 2000), null);
});

test("Codex activity glyphs do not invalidate a session meter", () => {
  assert.equal(sessionName("⠇ Review code | repo"), "Review code");
  assert.equal(sessionName("[ . ] Action Required | Review code | repo"), "Review code");
  const terminal = { address: "t1", title: "⠇ Review code | repo", app: "codex" };
  const value = { percent: 81, identity: { title: "Review code", app: "codex", pid: null } };
  assert.equal(currentReading(terminal, { collectedAt: 1000, terminals: { t1: value } }, 2000), value);
});
