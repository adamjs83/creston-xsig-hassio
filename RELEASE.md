# Release Process

This document describes the automated release process for the Crestron XSIG Integration.

## Overview

This project uses automated releases via GitHub Actions (`.github/workflows/release.yml`). The automation is triggered when a git tag matching `v*` is pushed to the repository.

## Semantic Versioning

Follow semantic versioning: **MAJOR.MINOR.PATCH**

- **MAJOR**: Breaking changes (e.g., 2.0.0)
- **MINOR**: New features, backward compatible (e.g., 1.10.0)
- **PATCH**: Bug fixes, backward compatible (e.g., 1.9.8)
- **Pre-release**: alpha, beta, rc suffixes (e.g., 1.8.0-alpha.1)

## Required Files for Each Release

**⚠️ CRITICAL**: Every release MUST update these 3 files before tagging:

### 1. README.md
Update version badge on line 3:
```markdown
[![Version](https://img.shields.io/badge/version-X.Y.Z-blue.svg)](https://github.com/adamjs83/creston-xsig-hassio/releases)
```

### 2. custom_components/crestron/manifest.json
Update version on line 4:
```json
{
  "domain": "crestron",
  "name": "Crestron XSIG Integration",
  "version": "X.Y.Z",
  ...
}
```

**⚠️ CRITICAL**: The automation validates this matches the git tag. If there's a mismatch, the release will FAIL.

### 3. CHANGELOG.md
Add new version section at the top:
```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features and capabilities

### Changed
- Changes to existing functionality

### Fixed
- Bug fixes

### Technical Details
- Implementation notes
- Architecture changes
```

## Release Automation Workflow

When you push a tag matching `v*`, the GitHub Actions workflow:

1. **Validates** manifest.json version matches tag version
2. **Extracts** changelog entry for this version from CHANGELOG.md
3. **Creates** GitHub release with:
   - Release notes from CHANGELOG.md
   - Installation instructions (HACS and manual)
   - Links to documentation
   - Pre-release flag (for alpha/beta/rc versions)

**If manifest.json version doesn't match tag → Release FAILS** ❌

## Complete Release Process

Follow this exact sequence for every release:

### Step 1: Make Code Changes
```bash
# Edit files as needed
# Test thoroughly with Home Assistant
```

### Step 2: Update Version Files (ALL 3 REQUIRED)
```bash
# Edit README.md - update version badge
# Edit custom_components/crestron/manifest.json - update version
# Edit CHANGELOG.md - add new version section with date and changes
```

### Step 3: Stage and Commit
```bash
git add <modified_files>
git add README.md
git add custom_components/crestron/manifest.json
git add CHANGELOG.md

git commit -m "feat: descriptive title (vX.Y.Z)

Detailed description of changes made.

Features:
- List of new features
- Each on its own line

Implementation:
- Technical details
- Files modified

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 4: Create and Push Tag
```bash
# Create tag (MUST match manifest.json version exactly!)
git tag vX.Y.Z

# Push commit and tags
git push
git push --tags
```

### Step 5: Verify Automation
- GitHub Actions will trigger automatically
- Check workflow: https://github.com/adamjs83/creston-xsig-hassio/actions
- Release appears: https://github.com/adamjs83/creston-xsig-hassio/releases
- Should complete in ~2-3 minutes

## Commit Message Format

### Standard Format
```
type: brief description (vX.Y.Z)

Detailed description...

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Commit Types
- `feat`: New feature (e.g., "feat: add UI configuration for sensors")
- `fix`: Bug fix (e.g., "fix: keep hub running during reload")
- `docs`: Documentation only
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code restructure (no feature/fix)
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

## Fixing a Failed Release

If you forgot to update a file (e.g., manifest.json):

```bash
# Add the missing files
git add custom_components/crestron/manifest.json CHANGELOG.md

# Amend the commit (keeps same message)
git commit --amend --no-edit

# Delete old tag locally and remotely
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z

# Re-create tag and force push
git tag vX.Y.Z
git push --force
git push --tags
```

The automation will trigger again with the corrected files.

## Pre-release Versions

For alpha, beta, or release candidate versions:

1. Use version format: `X.Y.Z-alpha.N`, `X.Y.Z-beta.N`, or `X.Y.Z-rc.N`
2. Update all 3 files (README.md, manifest.json, CHANGELOG.md)
3. Tag as: `vX.Y.Z-alpha.N`
4. The automation will mark it as a "Pre-release" on GitHub

## Checklist

Before creating a release, verify:

- [ ] All code changes are tested
- [ ] README.md version badge updated
- [ ] manifest.json version updated
- [ ] CHANGELOG.md has entry for this version with date
- [ ] manifest.json version matches intended tag exactly
- [ ] Commit message follows format
- [ ] Ready to push tag

## Troubleshooting

### "Release validation failed: version mismatch"
- Check that manifest.json version matches the git tag (without 'v' prefix)
- Tag: `v1.10.0` → manifest.json: `"version": "1.10.0"`

### "No changelog found for version X.Y.Z"
- Verify CHANGELOG.md has a section: `## [X.Y.Z] - YYYY-MM-DD`
- Check formatting matches exactly (with square brackets)

### Automation didn't trigger
- Verify tag was pushed: `git push --tags`
- Check GitHub Actions tab for workflow runs
- Ensure tag format matches `v*` pattern

## Additional Resources

- GitHub Actions Workflow: `.github/workflows/release.yml`
- CHANGELOG format: https://keepachangelog.com/
- Semantic Versioning: https://semver.org/
