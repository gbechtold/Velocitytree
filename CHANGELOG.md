# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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