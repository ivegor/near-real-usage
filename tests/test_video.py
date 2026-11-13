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
