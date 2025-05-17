# Contributing to Velocitytree

We love your input! We want to make contributing to Velocitytree as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## We Develop with Github

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## We Use [Github Flow](https://guides.github.com/introduction/flow/index.html)

Pull requests are the best way to propose changes to the codebase. We actively welcome your pull requests:

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](LICENSE) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](https://github.com/gbechtold/Velocitytree/issues)

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/gbechtold/Velocitytree/issues/new).

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/gbechtold/Velocitytree.git
   cd Velocitytree
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   pip install -e .
   ```

4. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=velocitytree

# Run specific test file
pytest tests/test_core.py

# Run tests in parallel
pytest -n auto
```

## Code Style

We use several tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

Run all checks:
```bash
black velocitytree/
isort velocitytree/
flake8 velocitytree/
mypy velocitytree/
```

Or use pre-commit:
```bash
pre-commit run --all-files
```

## Documentation

Documentation is built using Sphinx:

```bash
cd docs
make html
```

View the documentation locally:
```bash
open docs/_build/html/index.html  # On macOS
xdg-open docs/_build/html/index.html  # On Linux
```

## Creating a Pull Request

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit:
   ```bash
   git add .
   git commit -m "Add some feature"
   ```

3. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a pull request from your fork to the main repository.

## Pull Request Guidelines

- Include tests for new functionality
- Update documentation as needed
- Add a changelog entry in the PR description
- Ensure all tests pass
- Keep your PR focused on a single feature/fix

## Release Process

Releases are handled by maintainers:

1. Update version in `velocitytree/__init__.py`
2. Update CHANGELOG.md
3. Create a git tag:
   ```bash
   git tag -a v0.1.0 -m "Release version 0.1.0"
   git push origin v0.1.0
   ```
4. GitHub Actions will automatically publish to PyPI

## Community

- Join our [Discord server](https://discord.gg/velocitytree)
- Follow us on [Twitter](https://twitter.com/velocitytree)
- Read our [blog](https://blog.velocitytree.io)

## License

By contributing, you agree that your contributions will be licensed under its MIT License.