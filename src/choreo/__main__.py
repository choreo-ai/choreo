"""Minimal CLI entry point.

Real commands (`choreoai init`, `choreoai run`, ...) are on the roadmap. For now
this just confirms a working install and points at the project.
"""

from choreo import __version__


def main() -> None:
    print(f"ChoreoAI {__version__} - multi-agent systems, in production.")
    print("Early stage: the API is still being designed.")
    print("See https://github.com/choreo-ai/choreoai")


if __name__ == "__main__":
    main()
