"""Demo video: a slideshow rendered from the build outputs, so the numbers on screen are the ones in summary.json.

`python -m thesis video` writes demo/near-real-usage.mp4 (needs ffmpeg on PATH). Run it after `python -m thesis build`.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import textwrap
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS, OUT = ROOT / "docs", ROOT / "demo" / "near-real-usage.mp4"
INK, ACCENT, MUTED = "#1f2328", "#00a27a", "#57606a"


def slides(s: dict) -> list[dict]:
    """What each slide says: headline, one supporting line, the chart it shows, seconds on screen."""
    p, c, v = s["population"]["segments"], s["clients"], s["value_capture"]
    al = p["all"]
    sg = s["segments"]["metrics"]
    latest = c["months"][c["latest_month"]]
    cc = s.get("cross_check", {}).get("recent")
    out = [
        {"head": f"NEAR lost {abs(al['accounts']['pct_change']):.0f}% of its active accounts in a year.",
         "line": "We counted every one. Built at NEAR HACKATHON, track Investment Thesis.", "chart": None, "sec": 6},
        {"head": f"{s['population']['reward_apps_share_of_lost']['accounts'] * 100:.0f}% of the accounts that left belonged to reward apps.",
         "line": f"Accounts whose fees an app paid: {sg['sponsored_accounts']['prior'] / 1e6:.1f}M a year ago, "
                 f"{sg['sponsored_accounts']['latest'] / 1e6:.2f}M now.",
         "chart": "population", "sec": 10},
        # the count of regular accounts is not the headline: part of its fall is one game moving its players to a relayer
        {"head": f"{sg['heavy_accounts']['latest']:,.0f} heavy accounts send "
                 f"{s['segments']['heavy_share_of_independent_self_paid_txs']['latest'] * 100:.0f}% of the self-paid transactions.",
         "line": f"Outside reward apps. Regular accounts (10 to 999 a month) number {sg['regular_accounts']['latest']:,.0f}; "
                 f"their low was {s['segments']['regular_accounts_low']['value']:,.0f} in "
                 f"{datetime.strptime(s['segments']['regular_accounts_low']['month'], '%Y-%m'):%B %Y}.",
         "chart": "segments", "sec": 11},
        {"head": f"{latest['accounts_for_half_of_txs']} accounts send half of all transactions.",
         "line": f"Reward and wallet apps are still {c['reward_apps_share']['latest'] * 100:.0f}% of them; trading, Intents, tokens and "
                 f"bridges are {c['finance_share']['latest'] * 100:.0f}% and grew {c['finance_txs']['pct_change']:+.0f}% in a year.",
         "chart": "clients", "sec": 12},
        {"head": f"Buybacks cover {v['buyback_coverage_of_new_supply'] * 100:.0f}% of the new NEAR issued.",
         "line": f"Intents fees are {v['intents_fees_vs_l1_fees']:.0f}x the network's own fees; NEAR keeps "
                 f"{v['captured_share_of_gross_fees'] * 100:.0f}% of them and buys NEAR with it: ${v['buyback_usd_annualized'] / 1e6:.1f}M a year.",
         "chart": "value_capture", "sec": 10},
    ]
    if cc:
        out.append({"head": "Checked a second way, with no API key.",
                    "line": f"A random sample of blocks agrees with the full count: relayed transactions "
                            f"{cc['relayed_tx_share']['sample'] * 100:.0f}% vs {cc['relayed_tx_share']['bigquery'] * 100:.0f}%, "
                            f"top 10 accounts {cc['top10_tx_share']['sample'] * 100:.0f}% vs {cc['top10_tx_share']['bigquery'] * 100:.0f}%.",
                    "chart": "signer_census", "sec": 9})
    n_out = sum(len(x["outside_band"]) for x in s["lead_vs_price"].values())
    out += [
        {"head": "Usage does not lead price.",
         "line": f"{n_out} of {17 * len(s['lead_vs_price'])} weekly lead-lag tests fall outside the noise band; about 4 are expected by chance.",
         "chart": "lead_lag", "sec": 8},
        {"head": "Every number is rebuilt by one command.",
         "line": f"python -m thesis build    |    github.com/ivegor/near-real-usage    |    "
                 f"{len(s.get('predictions', {}).get('items', []))} dated predictions, scored by the build",
         "chart": None, "sec": 7},
    ]
    return out


def _render(slide: dict, path: Path) -> None:
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100)
    fig.patch.set_facecolor("white")
    big = slide["chart"] is None
    fig.text(0.5 if big else 0.05, 0.60 if big else 0.90, "\n".join(textwrap.wrap(slide["head"], 54 if big else 70)),
             fontsize=34 if big else 25, color=INK, weight="bold", ha="center" if big else "left", va="center")
    fig.text(0.5 if big else 0.05, 0.40 if big else 0.795, "\n".join(textwrap.wrap(slide["line"], 80 if big else 120)),
             fontsize=17 if big else 14.5, color=MUTED, ha="center" if big else "left", va="center")
    if not big:
        ax = fig.add_axes([0.04, 0.03, 0.92, 0.70])
        ax.imshow(mpimg.imread(DOCS / f"{slide['chart']}.png"))
        ax.axis("off")
    fig.add_artist(plt.Line2D([0.05, 0.95], [0.985, 0.985], color=ACCENT, linewidth=6))
    fig.savefig(path, dpi=100)
    plt.close(fig)


def build(out: Path = OUT) -> Path:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not found on PATH")
    spec = slides(json.loads((DOCS / "summary.json").read_text(encoding="utf-8")))
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        lines = []
        for i, slide in enumerate(spec):
            png = Path(tmp) / f"slide_{i:02d}.png"
            _render(slide, png)
            lines += [f"file '{png}'", f"duration {slide['sec']}"]
        lines.append(lines[-2])  # the concat demuxer needs the last file repeated
        (Path(tmp) / "slides.txt").write_text("\n".join(lines), encoding="utf-8")
        total = sum(slide["sec"] for slide in spec)  # without -t the repeated last slide stays on screen twice as long
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(Path(tmp) / "slides.txt"),
                        "-vf", "fps=30,format=yuv420p", "-t", str(total), "-c:v", "libx264", "-movflags", "+faststart", str(out)],
                       check=True)
    return out
