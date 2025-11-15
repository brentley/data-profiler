# GitHub Issues Creation Guide

Complete guide for creating GitHub issues from the GITHUB_ISSUES.md document and linking them to pull requests and Git Flow management.

## Quick Start

1. **Read the issues**: `/Users/brent/git/data-profiler/GITHUB_ISSUES.md`
2. **Create each issue** on GitHub using the structured format
3. **Reference issues in PRs** using "Closes #N" pattern
4. **Link to Git Flow** using Git Workflow Manager

## Issue Creation Process

### Step 1: Access GitHub Issue Creation

Go to: `https://github.com/[your-org]/data-profiler/issues/new`

### Step 2: Fill in Issue Details

For each issue in GITHUB_ISSUES.md:

1. **Title** - Copy exact title from document
2. **Description** - Start with issue summary
3. **Add Sections** - Use GitHub markdown formatting:

```markdown
## Problem
[Copy from "Problem" section]

## Solution
[Copy from "Solution" section]

## Files Modified
[Copy list from "Files Modified" section]

## Testing Notes
[Copy from "Testing Notes" section]

## Acceptance Criteria
[Copy checklist items, prefixed with "- [ ]"]
```

### Step 3: Add Labels

For each issue, add labels:
- Type: `bug` | `enhancement` | `test` | `documentation`
- Priority: `critical` | `high` | `medium` | `low`
- Component: `backend` | `frontend` | `ui-ux`
- Status: `needs-review` | `in-progress` | `blocked`

### Step 4: Set Project and Milestone

- **Project**: data-profiler
- **Milestone**: UI/UX Improvements v1.1.0 (create if needed)

### Step 5: Submit Issue

Click "Submit new issue" button.

## Issue Reference Numbers

After creating issues, record the GitHub issue numbers:

```
#1 - Auto-detection metadata schema
#2 - Tailwind CSS max-width utilities
#3 - Fix oversized icons
#4 - Apply VisiQuate branding
#5 - Page layout redesign
#6 - Force dark mode
#7 - Enhance HTML report
#8 - Auto-detection tests
```

## Workflow: Creating PRs for Issues

### Using Git Flow Manager

```bash
# Create feature branch for an issue
/git-workflow:feature issue-3-fix-oversized-icons

# Check flow status
/git-workflow:flow-status

# Make changes...

# When ready to merge
/git-workflow:finish
```

### Manual Git Flow

```bash
# Start feature branch (from develop)
git checkout -b feature/issue-3-fix-oversized-icons develop

# Make changes to address issue
# Commit with issue reference
git commit -m "fix: reduce icon sizes across components (fixes #3)"

# Push feature branch
git push -u origin feature/issue-3-fix-oversized-icons

# Create PR linking to issue
gh pr create \
  --title "Fix: Reduce oversized icons across components" \
  --body "Closes #3

## Changes
- Reduced feature card icons from 40px to 32px
- Reduced upload area icon to 40px
- Added CSS icon size variables

## Testing
- Visual inspection at 1920x1080
- Verified proportions with text
- Dark mode appearance checked

## Fixes
- Closes #3"
```

### PR Naming Convention

- **Branch name**: `feature/issue-N-short-description` or `issue-N-description`
- **PR title**: `fix/feat: description (closes #N)`
- **Commit messages**: Include `(fixes #N)` at end

### PR Template

```markdown
## Description
This PR addresses [issue #N - brief description]

## Changes Made
- Specific change 1
- Specific change 2
- Specific change 3

## Files Modified
- File 1
- File 2
- File 3

## How to Test
1. Step 1 to reproduce
2. Step 2 to verify fix
3. Expected result

## Acceptance Criteria
- [ ] All tests pass
- [ ] Code follows project standards
- [ ] Documentation updated
- [ ] No breaking changes
- [ ] Performance verified

## Screenshots (if UI changes)
[Add before/after screenshots]

## Related Issues
Closes #N
```

## Issue Dependency Graph

```
Issue #1: Auto-detection metadata schema
├─ Depends on API structure (app.py, models/run.py)
├─ Feeds into Issue #7 (HTML report)
└─ Enables Issue #8 (auto-detection tests)

Issue #2: Tailwind CSS max-width
├─ Prerequisite for Issue #5 (layout redesign)
└─ Used throughout Issues #4, #6

Issue #3: Fix oversized icons
├─ Independent
├─ Impacts visual of Issues #4, #5
└─ Quick win (low effort)

Issue #4: Apply VisiQuate branding
├─ Depends on Issue #2, #3
├─ Feeds into Issue #5, #6
└─ Uses Issue #1 data in FileSummary

Issue #5: Page layout redesign
├─ Depends on Issues #2, #3, #4
├─ Major refactor (high effort)
└─ Improves entire UI

Issue #6: Force dark mode
├─ Can be done independently
├─ Simplifies Issues #4, #5
└─ Quick win (low effort)

Issue #7: Enhance HTML report
├─ Depends on Issue #1 (auto-detection metadata)
├─ Backend changes (medium effort)
└─ User-facing enhancement

Issue #8: Auto-detection tests
├─ Depends on Issue #1 structure
├─ Validates auto-detection logic
└─ Testing (medium effort)
```

## Recommended Implementation Order

### Phase 1: Quick Wins (1-2 days)
1. **Issue #3** - Fix oversized icons (1-2 hours)
2. **Issue #6** - Force dark mode (30 minutes)

**Impact**: Immediate visual improvement, simplifies other work

### Phase 2: Foundation (2-3 days)
3. **Issue #2** - Tailwind CSS max-width (2-4 hours)
4. **Issue #1** - Auto-detection metadata schema (4-6 hours)

**Impact**: Enables layout work, fixes structural issues

### Phase 3: Design System (2-3 days)
5. **Issue #4** - Apply VisiQuate branding (4-6 hours)
6. **Issue #5** - Page layout redesign (6-8 hours)

**Impact**: Professional appearance, improved readability

### Phase 4: Polish (1-2 days)
7. **Issue #7** - Enhance HTML report (4-6 hours)
8. **Issue #8** - Auto-detection tests (4-6 hours)

**Impact**: User experience, reliability

## Tracking Progress

### GitHub Project Board

Create columns:
- 📋 Backlog - All issues
- 🔄 In Progress - Current work
- 👀 Review - PR submitted
- ✅ Done - Merged

### Milestone Tracking

```
UI/UX Improvements v1.1.0
├─ Open: 8
├─ In Progress: 0
└─ Done: 0
```

### Progress Checklist

Track completion:

```
Phase 1: Quick Wins
- [ ] Issue #3 - Fix oversized icons (ETA: 1-2h)
- [ ] Issue #6 - Force dark mode (ETA: 30m)

Phase 2: Foundation
- [ ] Issue #2 - Tailwind CSS (ETA: 2-4h)
- [ ] Issue #1 - Auto-detection metadata (ETA: 4-6h)

Phase 3: Design System
- [ ] Issue #4 - VisiQuate branding (ETA: 4-6h)
- [ ] Issue #5 - Layout redesign (ETA: 6-8h)

Phase 4: Polish
- [ ] Issue #7 - HTML report enhancement (ETA: 4-6h)
- [ ] Issue #8 - Auto-detection tests (ETA: 4-6h)

Total Estimated Effort: 31-44 hours
```

## Slack/Communication Template

When announcing issues:

```
🚀 Starting UI/UX Improvements Phase

We're making 8 targeted improvements to data-profiler:

Quick Wins 🎯
- Issue #3: Reduce oversized icons
- Issue #6: Force dark mode

Foundation 🏗️
- Issue #2: Fix Tailwind CSS utilities
- Issue #1: Auto-detection metadata

Design System 🎨
- Issue #4: VisiQuate branding
- Issue #5: Layout redesign

Polish ✨
- Issue #7: HTML report data
- Issue #8: Auto-detection tests

See GITHUB_ISSUES.md for details.
Start with Phase 1 (quick wins) for immediate impact.
```

## Code Review Checklist for Issues

When reviewing PR that addresses an issue:

- [ ] All acceptance criteria met
- [ ] Tests pass (coverage maintained)
- [ ] Files match "Files Modified" list
- [ ] Code follows project standards
- [ ] No breaking changes
- [ ] Backward compatibility maintained
- [ ] Documentation updated
- [ ] PR references issue number
- [ ] Screenshots provided (if UI changes)
- [ ] Performance impact verified

## Troubleshooting

### Issue Can't Be Created
- Verify GitHub login
- Check repository permissions
- Try creating in browser, not CLI

### PR Won't Merge
- Ensure issue #N is closed in PR description
- Verify main branch protection rules pass
- Check CI/CD pipeline status
- Confirm reviewer approvals

### Auto-detection Tests Fail
- Check test file paths match project structure
- Verify golden files exist
- Run locally: `pytest api/tests/test_auto_detection.py -v`
- Check Python version (requires 3.10+)

## Additional Resources

- **Git Flow**: /git-workflow commands
- **Issue Details**: GITHUB_ISSUES.md
- **UI Design Guide**: UX_DESIGN_RECOMMENDATIONS.md
- **API Spec**: API.md
- **Data Model**: DATA_MODEL.md

---

**Last Updated**: 2025-11-14
**Version**: 1.0
**Maintained By**: Documentation Team
