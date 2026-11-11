"""Render the README's sample Herdr interface as SVG using only the standard library."""

from html import escape
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def color(percent):
    if percent is None:
        return "#94a3b8"
    return "#ed6a6a" if percent >= 100 else "#e6a23c" if percent >= 80 else "#47b881"


def render(data):
    parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="670" viewBox="0 0 1120 670" role="img" aria-labelledby="title description">
<title id="title">Herdr Context Colors</title>
<desc id="description">Illustrative agent list with Done, Working, and Idle groups, fixed-width context percentages, and a detailed hover card. Sample sessions show green, orange, red, and unknown readings.</desc>
<defs>
  <linearGradient id="backdrop" x2="1" y2="1"><stop stop-color="#101c31"/><stop offset="1" stop-color="#141526"/></linearGradient>
  <linearGradient id="card" x2="1" y2="1"><stop stop-color="#17243b"/><stop offset="1" stop-color="#192136"/></linearGradient>
  <clipPath id="frame"><rect x="24" y="24" width="1072" height="622" rx="16"/></clipPath>
</defs>
<rect width="1120" height="670" rx="22" fill="url(#backdrop)"/>
<g clip-path="url(#frame)">
<rect x="24" y="24" width="1072" height="622" fill="#0f172a"/>
<rect x="24" y="24" width="1072" height="48" fill="#19243a"/>
<circle cx="47" cy="48" r="5" fill="#fb7185"/><circle cx="65" cy="48" r="5" fill="#fbbf24"/><circle cx="83" cy="48" r="5" fill="#47b881"/>
<g font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" fill="#e2e8f0">
<text x="560" y="54" text-anchor="middle" font-size="13" fill="#94a3b8">Herdr · Context Colors</text>
<path d="M448 72V612 M24 612H1096" stroke="#263247"/>
<text x="48" y="111" font-size="12" font-weight="600" fill="#94a3b8">AGENTS</text>
<circle cx="415" cy="106" r="7" fill="none" stroke="#64748b" stroke-width="1.5"/>
<path d="M415 102v5l3 2" fill="none" stroke="#64748b" stroke-width="1.5"/>
''']
    y = 147
    for group in data["groups"]:
        parts.append(f'<text x="48" y="{y}" font-size="13" font-weight="600" fill="{group["color"]}">{escape(group["name"])} <tspan fill="#64748b">{len(group["agents"])}</tspan></text>')
        y += 32
        for agent in group["agents"]:
            if agent.get("selected"):
                parts.append(f'<rect x="36" y="{y - 23}" width="400" height="38" rx="8" fill="#1e2b40"/>')
            parts.append(f'<rect x="49" y="{y - 16}" width="20" height="20" rx="6" fill="#23324b"/>')
            parts.append(f'<text x="59" y="{y - 1}" text-anchor="middle" font-size="12" font-weight="600" fill="#c4b5fd">{escape(agent["icon"])}</text>')
            parts.append(f'<text x="80" y="{y}" font-size="13" fill="{("#e2e8f0" if agent["status"] != "idle" else "#94a3b8")}">{escape(agent["name"])}</text>')
            parts.append(f'<text x="337" y="{y}" text-anchor="end" font-size="11" fill="#64748b">{agent["minutes"]}m</text>')
            percent = agent["percent"]
            label = "—" if percent is None else f"{int(percent)}%"
            parts.append(f'<text x="396" y="{y}" text-anchor="end" font-size="12" fill="{color(percent)}">{label}</text>')
            if agent["status"] == "working":
                parts.append(f'<circle cx="419" cy="{y - 5}" r="5" fill="none" stroke="#665c38" stroke-width="2"/><path d="M414,{y - 5}a5,5 0 0,1 7,-4" fill="none" stroke="#e6a23c" stroke-width="2" stroke-linecap="round"/>')
            else:
                parts.append(f'<circle cx="419" cy="{y - 5}" r="3.5" fill="{("#93c5fd" if agent["status"] == "done" else "none")}" stroke="{("#93c5fd" if agent["status"] == "done" else "#64748b")}" stroke-width="1.5"/>')
            y += 43
        y += 17
    parts.append('''
<rect x="470" y="88" width="171" height="31" rx="7" fill="#243047"/>
<text x="485" y="108" font-size="12">Investigate requests</text>
<text x="627" y="108" text-anchor="end" font-size="12" fill="#e6a23c">86%</text>
<text x="665" y="108" font-size="12" fill="#94a3b8">Polish navigation</text>
<text x="796" y="108" font-size="12" fill="#47b881">68%</text>
<path d="M448 135H1096" stroke="#263247"/>
<text x="486" y="191" font-size="11" font-weight="600" letter-spacing="2" fill="#5eead4">A LITTLE MORE VISIBILITY</text>
<text x="486" y="232" font-size="31" font-weight="650">Know which session</text>
<text x="486" y="272" font-size="31" font-weight="650">is filling up.</text>
<text x="486" y="307" font-size="14" fill="#94a3b8">Your groups. Your order. One compact reading.</text>
<rect x="486" y="341" width="400" height="161" rx="12" fill="url(#card)" stroke="#34425b"/>
<circle cx="509" cy="368" r="4" fill="#e6a23c"/>
<text x="523" y="373" font-size="14" font-weight="600" fill="#e6a23c">86.4% context used</text>
<text x="506" y="404" font-size="13" fill="#cbd5e1">410,400 / 475,000 tokens</text>
<text x="506" y="430" font-size="12" fill="#94a3b8">Latest observed usage · Codex latest request</text>
<path d="M506 449H866" stroke="#34425b"/>
<text x="506" y="477" font-size="12" fill="#c4b5fd">Hover for the precise reading.</text>
<circle cx="491" cy="548" r="4" fill="#47b881"/><text x="504" y="552" font-size="12" fill="#94a3b8">&lt;80%</text>
<circle cx="580" cy="548" r="4" fill="#e6a23c"/><text x="593" y="552" font-size="12" fill="#94a3b8">80–99%</text>
<circle cx="688" cy="548" r="4" fill="#ed6a6a"/><text x="701" y="552" font-size="12" fill="#94a3b8">≥100%</text>
<circle cx="791" cy="548" r="4" fill="#94a3b8"/><text x="804" y="552" font-size="12" fill="#94a3b8">Unknown</text>
<text x="48" y="633" font-size="11" fill="#64748b">SAMPLE SESSIONS · ILLUSTRATIVE PREVIEW</text>
<text x="1072" y="633" text-anchor="end" font-size="11" fill="#64748b">LOCAL READINGS · HERDR GUI</text>
</g></g>
<rect x="24" y="24" width="1072" height="622" rx="16" fill="none" stroke="#34425b"/>
</svg>
''')
    return "\n".join(parts)


def main():
    data = json.loads((HERE / "preview.json").read_text())
    (HERE / "preview.svg").write_text(render(data), encoding="utf8")


if __name__ == "__main__":
    main()
