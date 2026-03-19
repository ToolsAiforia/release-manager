# Contributing to Aiphoria

Thank you for your interest in contributing to Aiphoria! This guide will help you get started.

**Audience:** These guidelines apply to all contributors—human developers and AI coding assistants alike.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Quick Start](#quick-start)
- [How to Contribute](#how-to-contribute)
- [Git Workflow](#git-workflow)
- [PR Guidelines](#pr-guidelines)
- [Code Standards](#code-standards)
- [Getting Help](#getting-help)

## Code of Conduct

All contributors must adhere to our [Code of Conduct](./CODE_OF_CONDUCT.md). Please read it before contributing.

## Quick Start

💡 If you are using Claude as code assistant, please use `platform-engineering plugin` to get the best experience. It contains all the tools and knowledge to help you follow the standards and guidelines. Read original plugin documentation [here](https://github.com/ToolsAiforia/platform-engineering/blob/main/claude-plugins/platform/README.md).

### Prerequisites

| Stack          | Requirements                                                     |
| -------------- | ---------------------------------------------------------------- |
| **Python**     | Python 3.x, [uv](https://docs.astral.sh/uv/)                     |
| **TypeScript** | [Bun](https://bun.sh/) 1.x, [NodeJS](https://nodejs.org/) 22 LTS |

Use [README.md](./README.md) for development setup instructions.

## How to Contribute

Read [platform.meta.yml](./platform.meta.yml) to get the team's communication channels information.

### Reporting Bugs

1. Check if the issue already exists in associated Linear team.
2. Create a new issue with:
   - Label: **IssueType.BUG**
   - Status: **Triage**
   - Meaningful title
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details

> TIP: Use [Bug Report](https://linear.app/aiphoria-ai/team/QA/new?template=3253b758-2830-4302-8bc1-991617e780cd) issue template in Linear to create a bug report.

### Suggesting Features

1. Open a discussion in the team's Slack channel or issue in Linear (Status: **Triage**)
2. Describe the use case and proposed solution
3. Wait for feedback before starting implementation

> TIP: Use [Feature Request](https://linear.app/aiphoria-ai/team/PL/new?template=4ad8c9d5-fb4e-4bb0-85f1-8ffc9aab0060) issue template in Linear to create a feature request.

### Submitting Code

1. Create a branch from `main` following [branch naming convention](#branches)
2. Make your changes following [code standards](#code-standards)
3. Write tests for new functionality
4. Submit a PR following [PR guidelines](#pull-request-guidelines)

> What is Triage?
> Teams use Triage to manage issues between backlog and sprint planning. Triage means that the issue is not yet ready to be worked on — it must be analyzed and discussed before being assigned to a sprint. Read original [Linear documentation](https://linear.app/docs/triage) for more details.

## Git Workflow

We are coding in the platform of many services. One issue can be implemented in multiple PRs and services. That's why we need to be consistent with the branch naming convention. It helps to associate all changes related to the same issue across all services.

### Branches

Branch names link GitHub PR to Linear issue automatically. Read original [Linear documentation](https://linear.app/docs/github#link-through-pull-requests) for more details.

**Format:**

```
<issue-id>-<short-description>
```

**Rules:**

- `issue-id` is required, **lowercase** (e.g., `plcore-123`, `vux-45`) — Linear generates lowercase branch names
- `short-description` is required, lowercase, hyphens only (no underscores)
- Aim for under 60 characters (hard limit: 100)

**Examples:**

- ✅ `plcore-123-add-password-reset`
- ✅ `plcore-123-update-dto`
- ✅ `plcore-123-implement-audio-archiving`
- ✅ `vux-789-update-proto`
- ❌ `add-user-auth`
- ❌ `plcore_123_add_auth`
- ❌ `wip`

**Special Prefix Branches:**

Some changes don't require a Linear issue (see [Special PR Prefixes](#special-pr-prefixes)). Use the prefix as the branch identifier:

```
<prefix>-<short-description>
```

- `prefix` must be lowercase: `hotfix`, `trivial`, or `maintenance`
- Same rules apply: lowercase, hyphens only, aim for under 60 characters (hard limit: 100)

**Examples:**

- ✅ `hotfix-memory-leak-tts`
- ✅ `trivial-fix-typo-readme`
- ✅ `maintenance-upgrade-node-22`

⚠️ This rule is enforced by [automated PR validation](https://github.com/ToolsAiforia/contributing-action). Invalid branch names block PR merge.

> TIP: Use `/platform:create-branch` slash command to generate branch name.

**Release Branches:**

Automated release workflows create branches that don't follow the standard `<issue-id>-<short-description>` format. These are created by [release-action](https://github.com/ToolsAiforia/release-action) and platform delivery workflows. See [Unified Release & Platform Delivery Process](https://github.com/ToolsAiforia/platform-engineering/blob/main/docs/rfc/PlatformReleaseStandard.md) for details.

```
release-<version>
platform-bundle-<version>
```

- `version` is a SemVer number (e.g., `1.2.0`, `22.0.0`) — no `v` prefix
- No short description required

**Examples:**

- ✅ `release-1.2.0`
- ✅ `release-10.0.1`
- ✅ `platform-bundle-22.0.0`
- ✅ `platform-bundle-2.5.1`
- ❌ `release-v1.2.0` — no `v` prefix
- ❌ `release` — missing version

⚠️ These branches are created automatically by release workflows. Do not create them manually.

### Commits

We follow [Conventional Commits](https://www.conventionalcommits.org/). Motivation behind this:

- It makes it easier to generate changelog and release notes
- It helps to understand the changes and context faster
- It helps to focus on important details
- It helps to avoid unnecessary discussions
- It helps to respect codeowners and reviewers time
- It helps to keep the commit history clear and readable by humans and AI
- It helps to speed up the review process
- It helps to investigate bugs in important changes, not in docs, tests, etc.

**Format:**

```
<type>(<scope>): <subject>

[body — required for feat/fix/refactor]

[optional footer(s)]
```

**Rules:**

- **Type**: Required. One of: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- **Scope**: Optional. Component or module name
- **Subject**: Required. Lowercase, imperative mood, no period, max 50 chars. Must name the specific thing that changed
- **Issue ID**: Do NOT include in commit messages (branch handles linking)
- **PR References**: Do NOT reference PRs, review comments, or feedback in commit messages. Commits must be self-contained and understandable without viewing any PR
- **AI Co-authorship**: Do NOT include AI agent `Co-authored-by` trailers (e.g., Claude, ChatGPT, Copilot, Codex). Disable co-authorship in your AI tool settings.

**Commit Types:**

| Type       | Description                             |
| ---------- | --------------------------------------- |
| `feat`     | New feature                             |
| `fix`      | Bug fix                                 |
| `docs`     | Documentation only                      |
| `style`    | Code style (formatting, semicolons)     |
| `refactor` | Code change that neither fixes nor adds |
| `perf`     | Performance improvement                 |
| `test`     | Adding or updating tests                |
| `build`    | Build system or dependencies            |
| `ci`       | CI/CD configuration                     |
| `chore`    | Maintenance tasks                       |
| `revert`   | Reverting a previous commit             |

**Examples:**

✅ Commit with body (required for feat/fix/refactor):

```
feat(auth): add jwt token refresh endpoint

- Added /auth/refresh endpoint for issuing new access tokens
- Added 7-day expiry validation for refresh tokens
```

✅ Commits where body may be omitted:

```
docs: add environment variables reference to readme
test(auth): add jwt refresh token expiry edge cases
chore(deps): upgrade zod from 3.21 to 3.23
```

✅ Commit message with description and breaking change footer:

```
feat: allow provided config object to extend other configs

BREAKING CHANGE: `extends` key in config file is now used for extending other config files
```

```
fix: prevent racing of requests

Introduce a request id and a reference to latest request. Dismiss
incoming responses other than from latest request.

Remove timeouts which were used to mitigate the racing issue but are
obsolete now.
```

❌ Bad commits examples:

```
PLCORE-123: Add feature
Added new endpoint
fix: review updates
fix: resolve issue
feat: add new feature
refactor: address PR #107 review comments
docs(asr): update based on PR feedback
fix: changes requested in code review
wip
btw
```

⚠️ This rule is enforced by [automated PR validation](https://github.com/ToolsAiforia/contributing-action) and pre-commit hooks. Invalid commits block PR merge.

#### Atomic Commits

When your changes span multiple categories (docs, tests, implementation), consider splitting them into separate commits. This practice improves:

- **Reverting**: Cleanly undo specific changes without affecting unrelated code
- **Code Review**: Smaller focused commits are easier to review
- **Git Bisect**: Pinpoint exactly which commit introduced a bug
- **Changelog**: Each commit type appears in the right changelog section

**Recommended commit order:**

1. `docs` — Documentation first (context for reviewers)
2. `test` — Tests before implementation
3. `feat`/`fix`/`refactor` — Main implementation
4. `chore`/`build` — Configuration and dependencies
5. `ci` — CI/CD changes last

**Example:** If you add a feature with tests and docs, create 3 commits:

```
docs(auth): add jwt validation documentation
test(auth): add jwt validation tests
feat(auth): implement jwt validation
```

> TIP: Use `/platform:create-commit` slash command to generate commit message.

## PR Guidelines

**Why these rules are important:**

- It helps to associate all changes related to the same issue across all services
- It helps to generate changelog and release notes across all services
- It helps to understand the changes and context faster
- It helps to avoid unnecessary discussions

### PR Title

**Format:**

```
<ISSUE-ID>: <Business-valuable description>
```

**Rules:**

- `ISSUE-ID` is required, uppercase, followed by colon (as displayed in Linear)
- `Business-valuable description` is required, capitalized, business-focused, no period
- Under 120 characters total
- NOT Conventional Commits format — this is the default behavior for PR titles if you have only one commit, but again, respect codeowners and reviewers time. This PR will fail validation but reviewers already called to see the changes.

**PR title should be understandable:**

- From just that single line
- By someone on their first day at the company
- By someone outside the company
- When reviewed a year from now
- Without needing to read the code changes

**Avoid:**

- Implementation details (use PR body for those)
- Technical jargon without context
- Vague descriptions

**Examples:**

- ✅ `PLCORE-749: Allow TTS engine selection by language`
- ❌ `feat(tts): add language routing`
- ❌ `Added GRPC options`

⚠️ This rule is enforced by [automated PR validation](https://github.com/ToolsAiforia/contributing-action). Invalid PR titles block PR merge.

### Special PR Prefixes

Some changes don't fit the standard `<ISSUE-ID>: <description>` format — they are either urgent, too small for a ticket, or purely infrastructural. Special prefixes bypass PR title and description validation while keeping the history readable.

| Prefix         | When to use                                                                  | Example                               |
| -------------- | ---------------------------------------------------------------------------- | ------------------------------------- |
| `HOTFIX:`      | Emergency production fixes                                                   | `HOTFIX: Memory leak in TTS engine`   |
| `TRIVIAL:`     | Changes not affecting production or CI/CD: typos, docs, comments, formatting | `TRIVIAL: Fix typo in README`         |
| `MAINTENANCE:` | Infrastructure updates: deps, CI, configs                                    | `MAINTENANCE: Upgrade Node to 22 LTS` |

**Rules:**

- Prefix must be uppercase, followed by colon and space
- Description after prefix follows the same rules as standard PR titles (capitalized, no period, under 120 chars total)
- Use sparingly — most PRs should reference an issue ID

### Release PR Titles

Release PRs are created by [release-action](https://github.com/ToolsAiforia/release-action) and platform delivery workflows. Their titles bypass the standard `<ISSUE-ID>: <description>` format. See [Unified Release & Platform Delivery Process](https://github.com/ToolsAiforia/platform-engineering/blob/main/docs/rfc/PlatformReleaseStandard.md) for details.

**Format:**

```
Release [<name>] <version>
```

**Rules:**

- `Release` keyword is required, capitalized
- `name` is the service or library name (optional for single-package repos, required for monorepos)
- `version` is a SemVer number — no `v` prefix

**Examples:**

- ✅ `Release 1.2.0`
- ✅ `Release Dialog Manager 1.2.0`
- ✅ `Release Platform Bundle 22.0.0`
- ❌ `Release v1.2.0` — no `v` prefix
- ❌ `release 1.2.0` — must be capitalized

⚠️ Release PRs are created automatically by release workflows. Do not create them manually.

### PR Description

**Include in PR description:**

- Brief description of what and why
- Bullet list for important details
- Magic words for Linear (see [Magic Words](#magic-words))

**Example:**

```markdown
Users can now specify preferred TTS engine per language in the request.
This enables better voice quality for non-English languages.

- Added language_engine_map config option
- Falls back to default engine if no mapping exists

Closes PLCORE-749
```

#### Magic Words

Magic words link **additional** Linear issues to the PR beyond the one already linked via [branch name](#branches). Use them in PR descriptions (not titles, not comments).

| Keyword      | Behavior               | Example                 |
| ------------ | ---------------------- | ----------------------- |
| `Closes`     | Links, closes on merge | `Closes PLCORE-123`     |
| `Fixes`      | Links, closes on merge | `Fixes PLCORE-123`      |
| `Resolves`   | Links, closes on merge | `Resolves PLCORE-123`   |
| `Part of`    | Links without closing  | `Part of PLCORE-789`    |
| `Related to` | Links without closing  | `Related to PLCORE-456` |

**Multiple issues:**

```markdown
Closes PLCORE-123, Closes PLCORE-124
Part of PLCORE-100
```

> **Prerequisite:** Magic words require the [GitHub↔Linear integration](https://linear.app/docs/github) to be configured for the repository. Status automation (e.g., Done on merge) is controlled by team settings at _Settings > Team > Issue statuses & automations_. Read more in the [Linear documentation](https://linear.app/docs/github#link-through-pull-requests).

⚠️ This rule is enforced by [automated PR validation](https://github.com/ToolsAiforia/contributing-action). Invalid PR descriptions block PR merge.

> TIP: Use `/platform:create-pr` slash command to generate PR title and description.

### Working with Draft PRs

If you need to work on a PR but it's not ready for the human review, you must mark it as a draft. Why draft PRs are important:

- Draft PRs do not start review process automatically
- Draft PRs not enforce any validation rules
- Allows you to experiment with the changes before review
- Allows you to structure commits and PR before review

⚠️ Be sure to mark the PR as ready for review only after all changes are complete and the PR is valid and fully tested.

### Merging Strategies

We use the following merging strategies:

- **Rebase**: When the branch is up to date with the base branch
- **Squash**: When the branch is not up to date with the base branch

Only one of the strategies can be used for the current repository. The reason why:

- Avoid confusion and complexity in the review process
- Consistency in the commit history and PR structure
- Predictable and stable release process
- Predictable changelog and release notes

💡 Available strategy is shown in the GitHub UI on the merge button dropdown.

### PR Checklist

**Before submitting:**

- [ ] Branch name starts with issue ID
- [ ] PR title follows format: `<ISSUE-ID>: <Business-valuable description>`
- [ ] All commits follow Conventional Commits format
- [ ] No commits contain issue IDs in messages
- [ ] No commits contain AI agent Co-authored-by trailers
- [ ] Tests pass locally
- [ ] Code follows standards

### Good PR examples

**Title:** `PLCORE-749: Allow TTS engine selection by language parameter`

```
Users can now specify preferred TTS engine per language in the request.
This enables better voice quality for non-English languages.

- Added language_engine_map config option
- Falls back to default engine if no mapping exists

Closes PLCORE-749
```

**Title:** `PLCORE-715: Fix load balancing in TL-to-ASR gRPC calls`

```
ASR requests were all hitting the same pod due to missing gRPC options.
This caused uneven load distribution and occasional timeouts.

Closes PLCORE-715
```

**Title:** `VUX-20: Add protobuf messages for SIP playback duration reporting`

```
SIP client needs to report how much audio was actually played back
before user interruption. This data is required for billing accuracy.

- FinishTransferringPlaybackEvent
- StartTransferringPlaybackEvent

Closes VUX-20
```

**Title:** `PLCORE-605: Refactor Discrete Call service for grpclib-to-grpcio migration`

```
Part of the grpclib-to-grpcio migration project. Discrete Call service
is now fully migrated to grpcio.

- No functional changes
- All existing tests pass

Part of PLCORE-600
Closes PLCORE-605
```

**Title:** `PLCORE-607: Remove legacy ASR provider integrations`

```
Direct integrations with Google, Aiphoria v1, Audiogram, and Deepgram
are no longer used. All ASR now goes through the unified provider interface.

Closes PLCORE-607
```

## Code Standards

- [Platform Service Common Standard](https://github.com/ToolsAiforia/platform-engineering/blob/main/docs/rfc/PlatformServiceCommonStandard.md)
- [Platform Service Logging Standard](https://github.com/ToolsAiforia/platform-engineering/blob/main/docs/rfc/PlatformServiceLoggingStandard.md)
- [Unified Release & Platform Delivery Process](https://github.com/ToolsAiforia/platform-engineering/blob/main/docs/rfc/PlatformReleaseStandard.md)

## Getting Help

- **Technical questions:** Open an issue in Linear or ask your team lead in Slack
- **General questions:** [Platform public channel in Slack](https://aiforia-hq.slack.com/archives/C06LH73K4UT) — `#platform`
- **Code of Conduct issues:** [compliance@aiphoria.ai](mailto:compliance@aiphoria.ai)

## FAQ

### Why do we use Conventional Commits with Squash merging strategy?

We use AI agents to generate changelog and release notes. When you squash merge a PR, the commit messages saved in squashed commit message. That means anybody can easily understand the changes and context of the PR by reading the squashed commit message.

### What if somebody bypass commit message validation and merge PR with invalid commit message?

Only admins can bypass PR checks. In general and ideally this commit will be reverted by codeowners.
