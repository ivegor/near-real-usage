"""Demo video: slide contents and layout; encoding with ffmpeg is checked separately."""
import json
from pathlib import Path

from matplotlib.figure import Figure

from thesis import charts, video


def test_slides_quote_the_summary_without_gaps():
    s = json.loads((Path(__file__).resolve().parent.parent / "docs" / "summary.json").read_text(encoding="utf-8"))
    spec = video.slides(s)
    text = " ".join(x["head"] + " " + x["line"] for x in spec)
    assert 6 <= len(spec) <= 9 and 50 <= sum(x["sec"] for x in spec) <= 95
    assert "nan" not in text.lower() and "None" not in text
    assert f"{s['clients']['months'][s['clients']['latest_month']]['accounts_for_half_of_txs']} accounts send half" in text
    # the headline of the accounts slide is what holds without a caveat: the heavy accounts, not the fall of the regular ones
    assert f"{s['segments']['metrics']['heavy_accounts']['latest']:,.0f} heavy accounts send" in text
    # a chart slide shows its supporting line on one row: 115 characters fit the 1280-pixel frame, 117 ran off its edge
    assert all(len(x["line"]) <= 115 for x in spec if x["chart"]), [len(x["line"]) for x in spec]


def test_slides_do_not_need_the_top_ten_comparison():
    """After a later run of the query the file of largest accounts may hold no month of the sample's window."""
    s = json.loads((Path(__file__).resolve().parent.parent / "docs" / "summary.json").read_text(encoding="utf-8"))
    with_it = next(x["line"] for x in video.slides(s) if x["chart"] == "signer_census")
    assert ", top 10 accounts " in with_it and with_it.endswith("%.")
    del s["cross_check"]["recent"]["top10_tx_share"]
    without = next(x["line"] for x in video.slides(s) if x["chart"] == "signer_census")
    assert "top 10" not in without and without.endswith("%.") and with_it.startswith(without[:-1])


def test_statistical_headlines_fit_the_video_frame(tmp_path, monkeypatch):
    s = json.loads((Path(__file__).resolve().parents[1] / "docs/summary.json").read_text())
    slide = next(x for x in video.slides(s) if x["chart"] == "lead_lag")

    def check_frame(fig, *args, **kwargs):
        fig.canvas.draw()
        boxes = [t.get_window_extent(fig.canvas.get_renderer()) for t in fig.texts]
        assert all(b.x0 >= 0 and b.x1 <= fig.bbox.width and b.y0 >= 0 and b.y1 <= fig.bbox.height for b in boxes)
        assert boxes[0].y0 > boxes[1].y1  # the headline cannot cover its supporting evidence

    monkeypatch.setattr(Figure, "savefig", check_frame)
    video._render(slide, tmp_path / "no_lead.png")
    s["lead_vs_price_holm_leads"] = [{"metric": "txns", "lag_weeks": 3, "p": 0.0}]
    video._render({**slide, "head": charts._takeaway("lead_lag", s)}, tmp_path / "lead.png")
