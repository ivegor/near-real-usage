"""Demo video: the slide texts come from the committed summary (rendering needs ffmpeg and is not tested)."""
import json
from pathlib import Path

from thesis import video


def test_slides_quote_the_summary_without_gaps():
    s = json.loads((Path(__file__).resolve().parent.parent / "docs" / "summary.json").read_text())
    spec = video.slides(s)
    text = " ".join(x["head"] + " " + x["line"] for x in spec)
    assert 6 <= len(spec) <= 9 and 50 <= sum(x["sec"] for x in spec) <= 95
    assert "nan" not in text.lower() and "None" not in text
    assert f"{s['clients']['months'][s['clients']['latest_month']]['accounts_for_half_of_txs']} accounts send half" in text
    # the headline of the accounts slide is what holds without a caveat: the heavy accounts, not the fall of the regular ones
    assert f"{s['segments']['metrics']['heavy_accounts']['latest']:,.0f} heavy accounts send" in text
    # a chart slide shows its supporting line on one row: 115 characters fit the 1280-pixel frame, 117 ran off its edge
    assert all(len(x["line"]) <= 115 for x in spec if x["chart"]), [len(x["line"]) for x in spec]
