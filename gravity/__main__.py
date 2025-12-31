import argparse
from pathlib import Path
from typing import NoReturn

from gravity.application import build_application
from gravity.config import load_config


def main() -> NoReturn:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Path to configuration file",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    app = build_application(cfg)

    raise SystemExit(app.run())


if __name__ == "__main__":
    main()
