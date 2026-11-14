import { div, PathBuilder } from "gpui-kit";
import { appHome, exec, terminals, shared, setShared } from "herdr";
import { KEY, COLORS, band, percentLabel, ringPoint } from "./model.js";
export { currentReading, highestReading } from "./model.js";

// A 22px ring: a 1.5px track and arc, with the whole percentage inside as a
// bare number. Small enough for a row, wide enough for "100" without the sign.
const RING = 22;
const coord = (n) => `${Math.round(n * 1000) / 1000}%`;
const trackPath = () => PathBuilder.stroke(1.5)
  .move_to("50%", "8%")
  .arc_to("42%", "42%", 0, false, true, "50%", "92%")
  .arc_to("42%", "42%", 0, false, true, "50%", "8%")
  .build();
const arcPath = (percent) => {
  const start = ringPoint(0), end = ringPoint(percent);
  return PathBuilder.stroke(1.5).move_to(coord(start.x), coord(start.y))
    .arc_to("42%", "42%", 0, percent > 50, true, coord(end.x), coord(end.y))
    .build();
};

export function badge(value, t, compact = false, id = "context-meter") {
  const state = band(value?.percent);
  const color = COLORS[state] ?? t.dim;
  const label = state === "unknown" ? "—" : percentLabel(value.percent);
  const short = state === "unknown" ? "—" : value.percent >= 1000 ? "999+" : `${Math.floor(value.percent)}`;
  const counts = value?.used != null && value?.capacity ? `\n${Math.round(value.used).toLocaleString()} / ${Math.round(value.capacity).toLocaleString()} tokens` : "";
  const detail = state === "unknown" ? value?.reason ?? "Context usage unavailable or awaiting refresh." : `${label} context used${counts}\nLatest observed usage · ${value.source}${value.unknown ? `\n${value.unknown} other agent meter(s) unavailable; this is the highest observed.` : ""}`;
  const percent = state === "unknown" ? null : Math.max(0, Math.min(100, value.percent));
  return div().id(id).w(compact ? 3 : RING).min_w(compact ? 3 : RING).max_w(compact ? 3 : RING)
    .h(compact ? 18 : RING).flex_none().relative().flex().items_center().justify_center()
    .tooltip(`${detail}\nGreen <80% · Orange 80–99% · Red ≥100%\nContext usage, not weekly quota.`)
    .when(compact, el => el.child(div().w(3).h(10).rounded(2).bg(color)))
    .when(!compact, el => el
      .child(window.paint_path(trackPath(), t.dim + "40").absolute().inset(0))
      .when(percent > 0, el => el.child(window.paint_path(percent >= 100 ? trackPath() : arcPath(percent), color).absolute().inset(0)))
      .child(div().absolute().inset(0).flex().items_center().justify_center()
        .text_size(short.length > 3 ? 7 : short.length > 2 ? 8 : 9).font_weight(600).line_height(1).text_color(color).child(short)));
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
