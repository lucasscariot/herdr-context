import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

function element() {
  const data = { nodes: [], elementId: null };
  let proxy;
  proxy = new Proxy(data, { get(target, key) {
    if (key in target) return target[key];
    if (key === "child") return child => { target.nodes.push(child); return proxy; };
    if (key === "children") return children => { target.nodes.push(...children); return proxy; };
    if (key === "id") return id => { target.elementId = id; return proxy; };
    if (key === "when") return (condition, callback) => condition ? callback(proxy) : proxy;
    return () => proxy;
  } });
  return proxy;
}

function agentIds(node) {
  if (!node || typeof node !== "object") return [];
  return [...(/^ag-t/.test(node.elementId ?? "") ? [node.elementId] : []), ...node.nodes.flatMap(agentIds)];
}

test("context highlights preserve Herdr priority groups, pinning, and within-group order", async () => {
  const statuses = ["blocked", "done", "working", "idle", "working"];
  const list = statuses.map((status, i) => ({ address: `t${i}`, status, seq: i, tab: `tab${i}`, space: "space", space_name: "Repo", title: `Task ${i}`, program: {}, pinned: false }));
  const changes = Object.fromEntries(list.map((agent, i) => [agent.address, { s: agent.status === "done" ? "idle" : agent.status, at: 1000 + i }]));
  let ordering;
  let percentages = [5, 50, 99, 140, 10];
  globalThis.__herdrOrderTest = {
    View: class {}, div: element, image: element, svg: element, v_flex: element, h_flex: element,
    agents: () => list, terminals: () => list.map(a => ({ ...a, state: "live" })), panes: () => [], focused: () => null,
    spaces: () => [{ tabs: [] }], run() {}, theme: () => ({}), shared: () => "priority", setShared() {},
    setAgentOrder: addresses => { ordering = addresses; }, openOverlay() {}, closeOverlay() {}, props: () => ({}), window: () => ({}), layout: () => ({}),
    ContextMonitor: class { refresh() {} }, badge: element,
    currentReading: terminal => ({ percent: percentages[Number(terminal.address.slice(1))] }), snapshot: () => ({}), highestReading: () => null,
    localStorage: { getItem: key => key === "changed" ? JSON.stringify(changes) : null, setItem() {}, removeItem() {} },
  };
  const source = (await readFile(new URL("../mods/context-agents/main.js", import.meta.url), "utf8")).replace(/^import .*;\n/gm, "");
  const names = Object.keys(globalThis.__herdrOrderTest).join(", ");
  const { default: Agents } = await import(`data:text/javascript;base64,${Buffer.from(`const { ${names} } = globalThis.__herdrOrderTest;\n${source}`).toString("base64")}`);
  const view = new Agents();
  const cx = { timer: { every() {} }, notify() {} };
  view.init({}, cx);
  assert.deepEqual(agentIds(view.render(cx)), ["ag-t0", "ag-t1", "ag-t4", "ag-t2", "ag-t3"]);
  assert.deepEqual(ordering, ["t0", "t1", "t4", "t2", "t3"]);
  percentages = [150, 5, 10, 20, 99];
  assert.deepEqual(agentIds(view.render(cx)), ["ag-t0", "ag-t1", "ag-t4", "ag-t2", "ag-t3"]);
  list[3].pinned = true;
  assert.deepEqual(agentIds(view.render(cx)), ["ag-t3", "ag-t0", "ag-t1", "ag-t4", "ag-t2"]);
  delete globalThis.__herdrOrderTest;
});
