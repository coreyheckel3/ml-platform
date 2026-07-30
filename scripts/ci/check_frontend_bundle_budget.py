from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DIST_DIR = Path("frontend/dist")
DEFAULT_MAX_JS_CHUNK_BYTES = 500_000


@dataclass(frozen=True)
class BundleAsset:
    path: Path
    size_bytes: int


@dataclass(frozen=True)
class BundleBudgetResult:
    assets: tuple[BundleAsset, ...]
    violations: tuple[BundleAsset, ...]
    max_js_chunk_bytes: int

    @property
    def passed(self) -> bool:
        return not self.violations


def check_bundle_budget(
    dist_dir: Path = DEFAULT_DIST_DIR,
    max_js_chunk_bytes: int = DEFAULT_MAX_JS_CHUNK_BYTES,
) -> BundleBudgetResult:
    assets = tuple(
        sorted(
            (
                BundleAsset(path=asset, size_bytes=asset.stat().st_size)
                for asset in dist_dir.glob("assets/*.js")
            ),
            key=lambda asset: asset.path.name,
        )
    )
    violations = tuple(asset for asset in assets if asset.size_bytes > max_js_chunk_bytes)
    return BundleBudgetResult(
        assets=assets,
        violations=violations,
        max_js_chunk_bytes=max_js_chunk_bytes,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Enforce ForgeML frontend JavaScript chunk size budgets."
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=DEFAULT_DIST_DIR,
        help="Built Vite distribution directory.",
    )
    parser.add_argument(
        "--max-js-chunk-bytes",
        type=int,
        default=DEFAULT_MAX_JS_CHUNK_BYTES,
        help="Maximum allowed size for an individual JavaScript chunk.",
    )
    args = parser.parse_args(argv)

    result = check_bundle_budget(args.dist_dir, args.max_js_chunk_bytes)
    if not result.assets:
        print(f"FAIL no JavaScript chunks found under {args.dist_dir / 'assets'}")
        return 1

    largest_asset = max(result.assets, key=lambda asset: asset.size_bytes)
    if result.passed:
        print(
            "PASS frontend bundle budget: "
            f"{len(result.assets)} JS chunks, largest={largest_asset.size_bytes} bytes, "
            f"limit={result.max_js_chunk_bytes} bytes"
        )
        return 0

    print(
        "FAIL frontend bundle budget: "
        f"{len(result.violations)} chunk(s) exceed {result.max_js_chunk_bytes} bytes"
    )
    for asset in result.violations:
        print(f"- {asset.path}: {asset.size_bytes} bytes")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
