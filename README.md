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
- **Code drift** from original specifications and architecture?
- **Monitoring project health** and catching issues early?
- **Predicting project completion** accurately?

**Velocitytree is your solution!** 🚀

## ✨ What's New in v2.0

- 🔍 **Continuous Monitoring**: Background process that monitors code quality, performance, and drift
- 🎯 **Drift Detection**: Automatically detect when code drifts from specifications
- 🚨 **Smart Alerts**: Multi-channel alert system with rate limiting and suppression
- 🔧 **Realignment Suggestions**: AI-powered suggestions to fix detected issues
- 📈 **Predictive Analytics**: ML-based completion estimates with confidence intervals
- 🤖 **Claude Integration**: Native support for Anthropic's Claude AI
- 🧠 **Smart Documentation**: Context-aware documentation generation with quality checks
- ⚡ **Real-time Suggestions**: Get code improvements as you work
- 🔄 **Workflow Memory**: Learn from past decisions and avoid conflicts

## 🚀 Quick Start

```bash
# Clone and setup with virtual environment
git clone https://github.com/gbechtold/Velocitytree.git
cd Velocitytree
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

### Initialize your project
```bash
vtree init
```

### Start continuous monitoring
```bash
vtree monitor background start
```

### Check for drift
```bash
vtree monitor drift check
```

## 💡 Core Features

### 🔍 Continuous Monitoring & Evaluation

Monitor your project health in real-time:
```bash
# Start background monitoring
vtree monitor background start

# Check monitoring status
vtree monitor background status

# View recent issues
vtree monitor issues

# Configure monitoring
vtree monitor config --enable code --enable performance --interval 300
```

### 🎯 Drift Detection

Detect when your code drifts from specifications:
```bash
# Check for drift
vtree monitor drift check

# Generate detailed drift report
vtree monitor drift report

# View loaded specifications
vtree monitor drift specs
```

### 🚨 Intelligent Alert System

Get notified about critical issues:
```bash
# View recent alerts
vtree monitor alerts list

# Test alert system
vtree monitor alerts test --severity warning

# Configure alert channels
vtree monitor alert-config --channel email --channel webhook
```

### 🔧 Realignment Suggestions

Get AI-powered suggestions to fix issues:
```bash
# Generate suggestions based on drift
vtree monitor realign suggest

# Apply automated fixes
vtree monitor realign apply --suggestion-id <id>

# Export suggestions
vtree monitor realign export --output suggestions.json
```

### 📈 Predictive Analytics

Get ML-based completion estimates:
```bash
# Predict project completion
vtree progress predict

# Predict feature completion with risks
vtree progress predict --feature user-auth --risks --confidence

# Monitor velocity trends
vtree progress velocity

# Generate burndown chart
vtree progress burndown
```

### 🤖 Claude AI Integration

Native support for Anthropic's Claude:
```bash
# Configure Claude
export CLAUDE_API_KEY=your-key

# Use Claude for analysis
vtree ai analyze --model claude-3

# Get Claude suggestions
vtree analyze --suggestions --model claude
```

### 📘 Smart Documentation

Generate intelligent documentation:
```bash
# Generate comprehensive docs
vtree doc generate --smart

# Incremental documentation updates
vtree doc update --incremental

# Check documentation quality
vtree doc quality --report
```

### ⚡ Real-time Suggestions

Get code improvements as you work:
```bash
# Start interactive analysis
vtree analyze --interactive

# Get refactoring recommendations
vtree suggestions refactor --file src/main.py

# Get performance optimizations
vtree suggestions performance
```

### 🌟 Feature Tree Visualization

Visualize project structure and dependencies:
```bash
# Start visual interface
vtree visualize --web

# Generate static visualization
vtree visualize export --format png --layout spring

# Show feature dependencies
vtree visualize deps --feature user-auth
```

### 🔄 Natural Language Git Workflow

Manage git with natural language:
```bash
# Create feature branch
vtree git feature "Add user authentication"

# Smart commit messages
vtree git commit

# Analyze changes
vtree git analyze
```

### 🗣️ Conversational Planning

Plan projects through dialogue:
```bash
# Start planning session
vtree plan start

# Resume session
vtree plan resume <session-id>

# Export plan
vtree plan export <session-id>
```

### 🔌 Advanced Plugin System

Extend functionality with plugins:
```bash
# List plugins
vtree plugin list

# Install plugin
vtree plugin install monitoring-extension

# Create custom plugin
vtree plugin create my-plugin
```

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- Git
- Virtual environment (recommended)

### Standard Installation
```bash
pip install velocitytree
```

### Development Installation
```bash
git clone https://github.com/gbechtold/Velocitytree.git
cd Velocitytree
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Required Dependencies
The following will be installed automatically:
- Flask & flask-cors (web interface)
- scikit-learn (predictive analytics)
- psutil (system monitoring)
- GitPython (git integration)
- Rich (beautiful CLI)
- Click (command framework)
- And more...

## ⚙️ Configuration

### Global Configuration
```yaml
# ~/.velocitytree/config.yaml
monitoring:
  check_interval: 300
  enable_drift_detection: true
  alert_channels:
    - log
    - email
  
ai:
  default_model: claude-3
  max_tokens: 4000
  
documentation:
  quality_threshold: 0.8
  incremental_updates: true
```

### Project Configuration
```yaml
# .velocitytree.yaml
project:
  name: MyProject
  version: 2.0.0
  
monitoring:
  enabled: true
  specs:
    - openapi.yaml
    - ARCHITECTURE.md
  
alerts:
  email:
    smtp_host: smtp.gmail.com
    to_emails:
      - team@example.com
```

## 🛠️ Development

### Running Tests
```bash
# Run all tests
pytest

# Run specific test category
pytest tests/test_monitoring.py

# Run with coverage
pytest --cov=velocitytree
```

### Code Quality
```bash
# Run linters
flake8 velocitytree
black velocitytree
mypy velocitytree

# Install pre-commit hooks
pre-commit install
```

## 🐛 Troubleshooting

### Common Issues

**ModuleNotFoundError: No module named 'flask'**
```bash
pip install flask flask-cors
```

**ImportError in monitoring module**
```bash
pip install psutil scikit-learn sqlalchemy
```

**Permission errors**
```bash
# Always use virtual environment
source venv/bin/activate
```

### Getting Help
1. Check [documentation](docs/)
2. Search [issues](https://github.com/gbechtold/Velocitytree/issues)
3. Join our [Discord](https://discord.gg/velocitytree)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md).

### Areas for Contribution
- Additional monitoring metrics
- New alert channels
- Improved ML models
- More language adapters
- Documentation improvements
- Bug fixes

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🚧 Roadmap

### Version 2.1 (Q2 2024)
- [ ] Cloud monitoring dashboard
- [ ] Team collaboration features
- [ ] Mobile app for alerts
- [ ] More AI model integrations

### Version 2.2 (Q3 2024)
- [ ] Distributed monitoring
- [ ] Custom ML model training
- [ ] Advanced security scanning
- [ ] Performance profiling

## 🙏 Acknowledgments

- Built on the foundation of [TreeTamer](https://github.com/gbechtold/TreeTamer)
- Inspired by modern DevOps practices
- Thanks to all [contributors](https://github.com/gbechtold/Velocitytree/graphs/contributors)

---

**Made with ❤️ by the Velocitytree Team**

*Star ⭐ this repo if you find it useful!*