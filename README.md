# Velocitytree 🌳⚡

[![PyPI version](https://badge.fury.io/py/velocitytree.svg)](https://badge.fury.io/py/velocitytree)
[![Python Versions](https://img.shields.io/pypi/pyversions/velocitytree.svg)](https://pypi.org/project/velocitytree/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/gbechtold/Velocitytree/workflows/Tests/badge.svg)](https://github.com/gbechtold/Velocitytree/actions)

## 🎯 The Problem We Solve

Ever struggled with:
- **Complex project structures** becoming unwieldy and hard to navigate?
- **AI assistants** lacking project context and generating irrelevant code?
- **Repetitive tasks** eating up your valuable development time?
- **Managing multiple workflows** across different projects?
- **Documentation** that gets out of sync with your codebase?

**Velocitytree is your solution!** 🚀

## ✨ Benefits

- **Flatten complex codebases** into manageable, AI-friendly formats
- **Boost AI coding accuracy** by providing perfect context to ChatGPT, Claude, and others
- **Accelerate development** with automated workflows and smart templates
- **Maintain project consistency** across your entire team
- **Plugin architecture** for unlimited extensibility

## 🚀 Quick Start (One-Line Install)

```bash
# Clone, setup environment, and install in one command:
git clone https://github.com/gbechtold/Velocitytree.git && cd Velocitytree && python3 -m venv venv && source venv/bin/activate && pip install -e .
```

## 💡 Basic Usage

Initialize a new project:
```bash
vtree init
```

Flatten your project structure for AI analysis:
```bash
vtree flatten --output context.md
```

Get AI assistance with your project:
```bash
vtree ask "How can I optimize this codebase?"
```

Create a documentation snapshot:
```bash
vtree flatten --format markdown --include "*.py" --output docs/structure.md
```

## 📦 Installation Options

### Quick Install (Recommended)

The one-liner above is the fastest way to get started. It automatically:
1. Clones the repository
2. Creates a virtual environment
3. Activates the environment
4. Installs Velocitytree in development mode

### From PyPI

```bash
pip install velocitytree
```

### Manual Installation

```bash
# 1. Clone the repository
git clone https://github.com/gbechtold/Velocitytree.git
cd Velocitytree

# 2. Create virtual environment (IMPORTANT!)
python3 -m venv venv

# 3. Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 4. Install in development mode
pip install -e .
```

### Using Setup Scripts

For convenience, we provide automated setup scripts:

**Unix/Mac:**
```bash
./scripts/setup.sh
```

**Windows:**
```powershell
.\scripts\setup.ps1
```

These scripts handle virtual environment creation and dependency installation automatically.

## 🔧 Core Commands

| Command | Description |
|---------|-------------|
| `vtree init` | Initialize a new Velocitytree project |
| `vtree flatten` | Create a flattened view of your project |
| `vtree context` | Extract project context for AI tools |
| `vtree ask` | Get AI assistance with your code |
| `vtree workflow` | Manage project workflows |
| `vtree plugin` | Manage plugins |

For detailed command options, use `vtree [command] --help`.

## 🌟 Key Features

### Project Structure Flattening
Transform complex directory trees into AI-digestible formats:
```bash
# Flatten only Python files for code review
vtree flatten --include "*.py" --format markdown

# Create comprehensive project overview
vtree flatten --format tree --max-depth 3
```

### AI Integration
Work smarter with AI assistants:
```bash
# Get implementation suggestions
vtree ask "How should I implement user authentication?"

# Analyze code quality
vtree ask --context full "What improvements can be made to the codebase?"
```

### Workflow Automation
Streamline repetitive tasks:
```bash
# Run predefined workflow
vtree workflow run deploy

# Create custom workflow
vtree workflow create my-workflow
```

### Plugin System
Extend functionality:
```bash
# List available plugins
vtree plugin list

# Install a plugin
vtree plugin install awesome-plugin
```

## ⚙️ Configuration

Velocitytree can be configured via:
- `.velocitytree.yaml` - Project configuration
- `~/.velocitytree/config.yaml` - Global configuration
- Environment variables (prefix: `VELOCITYTREE_`)

Example configuration:
```yaml
# .velocitytree.yaml
project:
  name: MyProject
  version: 1.0.0

flatten:
  default_output: context.md
  exclude_patterns:
    - "*.log"
    - "__pycache__"
    - ".git"

ai:
  default_model: gpt-4
  max_tokens: 4000
```

## 🔌 Plugin Development

Create custom plugins to extend Velocitytree:

```python
from velocitytree.plugin_system import Plugin

class MyPlugin(Plugin):
    """Custom plugin example."""
    
    @property
    def name(self):
        return "my_plugin"
    
    def activate(self):
        """Called when plugin is activated."""
        super().activate()
        # Your initialization code here
```

See our [Plugin Development Guide](docs/PLUGIN_DEVELOPMENT.md) for detailed instructions.

## 📚 Documentation

- [User Guide](docs/USER_GUIDE.md)
- [API Reference](docs/API.md)
- [Plugin Development](docs/PLUGIN_DEVELOPMENT.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:
- Code of Conduct
- Development setup
- Submitting pull requests
- Reporting issues

## 🌟 The Velocitytree Advantage

Velocitytree is the evolution of [TreeTamer](https://github.com/gbechtold/TreeTamer), adding:
- Advanced AI integration
- Workflow automation
- Plugin architecture
- Better performance
- Enhanced CLI experience

## 🛠️ Development

For development setup:

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run linters
flake8 velocitytree
black velocitytree
```

### Pre-commit Hooks

We use pre-commit hooks to maintain code quality:
```bash
pre-commit install
```

## 🐛 Troubleshooting

### Common Issues

**Issue: ModuleNotFoundError when running vtree**
```bash
# Solution: Ensure you're in the virtual environment
source venv/bin/activate  # Unix/Mac
# or
venv\Scripts\activate  # Windows
```

**Issue: Permission errors**
```bash
# Solution: Use virtual environment instead of system Python
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Getting Help

1. Check the [FAQ](docs/FAQ.md)
2. Search [existing issues](https://github.com/gbechtold/Velocitytree/issues)
3. Open a new issue with the bug report template

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built on the foundation of [TreeTamer](https://github.com/gbechtold/TreeTamer)
- Thanks to all our [contributors](https://github.com/gbechtold/Velocitytree/graphs/contributors)
- Inspired by the need for better AI-assisted development tools

## 🚧 Roadmap

- [ ] GUI interface
- [ ] Cloud synchronization
- [ ] Team collaboration features
- [ ] Additional AI model support
- [ ] Performance optimizations

---

**Made with ❤️ by the Velocitytree Team**

*Star ⭐ this repo if you find it useful!*