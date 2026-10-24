import argparse
from .bootstrap import bootstrap
from .release import build, rollback
from .refresh import refresh


def main():
    parser = argparse.ArgumentParser(description="Shobi data lifecycle")
    parser.add_argument("command", choices=["bootstrap", "build", "refresh", "rollback"])
    parser.add_argument("--limit", type=int, help="Maximum original profiles requested in this run")
    parser.add_argument("--reference", help="MarvvRed snapshot root (bootstrap only)")
    args = parser.parse_args()
    if args.command == "bootstrap":
        bootstrap(args.reference)
        build()
    elif args.command == "build":
        build()
    elif args.command == "refresh":
        refresh(args.limit)
    else:
        rollback()


if __name__ == "__main__":
    main()
