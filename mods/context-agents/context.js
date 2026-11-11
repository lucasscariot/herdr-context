import { div } from "gpui-kit";
import { appHome, exec, terminals, shared, setShared } from "herdr";
import { KEY, COLORS, band, percentLabel } from "./model.js";
export { currentReading, highestReading } from "./model.js";

export function badge(value, t, compact = false, id = "context-meter") {
  const state = band(value?.percent);
  const color = COLORS[state] ?? t.dim;
  const label = state === "unknown" ? "—" : percentLabel(value.percent);
  const compactLabel = state === "unknown" ? "—" : value.percent >= 1000 ? "999+" : `${Math.floor(value.percent)}%`;
  const counts = value?.used != null && value?.capacity ? `\n${Math.round(value.used).toLocaleString()} / ${Math.round(value.capacity).toLocaleString()} tokens` : "";
  const detail = state === "unknown" ? value?.reason ?? "Context usage unavailable or awaiting refresh." : `${label} context used${counts}\nLatest observed usage · ${value.source}${value.unknown ? `\n${value.unknown} other agent meter(s) unavailable; this is the highest observed.` : ""}`;
  return div().id(id).w(compact ? 3 : 30).min_w(compact ? 3 : 30).max_w(compact ? 3 : 30)
    .h(18).flex_none().flex().items_center().justify_end().text_right().whitespace_nowrap().overflow_hidden()
    .text_size(10.5).text_color(color)
    .tooltip(`${detail}\nGreen <80% · Orange 80–99% · Red ≥100%\nContext usage, not weekly quota.`)
    .when(compact, el => el.child(div().w(3).h(10).rounded(2).bg(color)))
    .when(!compact, el => el.child(compactLabel));
}

export class ContextMonitor {
  constructor() { this.pending = false; }
  refresh(cx) {
    if (this.pending) return;
    const list = terminals().filter(t => t.state === "live" && (t.report?.app || t.program?.agent)).map(t => ({
      address: t.address, title: t.title ?? "", state: t.state,
      app: t.report?.app ?? t.program?.key ?? "", foreground: { pid: t.foreground?.pid },
    }));
    this.pending = true;
    cx.spawn(async (cx) => {
      try {
        const result = await exec("python3", [`${appHome()}/mods/context-agents/collector.py`, "--terminals", JSON.stringify(list)], { timeout: 15000 });
        if (result.code !== 0) throw new Error("Context collector failed");
        setShared(KEY, JSON.parse(result.stdout));
      } catch {
        setShared(KEY, { collectedAt: Date.now(), terminals: {} });
      } finally { this.pending = false; cx.notify(); }
    });
  }
}

export const snapshot = () => shared(KEY);
