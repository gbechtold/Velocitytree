# Plugin Lifecycle Hooks

Velocitytree's plugin system provides comprehensive lifecycle hooks that allow plugins to integrate deeply with the core system and extend functionality at key points in the application lifecycle.

## Overview

Lifecycle hooks are events that are triggered at specific points during Velocitytree's execution. Plugins can register callbacks for these hooks to:

- Modify behavior
- Add custom functionality
- Monitor system events
- Integrate with external systems

## Hook Categories

### Core System Hooks

| Hook Name | Description | Arguments | Return Value |
|-----------|-------------|-----------|--------------|
| `velocitytree_startup` | Triggered when Velocitytree starts | `config` | None |
| `velocitytree_shutdown` | Triggered when Velocitytree shuts down | None | None |

### Plugin Lifecycle Hooks

| Hook Name | Description | Arguments | Return Value |
|-----------|-------------|-----------|--------------|
| `plugin_loaded` | Triggered when a plugin is loaded | `plugin_name`, `plugin_instance` | None |
| `plugin_activated` | Triggered when a plugin is activated | `plugin_name` | None |
| `plugin_deactivated` | Triggered when a plugin is deactivated | `plugin_name` | None |

### Command Lifecycle Hooks

| Hook Name | Description | Arguments | Return Value |
|-----------|-------------|-----------|--------------|
| `before_command` | Triggered before a CLI command is executed | `command_name`, `args`, `kwargs` | `modified_args` |
| `after_command` | Triggered after a CLI command is executed | `command_name`, `result` | `modified_result` |

### Workflow Lifecycle Hooks

| Hook Name | Description | Arguments | Return Value |
|-----------|-------------|-----------|--------------|
| `workflow_start` | Triggered when a workflow starts | `workflow_name`, `context` | None |
| `workflow_step` | Triggered before each workflow step | `workflow_name`, `step_name`, `context` | `skip_step` |
| `workflow_complete` | Triggered when a workflow completes | `workflow_name`, `result`, `context` | None |
| `workflow_error` | Triggered when a workflow encounters an error | `workflow_name`, `error`, `context` | None |

### File Operation Hooks

| Hook Name | Description | Arguments | Return Value |
|-----------|-------------|-----------|--------------|
| `before_flatten` | Triggered before flattening operation | `directory`, `options` | `modified_options` |
| `after_flatten` | Triggered after flattening operation | `result` | None |
| `before_context_generation` | Triggered before context generation | `files`, `options` | `modified_options` |
| `after_context_generation` | Triggered after context generation | `context` | `modified_context` |

### Monitoring & Analysis Hooks

| Hook Name | Description | Arguments | Return Value |
|-----------|-------------|-----------|--------------|
| `drift_detected` | Triggered when code drift is detected | `drift_info`, `project_path` | None |
| `alert_created` | Triggered when an alert is created | `alert_data`, `channel` | None |
| `analysis_complete` | Triggered when code analysis completes | `analysis_results`, `project_path` | None |

### AI Integration Hooks

| Hook Name | Description | Arguments | Return Value |
|-----------|-------------|-----------|--------------|
| `before_ai_request` | Triggered before AI request | `prompt`, `context`, `system_prompt` | `modified_prompt` |
| `after_ai_response` | Triggered after AI response | `response`, `prompt` | `modified_response` |
| `ai_suggestion_generated` | Triggered when AI generates a suggestion | `suggestion`, `context` | None |

## Using Hooks in Your Plugin

### Basic Hook Registration

```python
from velocitytree.plugin_system import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"
    version = "1.0.0"
    
    def register_hooks(self, hook_manager):
        # Register a simple hook
        hook_manager.register_hook('workflow_start', self.on_workflow_start)
        
        # Register with priority (lower numbers run first)
        hook_manager.register_hook('before_command', self.modify_command, priority=10)
    
    def on_workflow_start(self, workflow_name, context):
        self.logger.info(f"Workflow {workflow_name} started")
    
    def modify_command(self, command_name, args, kwargs):
        # Modify command arguments
        if command_name == 'flatten':
            kwargs['verbose'] = True
        return args, kwargs
```

### Hook Priority

Hooks can be registered with a priority value (0-100). Lower numbers execute first:

```python
# This hook runs first
hook_manager.register_hook('before_command', high_priority_hook, priority=10)

# This hook runs second
hook_manager.register_hook('before_command', normal_priority_hook, priority=50)

# This hook runs last
hook_manager.register_hook('before_command', low_priority_hook, priority=90)
```

### Error Handling

Hooks are executed with error isolation - if one hook fails, others will still run:

```python
def safe_hook(self, *args):
    try:
        # Your hook logic here
        return self.process_data(*args)
    except Exception as e:
        self.logger.error(f"Hook failed: {e}")
        # Return None or appropriate default
        return None
```

### Return Values

Some hooks can modify data by returning values:

```python
def before_ai_request(self, prompt, context, system_prompt):
    # Add context to the prompt
    enhanced_prompt = f"{prompt}\n\nContext: {context.get('summary', '')}"
    return enhanced_prompt
```

## Advanced Hook Patterns

### Conditional Hook Execution

```python
def workflow_step(self, workflow_name, step_name, context):
    # Skip step based on condition
    if context.get('skip_tests') and 'test' in step_name:
        return True  # Skip this step
    return False  # Continue normally
```

### Stateful Hooks

```python
class StatefulPlugin(Plugin):
    def __init__(self, config):
        super().__init__(config)
        self.workflow_timings = {}
    
    def on_workflow_start(self, workflow_name, context):
        self.workflow_timings[workflow_name] = time.time()
    
    def on_workflow_complete(self, workflow_name, result, context):
        if workflow_name in self.workflow_timings:
            duration = time.time() - self.workflow_timings[workflow_name]
            self.logger.info(f"Workflow {workflow_name} took {duration:.2f}s")
```

### Aggregating Hook Results

Multiple plugins can register for the same hook. Results are aggregated:

```python
# Plugin A
def before_ai_request(self, prompt, context, system_prompt):
    return f"[Plugin A] {prompt}"

# Plugin B
def before_ai_request(self, prompt, context, system_prompt):
    return f"[Plugin B] {prompt}"

# Result: Both modifications are applied in priority order
```

## CLI Commands for Hook Management

List all registered hooks:
```bash
vtree plugin hooks list
```

Debug hook execution:
```bash
vtree plugin hooks debug --event workflow_start
```

## Best Practices

1. **Use appropriate priorities**: Default is 50, use 10-30 for early hooks, 70-90 for late hooks
2. **Handle errors gracefully**: Don't let your hook crash the entire system
3. **Keep hooks lightweight**: Heavy processing can slow down the system
4. **Document hook behavior**: Clearly document what your hooks do
5. **Test hook interactions**: Test your plugin with other plugins enabled
6. **Use return values wisely**: Only modify data when necessary

## Example: Monitoring Plugin

```python
class MonitoringPlugin(Plugin):
    name = "monitoring"
    version = "1.0.0"
    
    def __init__(self, config):
        super().__init__(config)
        self.metrics = {}
    
    def register_hooks(self, hook_manager):
        # Monitor all major events
        hook_manager.register_hook('workflow_start', self.track_workflow_start)
        hook_manager.register_hook('workflow_complete', self.track_workflow_complete)
        hook_manager.register_hook('drift_detected', self.alert_on_drift)
        hook_manager.register_hook('analysis_complete', self.record_analysis)
    
    def track_workflow_start(self, workflow_name, context):
        self.metrics[workflow_name] = {
            'start_time': time.time(),
            'status': 'running'
        }
    
    def track_workflow_complete(self, workflow_name, result, context):
        if workflow_name in self.metrics:
            self.metrics[workflow_name]['end_time'] = time.time()
            self.metrics[workflow_name]['status'] = result.get('status', 'unknown')
            self.metrics[workflow_name]['duration'] = (
                self.metrics[workflow_name]['end_time'] - 
                self.metrics[workflow_name]['start_time']
            )
    
    def alert_on_drift(self, drift_info, project_path):
        if drift_info.get('severity') == 'high':
            self.send_alert(f"High severity drift detected in {project_path}")
    
    def record_analysis(self, analysis_results, project_path):
        self.metrics['last_analysis'] = {
            'path': project_path,
            'timestamp': time.time(),
            'issues': len(analysis_results.get('issues', []))
        }
```

## Hook Development Tips

1. **Start simple**: Begin with basic hooks and add complexity as needed
2. **Use logging**: Log hook execution for debugging
3. **Consider performance**: Hooks run synchronously, so keep them fast
4. **Test thoroughly**: Test hooks with various inputs and edge cases
5. **Document behavior**: Document what your hooks modify and why

## Future Enhancements

Planned improvements to the hook system:

- Async hook support for long-running operations
- Hook namespacing for better organization
- Dynamic hook registration/unregistration
- Hook performance profiling
- Hook dependency management