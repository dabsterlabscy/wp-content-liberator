# Changelog

All notable changes to the `wp-content-liberator` skill will be documented in this file.

## [1.0.0] — 2026-04-21

Initial public release.

### Added
- `SKILL.md` — Main skill document covering identification, gotchas, and 7-step liberation workflow
- `references/bulletproof-overrides.md` — Inline `wp_head` priority 9999 CSS injection pattern
- `references/customizer-refactor.md` — Pattern for converting hardcoded templates to Customizer-editable fields
- `references/form-wiring.md` — Native-POST forms to n8n webhooks with environment portability
- `references/common-bugs.md` — Nine documented bug signatures with root causes and fixes
- `scripts/check_balance.py` — PHP brace-balance validator aware of strings and comments

### Known limitations
- Targets WPConvert-style themes most precisely; other generators may need heuristic adjustments
- No automated tests yet (skill-creator eval suite is the next improvement)
- Bug catalog is specific to the debugging experience on one production site — broader coverage welcome via PRs
