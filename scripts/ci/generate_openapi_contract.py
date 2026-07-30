from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from forgeml.main import create_app
from forgeml.platform.config import Settings

DEFAULT_OUTPUT_PATH = Path("contracts/openapi/forgeml.v1.openapi.json")


def generate_openapi_schema() -> dict[str, Any]:
    app = create_app(Settings(environment="contract", rate_limit_enabled=False))
    return app.openapi()


def serialize_openapi_schema(schema: dict[str, Any]) -> str:
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def write_openapi_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_openapi_schema(generate_openapi_schema()),
        encoding="utf-8",
    )


def check_openapi_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> bool:
    if not output_path.is_file():
        return False
    expected = serialize_openapi_schema(generate_openapi_schema())
    actual = output_path.read_text(encoding="utf-8")
    return actual == expected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate or verify the canonical ForgeML OpenAPI contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in OpenAPI contract.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when the checked-in OpenAPI contract is stale.",
    )
    args = parser.parse_args(argv)

    if args.check:
        if check_openapi_contract(args.output):
            print(f"PASS OpenAPI contract is current: {args.output}")
            return 0
        print(
            "FAIL OpenAPI contract is stale. "
            f"Regenerate it with: python {Path(__file__).as_posix()} --output {args.output}"
        )
        return 1

    write_openapi_contract(args.output)
    print(f"Wrote OpenAPI contract: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
