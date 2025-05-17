# Velocitytree Example Plugins

This directory contains example plugins that demonstrate the plugin system capabilities.

## Available Plugins

### 1. JSON Formatter Plugin

**Location**: `velocitytree/plugins/json_formatter/`

The JSON formatter plugin provides functionality to format JSON output files with pretty printing.

**Features**:
- Automatically formats JSON files after flattening
- Configurable indentation and key sorting
- CLI command for formatting existing JSON files

**Configuration**:
```yaml
indent: 2        # Indentation level
sort_keys: true  # Sort object keys alphabetically
```

**CLI Commands**:
```bash
velocitytree plugin format-json input.json --indent 4 --sort-keys
```

### 2. Output Validator Plugin

**Location**: `velocitytree/plugins/output_validator/`

The output validator plugin validates generated files against configurable rules.

**Features**:
- File size validation
- File extension filtering
- UTF-8 encoding verification
- Optional syntax validation for JSON and Python files
- Detailed error reporting

**Configuration**:
```yaml
max_file_size_mb: 10
allowed_extensions:
  - .py
  - .js
  - .json
  - .md
encoding_check: true
validate_syntax: false
```

**Validation Rules**:
- Checks file size limits
- Validates file extensions
- Ensures UTF-8 encoding
- Optionally validates syntax

### 3. Custom Commands Plugin

**Location**: `velocitytree/plugins/custom_commands/`

The custom commands plugin adds useful development commands to the CLI.

**Features**:
- Project statistics command
- Clean command for removing generated files
- Backup command for project archival

**Commands**:

#### Stats Command
Shows project statistics including file counts and line counts by file type.
```bash
velocitytree plugin stats
```

#### Clean Command
Removes generated files and caches.
```bash
velocitytree plugin clean --dry-run  # Preview what will be deleted
velocitytree plugin clean --force    # Delete without confirmation
```

#### Backup Command
Creates a compressed backup of the project.
```bash
velocitytree plugin backup --output backup.tar.gz
velocitytree plugin backup --exclude "*.log" --exclude "temp/*"
```

## Plugin Development

These example plugins demonstrate key plugin development patterns:

1. **Hook Registration**: How to register hooks for system events
2. **Command Registration**: How to add CLI commands
3. **Configuration**: How to handle plugin configuration
4. **Logging**: How to use the plugin logger
5. **Error Handling**: How to handle and report errors

To create your own plugin, use these examples as templates and refer to the [Plugin Development Guide](docs/plugin_development.md).

## Testing

Each plugin includes comprehensive tests in the `tests/test_example_plugins.py` file. Run tests with:

```bash
pytest tests/test_example_plugins.py
```

## Installation

These plugins are automatically discovered when Velocitytree starts. To disable a plugin, you can:

1. Remove or rename its directory
2. Disable it via configuration
3. Use the plugin management commands

## Contributing

Feel free to submit improvements to these example plugins or contribute new examples that demonstrate additional plugin capabilities.