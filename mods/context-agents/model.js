export const KEY = "context-colors.snapshot";
export const COLORS = { green: "#47b881", orange: "#e6a23c", red: "#ed6a6a" };
export const band = (percent) => !Number.isFinite(percent) || percent < 0 ? "unknown" : percent >= 100 ? "red" : percent >= 80 ? "orange" : "green";
export const percentLabel = (percent) => `${Math.floor(percent * 10) / 10}%`;
export const sessionName = title => title.trim().replace(/^[\u2800-\u28ff]\s*/, "").replace(/^(?:\[[^\]]{1,8}\]\s*)?(?:Action Required|Working|Ready|Waiting|Idle|Done)\s*\|\s*/, "").replace(/ \| [^|]*$/, "").trim();

export function currentReading(terminal, snapshot, now = Date.now()) {
  const value = snapshot?.terminals?.[terminal?.address];
  const age = now - (snapshot?.collectedAt ?? 0);
  const app = terminal?.report?.app ?? terminal?.app ?? terminal?.program?.key ?? "";
  const title = app === "codex" ? sessionName(terminal?.title ?? "") : terminal?.title ?? "";
  if (!value || age < 0 || age > 35000 || value.identity?.title !== title || value.identity?.pid !== (terminal?.foreground?.pid ?? null) || value.identity?.app !== app) return null;
  return value;
}

export function highestReading(values) {
  const known = values.filter(value => band(value?.percent) !== "unknown");
  const highest = known.reduce((best, value) => !best || value.percent > best.percent ? value : best, null);
  const unknown = values.length - known.length;
  // Green means every agent was measured. Warnings can still show a known
  // lower bound when another agent has an unavailable meter.
  if (unknown && (!highest || band(highest.percent) === "green")) return { percent: null, reason: `${unknown} agent context meter(s) unavailable.${highest ? ` Highest observed: ${percentLabel(highest.percent)}.` : ""}` };
  return highest ? { ...highest, unknown } : null;
}
