import argparse
from pathlib import Path
from typing import NoReturn

from gravity.application import build_application, run_benchmark, run_selftest
from gravity.config import load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=["run", "benchmark", "selftest"],
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Path to configuration file",
    )
    return parser.parse_args()


def main() -> NoReturn:
    args = parse_args()

    cfg = load_config(args.config)

    if args.mode == "run":
        app = build_application(cfg)
        res = app.run()
    elif args.mode == "benchmark":
        res = run_benchmark(cfg)
    elif args.mode == "selftest":
        res = run_selftest(cfg)
    else:
        res = 1

    raise SystemExit(res)


if __name__ == "__main__":
    main()
