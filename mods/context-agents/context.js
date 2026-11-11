import { div } from "gpui-kit";
import { h_flex } from "gpui-base";
import { appHome, exec, terminals, shared, setShared } from "herdr";
import { KEY, COLORS, band, percentLabel } from "./model.js";
export { currentReading, highestReading } from "./model.js";

export function badge(value, t, compact = false, id = "context-meter") {
  const state = band(value?.percent);
  const color = COLORS[state] ?? t.dim;
  const label = state === "unknown" ? "—" : percentLabel(value.percent);
  const counts = value?.used != null && value?.capacity ? `\n${Math.round(value.used).toLocaleString()} / ${Math.round(value.capacity).toLocaleString()} tokens` : "";
  const detail = state === "unknown" ? value?.reason ?? "Context usage unavailable or awaiting refresh." : `${label} context used${counts}\nLatest observed usage · ${value.source}${value.unknown ? `\n${value.unknown} other agent meter(s) unavailable; this is the highest observed.` : ""}`;
  return h_flex().id(id).flex_none().gap(4).items_center().px(compact ? 0 : 4).h(18).rounded(4)
    .text_size(10.5).text_color(color)
    .tooltip(`${detail}\nGreen <80% · Orange 80–99% · Red ≥100%\nContext usage, not weekly quota.`)
    .child(div().w(3).h(10).rounded(2).bg(color))
    .when(!compact, el => el.child(label));
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
