# Conversational Project Planning Guide

Velocitytree's conversational planning feature helps you transform ideas into structured project plans through natural dialogue. This guide covers how to use the planning commands to create comprehensive project plans, roadmaps, and tickets.

## Overview

The conversational planner provides:
- Interactive dialogue-based project planning
- Automatic extraction of goals, features, and requirements
- Export to multiple formats (Markdown, JSON)
- Session management (pause, resume, review)
- Integration with ticket systems (coming soon)

## Getting Started

### Starting a New Planning Session

```bash
# Start a new planning session
vtree plan start

# Start with a specific project name
vtree plan start --name "My E-commerce Platform"

# Use a planning template
vtree plan start --template web_app
```

### Interactive Planning Process

Once you start a session, Velocitytree will guide you through several planning stages:

1. **Project Initialization** - Define your project vision
2. **Goal Setting** - Establish clear objectives
3. **Feature Definition** - Identify key features
4. **Technical Planning** - Choose tech stack
5. **Timeline Estimation** - Set milestones
6. **Resource Planning** - Plan team and budget
7. **Review** - Review the complete plan
8. **Finalization** - Export your plan

### Example Session

```bash
$ vtree plan start
What's the name of your project? Task Management App

✓ Started planning session: a1b2c3d4...

Welcome! Let's plan your project. What type of project would you like to build? 
Please describe your vision in a few sentences.

> I want to build a task management web application that helps teams collaborate 
> more effectively. It should have real-time updates, project boards, and 
> integration with popular tools like Slack and GitHub.

Great! Now let's define your project goals. What are the main objectives you 
want to achieve? Think about what success looks like for this project.

> My main goals are:
> 1. Create an intuitive interface that reduces task management overhead
> 2. Support teams of 5-50 people with real-time collaboration
> 3. Integrate with at least 5 popular productivity tools
> 4. Achieve 90% user satisfaction rating within 6 months

Excellent goals! Now let's identify the key features. What are the must-have 
features for your project? We can prioritize them as high, medium, or low priority.

> Core features needed:
> - User authentication and team management
> - Project boards with drag-and-drop tasks
> - Real-time notifications and updates
> - Integration API for third-party tools
> - Mobile responsive design
> - Activity timeline and audit logs
```

## Planning Commands

### Session Management

```bash
# List all planning sessions
vtree plan list

# List sessions by status
vtree plan list --status active
vtree plan list --status completed

# Show session details
vtree plan show <session-id>

# Resume a paused session
vtree plan resume <session-id>

# Export a completed plan
vtree plan export <session-id> --format markdown
vtree plan export <session-id> --format json --output project-plan.json
```

### During a Session

While in a planning session, you can use these commands:

- `help` - Get help for the current stage
- `back` - Go back to the previous stage
- `skip` - Skip the current question
- `cancel` - Cancel the session (can resume later)
- `done` - Mark the current stage as complete

## Planning Stages in Detail

### 1. Project Initialization

Define your project's core vision and purpose.

**What to include:**
- Project type (web app, API, library, tool)
- Target audience
- Problem it solves
- Key differentiators

**Example inputs:**
```
> I'm building a SaaS platform for small businesses to manage customer relationships. 
> It will be simpler than Salesforce but more powerful than spreadsheets, focusing 
> on ease of use and automation.
```

### 2. Goal Setting

Establish measurable objectives.

**What to include:**
- Business goals
- Technical goals
- User experience goals
- Success metrics

**Example inputs:**
```
> Goals:
> 1. Onboard 100 paying customers in the first year
> 2. Achieve 99.9% uptime
> 3. Reduce customer onboarding time to under 5 minutes
> 4. Build a scalable architecture supporting 10,000 concurrent users
```

### 3. Feature Definition

List and prioritize features.

**What to include:**
- Core features (MVP)
- Secondary features
- Future enhancements
- Feature priorities

**Example inputs:**
```
> Must-have features:
> - User registration and authentication
> - Contact management with custom fields
> - Email campaign builder
> - Basic analytics dashboard
> - API for integrations
> 
> Nice-to-have features:
> - Advanced automation workflows
> - A/B testing for campaigns
> - Mobile app
> - AI-powered insights
```

### 4. Technical Planning

Define your technology stack.

**What to include:**
- Programming languages
- Frameworks and libraries
- Database choices
- Infrastructure needs
- Development tools

**Example inputs:**
```
> Frontend: React with TypeScript, Tailwind CSS
> Backend: Node.js with Express, GraphQL
> Database: PostgreSQL for main data, Redis for caching
> Infrastructure: AWS with Docker containers
> CI/CD: GitHub Actions
> Monitoring: Datadog, Sentry
```

### 5. Timeline Estimation

Set realistic milestones and deadlines.

**What to include:**
- Project phases
- Milestone deliverables
- Estimated durations
- Dependencies

**Example inputs:**
```
> Timeline breakdown:
> Phase 1 (2 months): Core infrastructure and authentication
> Phase 2 (3 months): MVP features - contact management, basic campaigns
> Phase 3 (2 months): Analytics and API
> Phase 4 (1 month): Beta testing and refinements
> Phase 5 (2 months): Launch preparation and marketing
> 
> Target launch date: October 2024
```

### 6. Resource Planning

Plan team and budget requirements.

**What to include:**
- Team roles needed
- Skill requirements
- Budget estimates
- External resources

**Example inputs:**
```
> Team needs:
> - 1 Full-stack developer (lead)
> - 1 Frontend developer
> - 1 Backend developer
> - 1 UX/UI designer (part-time)
> - 1 DevOps engineer (part-time)
> - 1 Product manager
> 
> Budget: $500,000 for first year
> - Development: $350,000
> - Infrastructure: $50,000
> - Tools and services: $30,000
> - Marketing: $70,000
```

## Export Formats

### Markdown Export

Creates a well-structured Markdown document:

```markdown
# Task Management App

**Description:** A task management web application that helps teams collaborate more effectively...

## Goals
1. Create an intuitive interface that reduces task management overhead (Priority: high)
2. Support teams of 5-50 people with real-time collaboration (Priority: high)
...

## Features
### User Authentication
**Description:** User registration and authentication system
**Priority:** high
**Effort:** medium
**Requirements:**
- OAuth support
- Multi-factor authentication
...

## Technical Stack
**Frontend:** React, TypeScript, Tailwind CSS
**Backend:** Node.js, Express, GraphQL
**Database:** PostgreSQL, Redis
...

## Timeline
...
```

### JSON Export

Creates a structured JSON file suitable for processing:

```json
{
  "name": "Task Management App",
  "description": "A task management web application...",
  "goals": [
    {
      "description": "Create an intuitive interface...",
      "priority": "high",
      "success_criteria": ["User satisfaction > 90%"]
    }
  ],
  "features": [
    {
      "name": "User Authentication",
      "description": "User registration and authentication system",
      "priority": "high",
      "effort_estimate": "medium",
      "requirements": ["OAuth support", "MFA"]
    }
  ],
  "tech_stack": {
    "frontend": ["React", "TypeScript"],
    "backend": ["Node.js", "Express"]
  }
}
```

## Best Practices

### 1. Be Specific

Instead of:
> "I want to build a web app"

Try:
> "I want to build a project management web app for creative agencies that 
> integrates with design tools like Figma and Adobe Creative Cloud"

### 2. Think in User Stories

Frame features as user needs:
> "As a project manager, I need to see all tasks across projects in one 
> dashboard so I can identify bottlenecks quickly"

### 3. Set Measurable Goals

Instead of:
> "Make it fast"

Try:
> "Page load times under 2 seconds for 95% of users"

### 4. Consider Constraints

Mention important limitations:
> "We have a 6-month deadline and a team of 3 developers. Budget is $100k."

### 5. Plan Iteratively

Start with MVP:
> "For MVP: Basic task creation and assignment. 
> For v2: Add time tracking and reporting.
> For v3: Add automation and AI suggestions."

## Advanced Features

### Using Templates

Templates provide pre-configured prompts for common project types:

```bash
# Available templates
vtree plan start --template web_app
vtree plan start --template mobile_app
vtree plan start --template api_service
vtree plan start --template cli_tool
```

### Collaborative Planning (Coming Soon)

Multiple team members can join a planning session:

```bash
# Start collaborative session
vtree plan start --collaborative

# Join existing session
vtree plan join <session-id>
```

### AI-Powered Suggestions

The planner provides intelligent suggestions based on:
- Similar projects
- Industry best practices
- Common patterns
- Your previous sessions

## Troubleshooting

### Session Won't Resume

If a session won't resume:
1. Check session ID: `vtree plan list`
2. Verify session status isn't "completed"
3. Check for session file in `~/.velocitytree/planning_sessions/`

### Export Issues

If export fails:
1. Ensure session is saved: `vtree plan show <session-id>`
2. Check file permissions for output location
3. Try different format: `--format json` instead of `--format markdown`

### AI Response Issues

If AI responses seem off:
1. Provide more specific information
2. Use the `back` command to retry
3. Check AI provider configuration: `vtree config`

## Integration Possibilities

### GitHub Issues (Coming Soon)

```bash
# Export directly to GitHub Issues
vtree plan export <session-id> --to github --repo username/project
```

### JIRA Integration (Coming Soon)

```bash
# Create JIRA tickets from plan
vtree plan export <session-id> --to jira --project PROJ
```

### Continuous Planning

Use planning sessions throughout development:
1. Initial planning session
2. Sprint planning sessions
3. Feature planning sessions
4. Retrospective planning

## Tips for Success

1. **Take Your Time** - Better planning saves development time
2. **Be Realistic** - Consider actual constraints and resources
3. **Get Specific** - Vague plans lead to vague results
4. **Iterate** - Plans can and should evolve
5. **Document Decisions** - Explain the "why" behind choices

## Examples Repository

Find example planning sessions for common project types:
- E-commerce Platform
- SaaS Application  
- Mobile App
- API Service
- Developer Tool
- Content Management System

Visit: [github.com/velocitytree/planning-examples](https://github.com/velocitytree/planning-examples)

---

For more information, see the [CLI Reference](../cli-reference.md) or run `vtree plan --help`.