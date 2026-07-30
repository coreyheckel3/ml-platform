from pathlib import Path

from scripts.ci.check_frontend_bundle_budget import check_bundle_budget


def test_bundle_budget_passes_when_chunks_are_under_limit(tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "entry.js").write_text("a" * 128, encoding="utf-8")
    (assets_dir / "route.js").write_text("b" * 64, encoding="utf-8")

    result = check_bundle_budget(tmp_path, max_js_chunk_bytes=256)

    assert result.passed
    assert [asset.path.name for asset in result.assets] == ["entry.js", "route.js"]
    assert result.violations == ()


def test_bundle_budget_reports_chunks_over_limit(tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "entry.js").write_text("a" * 512, encoding="utf-8")
    (assets_dir / "route.js").write_text("b" * 64, encoding="utf-8")

    result = check_bundle_budget(tmp_path, max_js_chunk_bytes=256)

    assert not result.passed
    assert [asset.path.name for asset in result.violations] == ["entry.js"]
