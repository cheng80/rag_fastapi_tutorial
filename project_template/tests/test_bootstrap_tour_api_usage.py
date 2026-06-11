from datetime import datetime
import os

from scripts.bootstrap_tour_api_usage import infer_counts_from_artifacts


def test_infer_counts_from_artifacts_counts_today_files(monkeypatch, tmp_path):
    generated = tmp_path / "generated" / "tour_api"
    raw = tmp_path / "raw" / "tourism_accessible"
    live = generated / "live_markdown"
    generated.mkdir(parents=True)
    raw.mkdir(parents=True)
    live.mkdir(parents=True)
    (generated / "서울_area_based_raw.json").write_text("{}", encoding="utf-8")
    (raw / "서울_1.md").write_text("# 서울", encoding="utf-8")
    (live / "부산_1.md").write_text("# 부산", encoding="utf-8")
    old = generated / "old_area_based_raw.json"
    old.write_text("{}", encoding="utf-8")
    old_time = datetime(2026, 5, 15, 1, 0).timestamp()
    os.utime(old, (old_time, old_time))

    monkeypatch.setattr("scripts.bootstrap_tour_api_usage.GENERATED_TOUR_API_DIR", generated)
    monkeypatch.setattr("scripts.bootstrap_tour_api_usage.RAW_SAMPLE_DIR", raw)
    monkeypatch.setattr("scripts.bootstrap_tour_api_usage.LIVE_MARKDOWN_DIR", live)

    counts = infer_counts_from_artifacts("2026-05-16")

    assert counts == {
        "areaBasedList2": 1,
        "detailCommon2": 2,
        "detailWithTour2": 2,
    }
