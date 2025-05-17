# Velocitytree Development Workflow

## Ticket System

We use a simple prefix system for tickets:
- `FEAT-XXX`: New features
- `FIX-XXX`: Bug fixes
- `DOC-XXX`: Documentation updates
- `TEST-XXX`: Testing improvements
- `REFACTOR-XXX`: Code refactoring
- `PERF-XXX`: Performance improvements

## Git Workflow

1. Create a ticket/issue
2. Create a feature branch: `git checkout -b ticket-type/TICKET-XXX-description`
3. Make changes
4. Write tests
5. Commit with meaningful messages: `[TICKET-XXX] Description of changes`
6. Push branch
7. Create Pull Request
8. Review and test
9. Merge to main

## Branch Naming Convention

- Feature: `feature/FEAT-XXX-description`
- Bugfix: `bugfix/FIX-XXX-description`
- Documentation: `docs/DOC-XXX-description`
- Testing: `test/TEST-XXX-description`

## Commit Message Format

```
[TICKET-XXX] Short description (50 chars or less)

- Detailed bullet points explaining the changes
- Include rationale for significant changes
- Reference any related tickets
```

## Testing Requirements

- All new features must have tests
- Bug fixes should include regression tests
- Maintain >80% code coverage
- Run tests before committing: `pytest`

## Review Process

- Self-review your changes
- Ensure CI passes
- Check test coverage
- Update documentation if needed