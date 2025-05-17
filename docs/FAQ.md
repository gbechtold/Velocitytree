# Frequently Asked Questions (FAQ)

## Installation Issues

### Q: I get "ModuleNotFoundError" when running vtree
**A:** This usually means you need to activate your virtual environment:
```bash
source venv/bin/activate  # Unix/Mac
# or
venv\Scripts\activate  # Windows
```

### Q: Installation fails with permission errors
**A:** Never install with sudo. Use a virtual environment instead:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Q: Missing dependencies after installation
**A:** Make sure to install from source with all dependencies:
```bash
git clone https://github.com/gbechtold/Velocitytree.git
cd Velocitytree
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## Usage Questions

### Q: How do I flatten only specific file types?
**A:** Use the `--include` option:
```bash
vtree flatten --include "*.py" --include "*.js"
```

### Q: How do I exclude certain directories?
**A:** Use the `--exclude` option or add patterns to `.velocitytree.yaml`:
```bash
vtree flatten --exclude "**/node_modules" --exclude "**/.git"
```

### Q: Can I use multiple AI providers?
**A:** Yes! Configure both in your environment:
```bash
export OPENAI_API_KEY=your_openai_key
export ANTHROPIC_API_KEY=your_anthropic_key
```
Then specify the provider:
```bash
vtree ask --provider openai "Your question"
vtree ask --provider anthropic "Your question"
```

## Configuration

### Q: Where should I put my configuration?
**A:** Velocitytree looks for configuration in this order:
1. `.velocitytree.yaml` in your project directory
2. `~/.velocitytree/config.yaml` (user config)
3. Environment variables (prefix: `VELOCITYTREE_`)

### Q: How do I set API keys securely?
**A:** Use environment variables or a `.env` file (never commit this!):
```bash
# .env file
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Plugin Development

### Q: How do I create a custom plugin?
**A:** See our [Plugin Development Guide](PLUGIN_DEVELOPMENT.md). Basic example:
```python
from velocitytree.plugin_system import Plugin

class MyPlugin(Plugin):
    @property
    def name(self):
        return "my_plugin"
    
    def activate(self):
        super().activate()
        # Your code here
```

### Q: Where do I put custom plugins?
**A:** In any of these locations:
- `~/.velocitytree/plugins/`
- `./plugins/` in your project
- Any directory in `VELOCITYTREE_PLUGIN_PATH`

## Workflows

### Q: How do I create a custom workflow?
**A:** Use the workflow create command:
```bash
vtree workflow create my-workflow
```
Or define in `.velocitytree.yaml`:
```yaml
workflows:
  custom_commands:
    - name: "deploy"
      steps:
        - command: "pytest"
        - command: "git push"
```

### Q: Can workflows use variables?
**A:** Yes! Use the `${variable}` syntax:
```yaml
steps:
  - command: "echo ${message}"
    variables:
      message: "Hello, World!"
```

## Troubleshooting

### Q: Velocitytree is running slowly
**A:** Try:
1. Excluding large directories (node_modules, .git)
2. Using specific include patterns
3. Reducing max tree depth
4. Clearing the cache

### Q: AI responses are cut off
**A:** Adjust the max_tokens setting:
```yaml
ai:
  max_tokens: 8000  # Increase token limit
```

### Q: Plugins aren't loading
**A:** Check:
1. Plugin is in the correct directory
2. Plugin is enabled in config
3. No syntax errors in plugin code
4. Virtual environment is activated

## Best Practices

### Q: What's the best way to structure a Velocitytree project?
**A:** 
```
project/
├── .velocitytree.yaml    # Project config
├── .velocitytree/        # Project-specific data
│   ├── workflows/        # Custom workflows
│   └── templates/        # Custom templates
├── plugins/              # Custom plugins
└── your_code/           # Your actual project
```

### Q: Should I commit .velocitytree.yaml?
**A:** Yes, but never commit:
- API keys
- `.env` files
- Personal configuration
- Cache directories

## Advanced Usage

### Q: Can I use Velocitytree in CI/CD?
**A:** Yes! Example GitHub Action:
```yaml
- name: Install Velocitytree
  run: |
    pip install velocitytree
    vtree flatten --output context.md
    vtree workflow run ci-checks
```

### Q: How do I integrate with my IDE?
**A:** Several options:
1. Use the CLI directly from terminal
2. Create IDE tasks/commands
3. Use shell integration
4. Wait for upcoming IDE plugins