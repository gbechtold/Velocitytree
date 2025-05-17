# Git Workflow with Natural Language

Velocitytree now includes powerful git integration that allows you to use natural language to manage your development workflow. This guide covers the new git-centric features that help streamline feature development.

## Overview

The git integration provides:
- Natural language branch creation
- Intelligent commit message generation
- Semantic versioning automation
- Change analysis and insights

## Creating Feature Branches

Use natural language to create descriptive feature branches:

```bash
# Basic feature creation
vtree git feature "Add user authentication with OAuth support"
# Creates: feature/add-user-authentication-oauth-support

# With custom prefix
vtree git feature "Fix login timeout issue" --prefix bugfix/
# Creates: bugfix/fix-login-timeout-issue

# With ticket reference
vtree git feature "Implement payment gateway" --ticket PROJ-123
# Creates: feature/proj-123-implement-payment-gateway
```

### Branch Naming Intelligence

The system automatically:
- Extracts action types (add, fix, update, refactor)
- Removes common words (the, a, for, to)
- Handles ticket references (#123, JIRA-456)
- Ensures valid git branch names

## Smart Commit Messages

Generate conventional commit messages based on your changes:

```bash
# Analyze changes and suggest a commit message
vtree git commit

# Provide custom message (will be enhanced)
vtree git commit -m "Update user profile validation"

# Force a specific commit type
vtree git commit --type feat
```

### Commit Analysis

The commit command provides:
- File change summary
- Insertion/deletion counts
- Impact level assessment
- Component detection
- Conventional commit format

Example output:
```
Change Analysis:
Files changed: 3
Insertions: +45
Deletions: -12
Impact level: moderate
Change type: feature

Suggested commit message:
feat(auth): add OAuth provider integration

Use this commit message? [Y/n]:
```

## Semantic Versioning

Automate version tagging with semantic versioning:

```bash
# Bump patch version (0.1.0 -> 0.1.1)
vtree git tag

# Bump minor version (0.1.1 -> 0.2.0)
vtree git tag --type minor

# Bump major version (0.2.0 -> 1.0.0)
vtree git tag --type major

# Custom version
vtree git tag --version v2.5.0
```

## Analyzing Changes

Get detailed insights about your current changes:

```bash
vtree git analyze
```

This provides:
- Detailed change metrics
- Component impact analysis
- File-by-file breakdown
- Suggested commit message

## Workflow Example

Here's a complete workflow using the git features:

```bash
# 1. Start a new feature
vtree git feature "Add dark mode support to dashboard"

# 2. Make your code changes
# ... edit files ...

# 3. Analyze what changed
vtree git analyze

# 4. Create a smart commit
vtree git commit

# 5. When feature is complete, tag a release
vtree git tag --type minor

# 6. Push to remote
git push origin feature/add-dark-mode-support-dashboard
git push origin --tags
```

## Configuration

Customize git behavior in `.velocitytree.yaml`:

```yaml
git:
  branch_prefix: "feature/"
  commit_format: "conventional"  # or "semantic", "custom"
  auto_tag: true
  version_strategy: "semantic"
```

## Best Practices

1. **Descriptive Feature Names**: Be specific in your feature descriptions
   ```bash
   # Good
   vtree git feature "Add email verification for user registration"
   
   # Less specific
   vtree git feature "Add verification"
   ```

2. **Include Ticket References**: Always include ticket numbers when available
   ```bash
   vtree git feature "Fix cart calculation bug" --ticket BUG-456
   ```

3. **Review Commit Messages**: Always review suggested commit messages before accepting
   ```bash
   vtree git commit
   # Review the suggestion, modify if needed
   ```

4. **Use Semantic Versioning**: Follow semantic versioning for releases
   - Patch: Bug fixes, minor changes
   - Minor: New features, backward compatible
   - Major: Breaking changes

## Integration with Existing Workflows

The git features integrate seamlessly with existing git workflows:

```bash
# Create feature branch with Velocitytree
vtree git feature "Implement user search"

# Regular git workflow
git add .
git status

# Smart commit with Velocitytree
vtree git commit

# Regular git push
git push origin feature/implement-user-search
```

## Troubleshooting

### "No git repository found"
Make sure you're in a git repository:
```bash
git init
```

### "Branch already exists"
The branch name already exists. Either:
1. Switch to the existing branch: `git checkout branch-name`
2. Delete the old branch: `git branch -d branch-name`
3. Use a different description

### Commit analysis shows no changes
Make sure you have staged or unstaged changes:
```bash
git status
git add .
```

## Advanced Usage

### Custom Branch Patterns

Create branches with specific patterns:
```bash
# Release branches
vtree git feature "Prepare version 2.0 release" --prefix release/

# Hotfix branches
vtree git feature "Critical security patch" --prefix hotfix/

# Experiment branches
vtree git feature "Try new caching strategy" --prefix experiment/
```

### Commit Message Templates

The system supports different commit formats:
- Conventional Commits: `feat:`, `fix:`, `docs:`, etc.
- Semantic: Clear, descriptive messages
- Custom: Your team's specific format

### Integration with CI/CD

Use the version tagging for automated deployments:
```bash
# Tag for production release
vtree git tag --type minor

# CI/CD can trigger on new tags
git push origin --tags
```

## Future Enhancements

Upcoming features include:
- PR description generation
- Automatic changelog creation
- Git hook integration
- Team workflow templates
- AI-powered code review preparation

---

For more information, see the [CLI Reference](../cli-reference.md) or run `vtree git --help`.