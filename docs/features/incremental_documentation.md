# Incremental Documentation Updates

VelocityTree's incremental documentation system monitors file changes and updates documentation efficiently, without regenerating everything from scratch.

## Overview

The incremental documentation updater provides:

- Real-time file monitoring
- Efficient change detection
- Smart incremental updates
- Documentation caching
- Automatic regeneration when needed

## Usage

### Watch Files for Changes

Monitor files and update documentation automatically:

```bash
# Watch specific files
vtree doc watch src/*.py

# Watch with custom patterns
vtree doc watch "src/**/*.py" "tests/**/*.py"

# Specify format and style
vtree doc watch src/*.py --format markdown --style google

# Custom check interval
vtree doc watch src/*.py --interval 2.0
```

### Cache Management

Control the documentation cache:

```bash
# Invalidate specific files
vtree doc invalidate-cache src/main.py src/utils.py

# Clear entire cache
vtree doc invalidate-cache --all
```

## How It Works

### Change Detection

The system tracks file changes using:

1. **File Hashing**: SHA-256 hashes detect content changes
2. **AST Analysis**: Parses code to identify specific changes
3. **Diff Comparison**: Finds exact lines that changed

### Incremental Updates

When changes are detected:

1. **Analyze Scope**: Determine what elements changed
2. **Check Incrementability**: Decide if incremental update is possible
3. **Update or Regenerate**: Apply minimal changes or regenerate fully

### Caching Strategy

Documentation is cached with:

- File content hashes
- Generated documentation
- Timestamps and metadata
- Quality scores

## Configuration

Configure incremental updates in `config.yaml`:

```yaml
documentation:
  incremental:
    enabled: true
    cache_dir: ~/.velocitytree/doc_cache
    watch_interval: 1.0
    max_cache_size: 100MB
```

## Use Cases

### Continuous Documentation

Keep documentation always up-to-date during development:

```bash
# Run in background while coding
vtree doc watch src/**/*.py &

# Check documentation quality continuously
vtree doc check src/ --recursive --watch
```

### CI/CD Integration

Use in continuous integration pipelines:

```bash
# Generate documentation if changed
vtree doc generate src/ --incremental

# Fail build if documentation quality drops
vtree doc check src/ --min-quality 80
```

### Large Projects

Efficient for large codebases:

```bash
# Watch only changed modules
vtree doc watch modules/**/api.py

# Invalidate stale documentation
vtree doc invalidate-cache --older-than 7d
```

## Best Practices

1. **Regular Cache Cleanup**: Invalidate cache periodically
2. **Selective Watching**: Monitor only relevant files
3. **Quality Thresholds**: Set minimum quality scores
4. **Incremental in CI**: Use for faster builds

## Performance Considerations

- **Memory Usage**: Cache grows with project size
- **CPU Usage**: Minimal during monitoring, spikes during updates
- **Disk I/O**: Reduced by caching, increased during initial scan

## Troubleshooting

### Common Issues

1. **Stale Documentation**
   ```bash
   vtree doc invalidate-cache --all
   ```

2. **High Memory Usage**
   ```bash
   # Limit cache size
   vtree config set documentation.cache_max_size 50MB
   ```

3. **Slow Updates**
   ```bash
   # Increase check interval
   vtree doc watch src/*.py --interval 5.0
   ```

## Example Workflow

Complete documentation workflow with incremental updates:

```bash
# 1. Generate initial documentation
vtree doc generate src/ --output docs/api/

# 2. Start watching for changes
vtree doc watch src/**/*.py --format markdown

# 3. Make code changes
# ... documentation updates automatically ...

# 4. Check quality before commit
vtree doc check src/ --recursive

# 5. Invalidate changed files before push
vtree doc invalidate-cache $(git diff --name-only)
```

## API Reference

### Python API

```python
from velocitytree.documentation import IncrementalDocUpdater

# Create updater
updater = IncrementalDocUpdater(config)

# Detect changes
changes = updater.detect_changes(['src/main.py'])

# Update documentation
results = updater.update_documentation(changes)

# Watch files
updater.watch_files(['src/**/*.py'], callback=my_callback)

# Cache management
updater.invalidate_cache(['src/old_file.py'])
```

### Change Detection

```python
# Custom change handler
def handle_changes(results, change_set):
    for change in change_set.doc_changes:
        print(f"{change.element}: {change.change_type}")
        
updater.watch_files(patterns, callback=handle_changes)
```