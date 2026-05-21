"""Allow running cloq as a module: python -m cloq."""

from cloq.cli.main import app

if __name__ == "__main__":
    app()
