# Velocitytree Architecture

## Overview

Velocitytree is built with a modular architecture that emphasizes extensibility, maintainability, and ease of use. The system consists of several key components:

## Core Architecture

```
velocitytree/
├── core.py          # Core flattening and context management
├── cli.py           # Command-line interface
├── ai.py            # AI integration layer
├── workflows.py     # Workflow automation
├── plugin_system.py # Plugin architecture
├── config.py        # Configuration management
├── utils.py         # Utility functions
└── plugins/         # Built-in plugins
```

## Key Components

### 1. Core Module (`core.py`)
The heart of Velocitytree, responsible for:
- **TreeFlattener**: Converts directory structures into various formats
- **ContextManager**: Manages project context for AI interactions
- **FileProcessor**: Handles file reading and processing

### 2. CLI Module (`cli.py`)
Provides the command-line interface using Click framework:
- Command routing and parsing
- User interaction and prompts
- Progress indication and output formatting

### 3. AI Module (`ai.py`)
Manages AI integrations:
- **AIAssistant**: Abstract base class for AI providers
- **OpenAIAssistant**: OpenAI/ChatGPT integration
- **AnthropicAssistant**: Claude integration
- Context preparation and token management

### 4. Workflow Module (`workflows.py`)
Enables automation and task orchestration:
- **Workflow**: Defines step sequences
- **WorkflowExecutor**: Executes workflows with error handling
- **WorkflowManager**: Manages workflow lifecycle

### 5. Plugin System (`plugin_system.py`)
Provides extensibility through plugins:
- **Plugin**: Base class for all plugins
- **PluginManager**: Discovers, loads, and manages plugins
- **HookManager**: Manages plugin hooks and events

## Design Patterns

### 1. Plugin Architecture
- Uses abstract base classes for extensibility
- Hook-based event system for plugin integration
- Dynamic plugin discovery and loading

### 2. Configuration Management
- Hierarchical configuration (project → user → global)
- Environment variable support
- Multiple format support (YAML, TOML, JSON)

### 3. Command Pattern
- CLI commands encapsulate actions
- Workflows compose complex operations
- Plugins can register custom commands

## Data Flow

1. **User Input** → CLI parses command
2. **Configuration** → Loaded and merged
3. **Core Processing** → Execute requested operation
4. **Plugin Hooks** → Triggered at key points
5. **Output** → Formatted and displayed

## Extension Points

### Plugin Hooks
- `startup`: Application start
- `before_command`: Before command execution
- `after_command`: After command execution
- `before_flatten`: Before flattening operation
- `after_flatten`: After flattening operation
- `error`: Error handling

### Custom Commands
Plugins can register new CLI commands:
```python
@click.command()
def my_command():
    """My custom command."""
    pass

plugin.register_command(my_command)
```

### Workflow Steps
Custom workflow steps can be added:
```python
class CustomStep(WorkflowStep):
    def execute(self, context):
        # Custom logic here
        pass
```

## Security Considerations

1. **API Key Management**
   - Keys stored in environment variables
   - Never committed to repository
   - Encrypted storage recommended

2. **File Access**
   - Respects .gitignore patterns
   - Configurable exclusion patterns
   - Size limits for processing

3. **Plugin Security**
   - Plugins run with full permissions
   - Only install trusted plugins
   - Plugin sandboxing planned

## Performance Optimization

1. **Lazy Loading**
   - Plugins loaded on demand
   - Large files streamed, not loaded entirely

2. **Caching**
   - AI responses cached
   - File metadata cached
   - Configuration cached

3. **Async Operations**
   - AI calls are asynchronous
   - File operations optimized
   - Parallel workflow execution

## Future Architecture Plans

1. **GUI Support**
   - Separate GUI process
   - REST API for communication
   - Real-time updates via WebSocket

2. **Cloud Integration**
   - Cloud storage backends
   - Distributed workflow execution
   - Team collaboration features

3. **Performance Improvements**
   - Rust extensions for core operations
   - Better caching strategies
   - Incremental processing