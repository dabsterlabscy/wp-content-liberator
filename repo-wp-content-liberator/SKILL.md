---
name: wp-content-liberator
description: "Take a WordPress site whose content is trapped in hardcoded template files — from a React-to-WP converter (like WPConvert), a static HTML import wrapped in PHP, a page-builder theme the user wants to escape, or a hand-coded theme that was never made editable — and turn it into a Customizer-editable, form-functional site without paid plugins, SaaS subscriptions, or page builders. Trigger when a user says \"my WP site has hardcoded content\", \"I want this editable without Elementor/Divi\", \"WPConvert generated my theme and I can't edit from admin\", \"how do I wire this form without a subscription\", or describes symptoms of trapped content: multiple stylesheets fighting each other, inline styles that won't yield to CSS, duplicate menus/accordions, post-migration URL leakage. Trigger proactively when the theme has data-wpc-id attributes, a large inline JS blob in functions.php, or multiple anonymous-hash CSS files — all markers of generated, uneditable themes."
---

# WordPress Content Liberator

A field guide for taking a WordPress site whose content is locked inside PHP template files and giving its owner real control — using only WordPress core (Customizer, nav menus, theme mods) and plain PHP/CSS/JS. No paid plugins. No SaaS page builders. No subscriptions.

## When this skill applies

The user has a WordPress theme and any of these is true:

- Most or all visible text/images/links live inside `.php` files, not in wp_posts or Customizer
- The theme was generated from a React/Vite build via a converter (WPConvert, Create React App export, custom build scripts)
- The theme was imported from a static HTML site with minimal WP integration
- A page builder (Elementor, Divi, Beaver, Bricks) locked the content into proprietary data structures
- A developer hand-coded the theme but never wired up Customizer fields
- The user wants to "escape" a builder and own their site without ongoing license fees

Common phrases that signal this skill:

- "I can't edit anything from WordPress admin"
- "The content is hardcoded"
- "How do I make this editable without [SaaS tool]?"
- "I need to give this to a non-technical client"
- "Moving off Elementor / off Divi / off Webflow"
- "The previous developer didn't set up Customizer"

## What "liberation" means here

Three outcomes to aim for:

1. **Content-editable.** Every piece of copy, every image, every CTA label can be changed from **Appearance → Customize** by someone who doesn't know PHP. Defaults preserve the current look, so users who don't edit see no change.

2. **Form-functional.** Contact forms, newsletter signups, quote requests submit to a real endpoint the user controls (their own n8n, their own WordPress REST endpoint, a webhook to their CRM). No dependency on Formidable, WPForms, Gravity Forms subscriptions, or "forms-as-a-service" providers.

3. **Migration-portable.** The theme uses `home_url()` everywhere, form action URLs auto-adapt to staging/production, n8n workflows read redirect targets from the form rather than hardcoding. Moving the site between environments is a database search-replace away, not a code rewrite.

The user gets a site their kids could edit. You get a theme that won't rot when a SaaS plan gets cancelled.

## The three big gotchas in generated/imported themes

Before you change anything, understand these. Most "liberation" work is just applying one of the three patterns below.

### Gotcha 1: Cascade chaos from multiple stylesheets

Converter-generated themes typically enqueue 3–5 CSS files — root `style.css`, `assets/css/style.css`, one or more `index-[hash].css` bundles. Their load order depends on WordPress's dependency resolution, which can reshuffle between page templates. Result: a rule that wins on one page loses on another, and `!important` alone won't save you.

**The fix: inline critical CSS in `wp_head` at priority 9999.** Inline `<style>` in `<head>` beats every external stylesheet regardless of order. See `references/bulletproof-overrides.md` for the full pattern including JS fallbacks for modern-selector edge cases.

### Gotcha 2: Leftover JS from the generator fighting your HTML

Converters bundle generic handlers for Radix, Material UI, Bootstrap, etc. When your native `<details>`, `<summary>`, `<button>`, or menu element matches those handlers' selectors, it gets hijacked — you see inline styles appearing, toggles breaking, elements flickering. The JS was never meant for native HTML.

**The fix: early-exit guards.** Add `if (el.closest('.your-namespace').length) return;` at the top of each offending handler. Mark guards with a unique comment tag (`// [PROJECT] OVERRIDE:`) so you can find them later.

### Gotcha 3: Stored data in post_meta or the database, not the template

Menu items have classes stored in `_original_classes` post_meta. Customizer values live in `wp_options`. Forms carry hardcoded URLs that survived the "move to production" step. When something won't change despite your code edits, the code isn't the source — the database is.

**The fix: search-replace the database.** Install "Better Search Replace" (free, no subscription), run dry runs, then real passes. Check post_meta for menu-item stored classes if nav layout is stuck. See `references/common-bugs.md` for specific recipes.

## The liberation workflow

When a user asks you to "make this editable", work in this order:

### Step 1: Identify what you're working with

```bash
cd <theme-dir>

# Generator signatures
grep -l "data-wpc-id\|data-wpconvert-\|data-builder-" *.php | head
grep -l "WPCONVERT_JS\|WPCONVERT\|WPConvert_" functions.php | head

# How many stylesheets?
ls assets/css/*.css 2>/dev/null | wc -l
find . -name "*.css" -not -path "./node_modules/*" | wc -l

# Hardcoded content indicators
grep -rn "<h1\|<h2\|<p>" --include="*.php" page-*.php front-page.php 2>/dev/null | wc -l

# Existing editability
grep -rn "get_theme_mod\|customize_register" functions.php | wc -l

# Enqueued stylesheets (to understand cascade)
grep -n "wp_enqueue_style" functions.php | head
```

Write the findings down. A "10-enqueued-stylesheets + 3000-line functions.php + zero customize_register calls" theme is a bigger job than a "1 stylesheet + 1 customize_register call + mostly-clean functions.php" theme.

### Step 2: Baseline the PHP state

Any PHP file you edit needs a balance check before AND after. Use the included script:

```bash
python3 <skill-path>/scripts/check_balance.py <theme-dir>/functions.php
```

Many generated themes have non-zero baselines (WPConvert is typically `-2/0/0`). Whatever baseline the file starts with is what you must preserve. If it changes after an edit, you introduced a syntax error — revert.

### Step 3: Plan the refactor before touching the template

For each page the user wants editable:

1. Open the template file (e.g., `front-page.php`, `page-about.php`)
2. List every hardcoded string meant for humans (headings, body, button labels, prices, quotes, etc.). Image URLs too if they'll be editable.
3. Group by semantic section (Hero, Features, Pricing, Testimonials, FAQ, Final CTA).
4. Name the fields: `<prefix>_<page>_<section>_<field>`. Example: `dabster_home_hero_heading`.

Don't edit yet. Write the field list first. A home page typically yields 30–60 fields. A spartan About page: 10. A services page with 6 services: 50–80.

See `references/customizer-refactor.md` for the registration + template-rewrite patterns.

### Step 4: Register Customizer fields, rewrite the template

Register all fields for one page in a single `<prefix>_customize_<page>()` function. Hook it into `customize_register`. Use the "$add helper" pattern to reduce boilerplate.

Then rewrite the template, replacing each hardcoded string with `get_theme_mod( 'field_id', 'original_hardcoded_value' )`. Keep the original text as the default — that way, if the user deletes a value, they fall back to the original content rather than a blank page.

### Step 5: Fix cascade conflicts (if any)

If your CSS changes don't "stick" across all pages, move the critical rules to inline `wp_head` at priority 9999. See `references/bulletproof-overrides.md`.

### Step 6: Wire the forms

Replace empty form actions (`<form action="" method="post">`) with real destinations. For a multi-step funnel (homepage form → contact page → n8n), use the URL-param handoff pattern. For contact-to-CRM, use native POST with `home_url()`-generated redirect fields so n8n can redirect correctly in any environment. See `references/form-wiring.md`.

### Step 7: Validate, version, build, hand over

```bash
# Balance must still match baseline
python3 <skill-path>/scripts/check_balance.py <theme-dir>/functions.php

# Bump Version: line in style.css
# Use semver: patch for fixes, minor for features, major for breaking

# Build zip
cd <theme-parent>
zip -rq /out/<theme-name>.zip <theme-name>
unzip -p /out/<theme-name>.zip <theme-name>/style.css | grep "^Version:"

# Present to user with deploy instructions
```

Always tell the user:
- Which version they're getting
- To clear cache or use private-browser mode (cache is the #1 "your fix didn't work" cause)
- What specifically to click to verify

## Anti-patterns — what NOT to do

These are shortcuts that create bigger problems:

- **Don't install a page builder to "fix" a hardcoded theme.** That just trades one lock-in for another, often paid.
- **Don't pile on `!important` in a stylesheet that's losing the cascade.** Figure out WHY it's losing (usually: wrong file). More `!important` on the same losing file doesn't help.
- **Don't use `wp_die()` or custom form handlers when `wp_nav_menu`/`get_theme_mod`/native forms work.** WordPress core is the goal.
- **Don't rewrite `functions.php` top-to-bottom.** Surgical edits with `str_replace`. You'll need to see your specific change when something breaks.
- **Don't edit files inside a page builder's output.** If the user wants off Elementor, migrate content out first via content export + manual rebuild. Editing Elementor's serialized post_meta ends in tears.

## Communication patterns that work

- **Announce risk.** "This is a low-risk CSS change" vs. "This touches functions.php — I'll verify the brace balance before sending."
- **Show diagnostics from the user's tools.** If they bring DevTools output, ChatGPT output, Google AI Console output — take it seriously. Verify claims against the code, then act. External tools often catch what you miss.
- **Version every build.** "Deploy this" without "this is v2.x.y" makes cache-debugging impossible.
- **Don't bundle unrelated fixes.** When chasing a hard bug across multiple rounds, change one thing per version. Your goal is to minimize variables, not maximize delivery.
- **Admit when you're guessing.** "I think X is the cause but I'm not certain — let's test before committing to the fix."

## What this skill does NOT cover

- Building the original React/HTML source (that's upstream work)
- WordPress multisite, WP-CLI administration, server configuration
- Payment processing integration (Stripe, PayPal) — beyond form-wiring
- Custom post types or complex taxonomies (use WP docs)
- Block editor / Gutenberg patterns — the skill uses Customizer precisely because the content lives in templates, not posts
- Performance optimization beyond basics (separate concern; use WP Rocket / LiteSpeed Cache)

## References

- `references/bulletproof-overrides.md` — Inline CSS in `wp_head` priority 9999 pattern, when and how to use it, JS fallbacks for older browsers
- `references/customizer-refactor.md` — Converting hardcoded page templates into Customizer-editable fields; naming conventions, escaping rules, time estimates, common mistakes
- `references/form-wiring.md` — Homepage → contact handoff via URL params, contact → n8n webhook, environment-portable redirects, CORS handling, honeypot anti-spam, WordPress REST proxy fallback
- `references/common-bugs.md` — Specific bug signatures with root causes and fixes (FAQ accordion hijack, mobile nav phantom menu, pricing card contrast, footer column collapse, post-migration URL leakage, duplicate mobile CTAs, etc.)
- `scripts/check_balance.py` — PHP brace balance checker that respects strings and comments; use before/after every functions.php edit
