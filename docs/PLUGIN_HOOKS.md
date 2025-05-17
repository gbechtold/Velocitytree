# Plugin Lifecycle Hooks

This guide covers the lifecycle hooks available in the Velocitytree plugin system.

## Hook System Overview

Velocitytree provides a comprehensive hook system that allows plugins to:
- React to system events
- Modify behavior at key points
- Add custom functionality
- Integrate with core operations

### Hook Registration

```python
def register_hooks(self, hook_manager):
    """Register hooks for this plugin."""
    hook_manager.register_hook(event_name, callback, priority=50)
```

### Priority System

Hooks are executed in priority order (0-100):
- Lower numbers execute first
- Default priority is 50
- Use priority to control execution order

## Available Lifecycle Hooks

### Core System Hooks

#### velocitytree_startup
Triggered when Velocitytree starts.
- **Args**: `config` - The configuration object
- **Returns**: None
- **Usage**: Initialize resources, set up connections

```python
def on_startup(config):
    self.logger.info("Velocitytree starting up")
    # Initialize resources

hook_manager.register_hook('velocitytree_startup', on_startup)
```

#### velocitytree_shutdown
Triggered when Velocitytree shuts down.
- **Args**: None
- **Returns**: None
- **Usage**: Clean up resources, save state

### Plugin Lifecycle Hooks

#### plugin_loaded
Triggered when a plugin is loaded.
- **Args**: `plugin_name`, `plugin_instance`
- **Returns**: None

#### plugin_activated
Triggered when a plugin is activated.
- **Args**: `plugin_name`
- **Returns**: None

#### plugin_deactivated
Triggered when a plugin is deactivated.
- **Args**: `plugin_name`
- **Returns**: None

#### plugin_error
Triggered when a plugin encounters an error.
- **Args**: `plugin_name`, `error`, `traceback`
- **Returns**: None

### Command Lifecycle Hooks

#### before_command
Triggered before a CLI command executes.
- **Args**: `command_name`, `context`, `args`, `kwargs`
- **Returns**: Modified args/kwargs or None to continue, False to cancel
- **Note**: Returning False stops command execution

```python
def before_command(command_name, context, args, kwargs):
    if command_name == 'dangerous_command':
        return False  # Cancel execution
    # Modify args
    modified_args = list(args)
    modified_args.append('--safe-mode')
    return modified_args, kwargs
```

#### after_command
Triggered after a CLI command executes.
- **Args**: `command_name`, `result`, `context`
- **Returns**: Modified result or None

#### command_error
Triggered when a command encounters an error.
- **Args**: `command_name`, `error`, `context`
- **Returns**: None

### Workflow Lifecycle Hooks

#### workflow_start
Triggered when a workflow starts.
- **Args**: `workflow_name`, `context`
- **Returns**: None

#### workflow_step_start
Triggered before a workflow step executes.
- **Args**: `workflow_name`, `step_name`, `context`
- **Returns**: None

#### workflow_step_complete
Triggered after a workflow step executes.
- **Args**: `workflow_name`, `step_name`, `result`, `context`
- **Returns**: None

#### workflow_complete
Triggered when a workflow completes.
- **Args**: `workflow_name`, `result`, `context`
- **Returns**: None

#### workflow_error
Triggered when a workflow encounters an error.
- **Args**: `workflow_name`, `error`, `context`
- **Returns**: None

### File Operation Hooks

#### init_complete
Triggered after project initialization.
- **Args**: `project_path`, `config`
- **Returns**: None

#### flatten_start
Triggered before flattening operation.
- **Args**: `source_path`, `options`
- **Returns**: Modified options dict or None
- **Note**: Can modify flatten operation options

```python
def on_flatten_start(source_path, options):
    # Add custom excludes
    options['exclude_patterns'].append('*.secret')
    return options
```

#### flatten_complete
Triggered after flattening operation.
- **Args**: `result`, `source_path`
- **Returns**: None

#### context_generate
Triggered when generating context.
- **Args**: `project_path`, `options`
- **Returns**: Additional context data or None

### AI Integration Hooks

#### ai_request
Triggered before an AI request.
- **Args**: `prompt`, `context`, `model`
- **Returns**: Modified prompt or None
- **Note**: Can modify or enhance prompts

#### ai_response
Triggered after an AI response.
- **Args**: `response`, `prompt`, `model`
- **Returns**: Modified response or None
- **Note**: Can process or filter AI responses

## Hook Chaining

For certain hooks, you can use the hook chain mechanism:

```python
def modifier_hook(value, *args):
    # Modify and return the value
    return value + " modified"

hook_manager.register_hook('chainable_event', modifier_hook)
result = hook_manager.trigger_hook_chain('chainable_event', initial_value)
```

## Error Handling

Hooks should handle their own errors gracefully:

```python
def safe_hook(*args, **kwargs):
    try:
        # Hook logic
        do_something()
    except Exception as e:
        self.logger.error(f"Hook error: {e}")
        # Don't re-raise to avoid breaking other hooks
```

## Best Practices

1. **Use appropriate priorities**: Lower numbers run first
2. **Handle errors gracefully**: Don't let exceptions break the system
3. **Be efficient**: Hooks run synchronously, avoid blocking operations
4. **Document your hooks**: Explain what they do and why
5. **Test hook interactions**: Ensure your hooks work with others
6. **Clean up resources**: Use shutdown hooks for cleanup
7. **Respect cancellation**: Check return values for command hooks

## Example Plugin with Hooks

```python
from velocitytree.plugins import Plugin

class MonitoringPlugin(Plugin):
    name = "monitoring"
    version = "1.0.0"
    
    def register_hooks(self, hook_manager):
        # System monitoring
        hook_manager.register_hook('velocitytree_startup', self.on_startup, priority=20)
        hook_manager.register_hook('velocitytree_shutdown', self.on_shutdown, priority=80)
        
        # Command tracking
        hook_manager.register_hook('before_command', self.track_command, priority=30)
        hook_manager.register_hook('command_error', self.log_error, priority=50)
        
        # Workflow monitoring
        hook_manager.register_hook('workflow_start', self.start_timing)
        hook_manager.register_hook('workflow_complete', self.report_timing)
    
    def on_startup(self, config):
        self.start_time = datetime.now()
        self.command_count = 0
        self.logger.info("Monitoring started")
    
    def on_shutdown(self):
        runtime = datetime.now() - self.start_time
        self.logger.info(f"Session stats: {self.command_count} commands, runtime: {runtime}")
    
    def track_command(self, command_name, context, args, kwargs):
        self.command_count += 1
        self.logger.debug(f"Executing command: {command_name}")
        return None  # Don't modify args
    
    def log_error(self, command_name, error, context):
        self.logger.error(f"Command '{command_name}' failed: {error}")
    
    def start_timing(self, workflow_name, context):
        context.set_global_var(f'{workflow_name}_start_time', datetime.now())
    
    def report_timing(self, workflow_name, result, context):
        start_time = context.get_global_var(f'{workflow_name}_start_time')
        if start_time:
            duration = datetime.now() - start_time
            self.logger.info(f"Workflow '{workflow_name}' took {duration.total_seconds()}s")
```