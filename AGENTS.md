# AGENTS.md

Instructions for AI coding agents working in this repository.

## This is the DEV repo

| Repo | Role | Edit it? |
|------|------|----------|
| `adamjs83/creston-xsig-hassio` (this repo) | Development: all code, branches, PRs, CI, notes | **Yes — all work happens here** |
| `adamjs83/crestron-xsig-hassio` | Public HACS repo users install from | **Never edit directly** |

- The public repo is **publish-only**. Every release replaces its whole tree with a
  snapshot from this repo, so any direct change there is lost on the next release.
- Never clone, branch, commit, or open PRs against the public repo.
- User-facing URLs (manifest `documentation`/`issue_tracker`, README, info.md,
  blueprints) point at the **public** repo. Keep it that way.

## What gets published

- Only paths listed in `.publish-include` are published. Everything else (tests,
  `pyproject.toml`, `ci.yml`, `RELEASE.md`, this file, notes) stays private.
- Only git-tracked files are exported (`git archive`), so untracked/ignored files never leak.
- Markdown between `<!-- dev-only:start -->` and `<!-- dev-only:end -->` is stripped on
  publish. Use it for dev-only notes inside published files (e.g. the README "moved" banner).
- Adding a new top-level file or directory that users need? Add it to `.publish-include`.
- Never commit secrets. The publish workflow runs gitleaks on the published tree and fails
  the release if it finds one.

## Releasing

Pushing a `vX.Y.Z` tag runs `.github/workflows/publish-public.yml`, which commits the
snapshot to the public repo as one `Release vX.Y.Z` commit, tags it, and creates the
GitHub release there (notes come from `CHANGELOG.md`).

Before tagging, in one PR:
1. Bump `version` in `custom_components/crestron/manifest.json` (must equal the tag minus `v`).
2. Bump the `Version` badge under the title in `README.md`.
3. Add `## [X.Y.Z] - YYYY-MM-DD` to the top of the root `CHANGELOG.md`.

Rules:
- Never re-use a version that already exists on the public repo; the workflow refuses it.
- Do not push tags yourself unless the user asks. Tagging is the release trigger.
- Pre-release tags (`-alpha`, `-beta`, `-rc`) are published as GitHub pre-releases.

Full details: `RELEASE.md`.

## Community contributions

Issues and PRs arrive on the **public** repo. To take a PR:
1. Work in this repo on a branch.
2. Apply the patch: `curl -L https://github.com/adamjs83/crestron-xsig-hassio/pull/N.patch | git am`
3. PR here, release as normal, then close the public PR referencing the release.

## Project layout

- `custom_components/crestron/` — the integration (domain `crestron`).
  - `config_flow.py` — thin entry point; hassfest **requires** this file to exist.
  - `flow_handlers/` — actual config/options flow implementation. Do not rename it to
    `config_flow/`: a package with that name shadows `config_flow.py` and breaks hassfest.
  - `strings.json` and `translations/en.json` — keep in sync when adding flow text.
  - `brand/` — `icon.png` (256px) and `icon@2x.png` (512px) for HACS/HA.
- `blueprints/` — automation blueprints (published).
- `tests/` — pytest suite (not published).

## Checks before pushing

```bash
ruff check custom_components/crestron/
ruff format --check custom_components/crestron/
pytest tests/ -q          # needs: pip install pytest pytest-asyncio homeassistant
```

CI (`ci.yml`) runs lint + tests; `validate.yml` runs hassfest and HACS validation.
All must be green before merge. Ruff config (line length 120, py311) is in `pyproject.toml`.
