import sys


def info(message: str) -> None:
    print(message)


def error(message: str) -> None:
    print(message, file=sys.stderr)
