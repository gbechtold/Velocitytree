# Velocitytree 🌳⚡

[![PyPI version](https://badge.fury.io/py/velocitytree.svg)](https://badge.fury.io/py/velocitytree)
[![Python Versions](https://img.shields.io/pypi/pyversions/velocitytree.svg)](https://pypi.org/project/velocitytree/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/gbechtold/Velocitytree/workflows/Tests/badge.svg)](https://github.com/gbechtold/Velocitytree/actions)

Velocitytree is a powerful Python tool that streamlines developer workflows by intelligently managing project structure, context, and integrating AI assistance. It's the evolution of [TreeTamer](https://github.com/gbechtold/TreeTamer), bringing enhanced functionality and AI capabilities to project management.

## 🚀 Features

- **Project Structure Flattening**: Simplify complex directory hierarchies for easier navigation and management
- **Smart Context Management**: Automatically extract and maintain relevant project context
- **AI Integration**: Seamlessly integrate with AI assistants for enhanced code analysis and generation
- **Workflow Automation**: Streamline repetitive tasks and boost productivity
- **Extensible Plugin System**: Add custom functionality through a flexible plugin architecture
- **Rich CLI Interface**: Beautiful, intuitive command-line interface with progress indicators
- **Project Templates**: Quick project initialization with best practices
- **Configuration Management**: Flexible configuration through YAML, TOML, or environment variables

## 📦 Installation

### From PyPI

```bash
pip install velocitytree
```

### From Source (Recommended for Development)

> ⚠️ **Important**: Always use a virtual environment to avoid Python system conflicts

```bash
# Clone the repository
git clone https://github.com/gbechtold/Velocitytree.git
cd Velocitytree

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Optional: Install development dependencies
pip install -r requirements-dev.txt
```

### Automated Setup Script

For convenience, use our setup script:

```bash
# Unix/Mac
git clone https://github.com/gbechtold/Velocitytree.git
cd Velocitytree
./scripts/setup.sh        # Basic installation
./scripts/setup.sh --dev  # Include development dependencies

# Windows
git clone https://github.com/gbechtold/Velocitytree.git
cd Velocitytree
scripts\setup.bat        # Basic installation  
scripts\setup.bat --dev  # Include development dependencies
```

### One-Line Installation (Unix/Mac)

```bash
git clone https://github.com/gbechtold/Velocitytree.git && cd Velocitytree && python3 -m venv venv && source venv/bin/activate && pip install -e .
```

## 🏃 Quick Start

```bash
# Initialize a new project
vtree init

# Flatten project structure (like TreeTamer)
vtree flatten

# Generate project context for AI
vtree context

# Analyze project structure
vtree analyze

# Create a new workflow
vtree workflow create
```

## 🎯 Key Commands

### Project Management

```bash
# Initialize a new Velocitytree project
vtree init [--template <template-name>]

# Flatten directory structure
vtree flatten [--output <output-dir>] [--exclude <patterns>]

# Generate project context
vtree context [--format <json|yaml|markdown>] [--output <file>]
```

### AI Integration

```bash
# Analyze code with AI
vtree ai analyze <file>

# Generate code suggestions
vtree ai suggest <task>

# Create AI-ready context
vtree ai context
```

### Workflow Management

```bash
# List available workflows
vtree workflow list

# Create a new workflow
vtree workflow create <name>

# Run a workflow
vtree workflow run <name>
```

## ⚙️ Configuration

Create a `.velocitytree.yaml` file in your project root:

```yaml
project:
  name: MyAwesomeProject
  version: 1.0.0

flatten:
  exclude:
    - node_modules
    - .git
    - __pycache__
    - '*.pyc'
  include_extensions:
    - .py
    - .js
    - .md
    - .yaml
    - .json

ai:
  provider: openai
  model: gpt-4
  api_key: ${OPENAI_API_KEY}

workflows:
  daily_standup:
    - command: git status
    - command: vtree analyze --changes
    - command: vtree ai suggest --context today
```

## 🔌 Plugin System

Create custom plugins to extend Velocitytree:

```python
# plugins/my_plugin.py
from velocitytree.plugins import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"
    version = "1.0.0"
    
    def register_commands(self, cli):
        @cli.command()
        def my_command():
            """My custom command"""
            self.logger.info("Running my custom command")
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📚 Documentation

Full documentation is available at [https://velocitytree.readthedocs.io](https://velocitytree.readthedocs.io)

## 🙏 Acknowledgments

- Based on [TreeTamer](https://github.com/gbechtold/TreeTamer) by Guntram Bechtold
- Inspired by modern developer workflow tools
- Built with love for the developer community

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Bug Reports & Feature Requests

Please use the [GitHub Issues](https://github.com/gbechtold/Velocitytree/issues) page to report bugs or request features.

## 📧 Contact

Guntram Bechtold - [@gbechtold](https://github.com/gbechtold)

Project Link: [https://github.com/gbechtold/Velocitytree](https://github.com/gbechtold/Velocitytree)

---

⭐ If you find Velocitytree helpful, please consider giving it a star on GitHub! ⭐