"""
Lifecycle Demo Plugin

This plugin demonstrates the use of lifecycle hooks in Velocitytree.
"""

import time
from typing import Dict, Any, List

from velocitytree.plugin_system import Plugin


class LifecycleDemoPlugin(Plugin):
    """Plugin that demonstrates lifecycle hooks."""
    
    name = "lifecycle_demo"
    version = "1.0.0"
    description = "Demonstrates plugin lifecycle hooks"
    author = "Velocitytree Team"
    
    def __init__(self, config=None):
        super().__init__(config)
        self.workflow_metrics: Dict[str, Dict[str, Any]] = {}
        self.command_history: List[Dict[str, Any]] = []
        self.ai_request_count = 0
    
    def activate(self):
        """Called when the plugin is activated."""
        super().activate()
        self.logger.info("Lifecycle Demo plugin activated - ready to monitor events")
    
    def deactivate(self):
        """Called when the plugin is deactivated."""
        self.logger.info("Lifecycle Demo plugin deactivated")
        self.logger.info(f"Total AI requests monitored: {self.ai_request_count}")
        self.logger.info(f"Total workflows monitored: {len(self.workflow_metrics)}")
        super().deactivate()
    
    def register_hooks(self, hook_manager):
        """Register hooks for this plugin."""
        # Core lifecycle
        hook_manager.register_hook('velocitytree_startup', self.on_startup, priority=10)
        hook_manager.register_hook('velocitytree_shutdown', self.on_shutdown, priority=90)
        
        # Plugin lifecycle
        hook_manager.register_hook('plugin_activated', self.on_plugin_activated)
        hook_manager.register_hook('plugin_deactivated', self.on_plugin_deactivated)
        
        # Command lifecycle
        hook_manager.register_hook('before_command', self.before_command, priority=20)
        hook_manager.register_hook('after_command', self.after_command)
        
        # Workflow lifecycle
        hook_manager.register_hook('workflow_start', self.on_workflow_start)
        hook_manager.register_hook('workflow_step', self.on_workflow_step)
        hook_manager.register_hook('workflow_complete', self.on_workflow_complete)
        hook_manager.register_hook('workflow_error', self.on_workflow_error)
        
        # File operations
        hook_manager.register_hook('before_flatten', self.before_flatten)
        hook_manager.register_hook('after_flatten', self.after_flatten)
        
        # AI integration
        hook_manager.register_hook('before_ai_request', self.before_ai_request)
        hook_manager.register_hook('after_ai_response', self.after_ai_response)
        
        # Monitoring
        hook_manager.register_hook('drift_detected', self.on_drift_detected)
        hook_manager.register_hook('alert_created', self.on_alert_created)
    
    # Core lifecycle hooks
    def on_startup(self, config):
        """Called when Velocitytree starts."""
        self.logger.info("🚀 Velocitytree is starting up!")
        self.logger.info(f"Configuration loaded: {config.config_file}")
    
    def on_shutdown(self):
        """Called when Velocitytree shuts down."""
        self.logger.info("👋 Velocitytree is shutting down!")
        self._print_summary()
    
    # Plugin lifecycle hooks
    def on_plugin_activated(self, plugin_name):
        """Called when any plugin is activated."""
        self.logger.debug(f"Plugin activated: {plugin_name}")
    
    def on_plugin_deactivated(self, plugin_name):
        """Called when any plugin is deactivated."""
        self.logger.debug(f"Plugin deactivated: {plugin_name}")
    
    # Command lifecycle hooks
    def before_command(self, command_name, args, kwargs):
        """Called before a command is executed."""
        start_time = time.time()
        self.command_history.append({
            'command': command_name,
            'args': args,
            'kwargs': kwargs,
            'start_time': start_time
        })
        self.logger.info(f"⚡ Executing command: {command_name}")
        return args, kwargs
    
    def after_command(self, command_name, result):
        """Called after a command is executed."""
        # Find the corresponding command in history
        for cmd in reversed(self.command_history):
            if cmd['command'] == command_name and 'end_time' not in cmd:
                cmd['end_time'] = time.time()
                cmd['duration'] = cmd['end_time'] - cmd['start_time']
                cmd['result'] = result
                self.logger.info(f"✅ Command completed: {command_name} ({cmd['duration']:.2f}s)")
                break
        return result
    
    # Workflow lifecycle hooks
    def on_workflow_start(self, workflow_name, context):
        """Called when a workflow starts."""
        self.workflow_metrics[workflow_name] = {
            'start_time': time.time(),
            'steps_completed': 0,
            'errors': []
        }
        self.logger.info(f"🔄 Workflow started: {workflow_name}")
    
    def on_workflow_step(self, workflow_name, step_name, context):
        """Called before each workflow step."""
        self.logger.debug(f"  📍 Step: {step_name}")
        if workflow_name in self.workflow_metrics:
            self.workflow_metrics[workflow_name]['steps_completed'] += 1
        
        # Example: Skip steps based on context
        if context.get('skip_tests', False) and 'test' in step_name.lower():
            self.logger.info(f"  ⏭️  Skipping test step: {step_name}")
            return True  # Skip this step
        
        return False  # Continue normally
    
    def on_workflow_complete(self, workflow_name, result, context):
        """Called when a workflow completes."""
        if workflow_name in self.workflow_metrics:
            metrics = self.workflow_metrics[workflow_name]
            metrics['end_time'] = time.time()
            metrics['duration'] = metrics['end_time'] - metrics['start_time']
            metrics['status'] = result.get('status', 'unknown')
            
            self.logger.info(
                f"✨ Workflow completed: {workflow_name} "
                f"({metrics['duration']:.2f}s, {metrics['steps_completed']} steps)"
            )
    
    def on_workflow_error(self, workflow_name, error, context):
        """Called when a workflow encounters an error."""
        self.logger.error(f"❌ Workflow error in {workflow_name}: {error}")
        if workflow_name in self.workflow_metrics:
            self.workflow_metrics[workflow_name]['errors'].append(str(error))
    
    # File operation hooks
    def before_flatten(self, directory, options):
        """Called before flattening operation."""
        self.logger.info(f"📁 Starting flatten operation on: {directory}")
        
        # Example: Add custom patterns to ignore
        if 'ignore_patterns' in options:
            options['ignore_patterns'].append('*.lifecycle_demo')
        
        return options
    
    def after_flatten(self, result):
        """Called after flattening operation."""
        files_count = result.get('files_processed', 0)
        self.logger.info(f"📄 Flatten completed: {files_count} files processed")
    
    # AI integration hooks
    def before_ai_request(self, prompt, context, system_prompt):
        """Called before AI request."""
        self.ai_request_count += 1
        self.logger.debug(f"🤖 AI request #{self.ai_request_count}")
        
        # Example: Add context to prompt
        if context.get('project_type'):
            enhanced_prompt = f"{prompt}\n\nProject type: {context['project_type']}"
            return enhanced_prompt
        
        return prompt
    
    def after_ai_response(self, response, prompt):
        """Called after AI response."""
        self.logger.debug(f"💬 AI response received ({len(response)} chars)")
        return response
    
    # Monitoring hooks
    def on_drift_detected(self, drift_info, project_path):
        """Called when code drift is detected."""
        severity = drift_info.get('severity', 'unknown')
        self.logger.warning(f"🚨 Drift detected in {project_path} (severity: {severity})")
        
        # Example: Send notification for high severity
        if severity == 'high':
            self._send_notification(f"High severity drift in {project_path}")
    
    def on_alert_created(self, alert_data, channel):
        """Called when an alert is created."""
        self.logger.info(f"🔔 Alert created on {channel}: {alert_data.get('message', '')}")
    
    # Helper methods
    def _print_summary(self):
        """Print summary of plugin activity."""
        self.logger.info("\n📊 Lifecycle Demo Plugin Summary:")
        self.logger.info(f"  Commands executed: {len(self.command_history)}")
        self.logger.info(f"  Workflows monitored: {len(self.workflow_metrics)}")
        self.logger.info(f"  AI requests: {self.ai_request_count}")
        
        if self.command_history:
            total_duration = sum(cmd.get('duration', 0) for cmd in self.command_history)
            self.logger.info(f"  Total command time: {total_duration:.2f}s")
    
    def _send_notification(self, message):
        """Send a notification (placeholder for actual implementation)."""
        self.logger.info(f"📬 Notification: {message}")
    
    def register_commands(self, cli):
        """Register CLI commands for this plugin."""
        import click
        
        @cli.group()
        def lifecycle():
            """Lifecycle demo plugin commands."""
            pass
        
        @lifecycle.command()
        def stats():
            """Show lifecycle plugin statistics."""
            click.echo("Lifecycle Demo Plugin Statistics:")
            click.echo(f"  Commands executed: {len(self.command_history)}")
            click.echo(f"  Workflows monitored: {len(self.workflow_metrics)}")
            click.echo(f"  AI requests: {self.ai_request_count}")
            
            if self.workflow_metrics:
                click.echo("\nRecent Workflows:")
                for name, metrics in list(self.workflow_metrics.items())[-5:]:
                    status = metrics.get('status', 'running')
                    duration = metrics.get('duration', 0)
                    click.echo(f"  {name}: {status} ({duration:.2f}s)")
        
        @lifecycle.command()
        def hooks():
            """List all hooks this plugin listens to."""
            from velocitytree.plugin_system import HookManager
            
            hook_manager = HookManager()
            click.echo("Lifecycle Demo Plugin Hooks:")
            
            for category in ['Core', 'Plugin', 'Command', 'Workflow', 'File', 'AI', 'Monitoring']:
                click.echo(f"\n{category} Hooks:")
                for hook_name in sorted(hook_manager.hook_metadata.keys()):
                    if category.lower() in hook_name:
                        metadata = hook_manager.get_hook_metadata(hook_name)
                        click.echo(f"  {hook_name}: {metadata.get('description', '')}")