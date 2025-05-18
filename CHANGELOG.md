# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-05-18

### Added
- **Continuous Monitoring & Evaluation** (Milestone 5.2)
  - Background monitoring process with configurable intervals
  - Real-time drift detection from specifications
  - Multi-channel alert system (log, file, email, webhook, console)
  - AI-powered realignment suggestions
  - Support for OpenAPI, README, and architecture specifications
  - Performance and security monitoring
  
- **Advanced Analytics** (Milestone 5.3)
  - ML-based predictive completion estimates
  - Confidence intervals and risk factors
  - Velocity tracking and burndown charts
  - Feature-level progress predictions
  
- **Claude AI Integration** (Milestone 5.4)
  - Native support for Anthropic's Claude
  - Efficient context streaming for large files
  - Specialized prompt templates
  - Intelligent response caching
  
- **Smart Documentation** (Milestone 4.2)
  - Context-aware documentation generation
  - Quality scoring and validation
  - Incremental documentation updates
  - Smart template selection
  
- **Real-time Suggestions** (Milestone 4.3)
  - Interactive code analysis sessions
  - Refactoring recommendations
  - Performance optimization suggestions
  - Learning from user feedback
  
- **Workflow Memory** (Milestone 5.1)
  - Decision history tracking
  - Precedent retrieval system
  - Conflict detection

### Changed
- Enhanced README with v2.0 features
- Updated dependency requirements
- Improved CLI command structure
- Reorganized monitoring commands

### Fixed
- Flask dependency issues in requirements.txt
- Import errors in monitoring modules
- Test coverage for new features

## [1.0.0] - 2024-05-17

### Added
- **Conversational Project Planning**: Interactive dialogue-based planning (Milestone 2)
  - Natural language project planning sessions
  - Structured goal and feature extraction
  - Multi-stage planning process (initialization → finalization)
  - Session management (pause, resume, export)
  - Export to Markdown and JSON formats
  - Planning templates for common project types
- **Git-Centric Feature Workflow**: Natural language git integration (Milestone 1)
  - Create feature branches from natural language descriptions
  - Generate smart commit messages based on code changes
  - Automatic semantic versioning and tagging
  - Comprehensive change analysis with impact assessment
  - Integration with ticket systems (GitHub Issues, JIRA)
- Complete plugin system with discovery, lifecycle, and hooks
- Example plugins: JSON formatter, output validator, custom commands
- Comprehensive plugin development guide
- Robust installation process with virtual environment support
- Setup scripts for Unix/Mac and Windows
- Improved project organization and structure

### Fixed
- Missing dependencies (anthropic, colorama) in pyproject.toml
- Plugin system test failures
- Import conflicts in plugin system

### Changed
- Reorganized README.md to be more user-friendly
- Improved documentation structure

## [0.1.0] - 2024-05-17

### Added
- Initial release of Velocitytree
- Core project flattening functionality
- AI integration with OpenAI and Anthropic
- Workflow automation system
- CLI interface with rich formatting
- Configuration management
- Basic plugin architecture
- Project initialization
- Context extraction for AI tools

### Features
- Tree flattening in multiple formats (markdown, JSON, tree)
- Smart file filtering and exclusion patterns
- AI-powered code analysis and suggestions
- Workflow templates and variables
- Conditional workflow steps
- Parallel workflow execution
- Plugin discovery and management

### Documentation
- README with installation and usage instructions
- Contributing guidelines
- Development documentation
- Plugin development guide

[Unreleased]: https://github.com/gbechtold/Velocitytree/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/gbechtold/Velocitytree/releases/tag/v0.1.0