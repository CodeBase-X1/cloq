# Contributing to Cloq

First off, thanks for considering contributing to Cloq! 🎭 Every contribution helps make LLM development safer for everyone.

## 🚀 Quick Start

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/cloq.git
cd cloq

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# 3. Install in development mode
pip install -e ".[all]"

# 4. Install pre-commit hooks
pre-commit install

# 5. Run tests to make sure everything works
pytest tests/ -v
```

## 🔧 Development Workflow

### Making Changes

1. Create a branch: `git checkout -b feature/my-awesome-feature`
2. Make your changes
3. Run checks: `make check` (lint + type-check + test)
4. Commit with a clear message
5. Push and open a PR

### Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/
```

### Testing

```bash
# Run all tests with coverage
make test

# Run specific tests
pytest tests/test_detection/test_secrets.py -v

# Run without coverage (faster)
make test-fast
```

### Type Checking

```bash
mypy src/cloq/
```

## 📝 Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation only
- `test:` — Adding or updating tests
- `refactor:` — Code change that neither fixes a bug nor adds a feature
- `perf:` — Performance improvement
- `ci:` — CI/CD changes

## 🧪 Adding a New Detector

Cloq uses a plugin architecture for detectors. To add a new one:

1. Create a new file in `src/cloq/detection/`
2. Subclass `BaseDetector`
3. Implement the `detect()` method
4. Add tests in `tests/test_detection/`
5. Register it in the pipeline

```python
from cloq.detection.base import BaseDetector, DetectionResult

class MyDetector(BaseDetector):
    name = "my_detector"

    def detect(self, text: str) -> list[DetectionResult]:
        # Your detection logic here
        ...
```

## 🐛 Reporting Bugs

Use the [Bug Report template](https://github.com/cloq-dev/cloq/issues/new?template=bug_report.yml) and include:

- Cloq version (`cloq --version`)
- Python version
- Operating system
- Steps to reproduce
- Expected vs. actual behavior

## 💡 Feature Requests

Use the [Feature Request template](https://github.com/cloq-dev/cloq/issues/new?template=feature_request.yml) and describe:

- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered

## 📜 License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
