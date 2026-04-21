# wp-content-liberator

A Claude skill for **liberating content from hardcoded WordPress themes** — whether they came from React-to-WP converters like WPConvert, static HTML imports, page builders the owner wants to escape, or hand-coded themes that were never made editable.

Turns a site where content lives in PHP template files into a **Customizer-editable, form-functional** WordPress site — using only WP core. No paid plugins. No SaaS subscriptions. No page builders.

## What's inside

```
wp-content-liberator/
├── SKILL.md                                 # main skill document
├── references/
│   ├── bulletproof-overrides.md             # inline wp_head CSS pattern for cascade wars
│   ├── customizer-refactor.md               # hardcoded → Customizer-editable conversion
│   ├── form-wiring.md                       # homepage→contact handoff + n8n webhook
│   └── common-bugs.md                       # 9 specific bug signatures with fixes
└── scripts/
    └── check_balance.py                     # PHP brace balance checker for safe edits
```

## Who this is for

You're a developer or agency who's ended up with a WordPress site where:

- Most content is hardcoded in `.php` template files instead of posts/Customizer
- A converter (WPConvert, React-to-WP, static-to-WP) generated the theme
- A page builder (Elementor, Divi, Bricks) locked content into proprietary structures
- The previous developer never wired up Customizer fields
- The client can't edit copy without a developer

The skill encodes patterns that actually work on these themes — especially the cascade-conflict and generator-JS quirks that trip up normal WordPress workflows.

## What problems it solves

### Cascade chaos
Converter-generated themes enqueue multiple stylesheets whose load order is unpredictable. A CSS rule wins on one page and loses on another. `!important` alone won't save you. The skill documents the inline `wp_head` priority 9999 pattern.

### Generator JS fighting native HTML
Converters bundle generic accordion/nav/tab handlers designed for Radix/MUI/Bootstrap. They hijack your native `<details>`, `<summary>`, `<button>` elements. The skill documents the DABSTER OVERRIDE guard pattern.

### Content in the DB, not the template
Menu items have classes in post_meta. Customizer values live in wp_options. Post-migration URL leakage persists. The skill shows when to search-replace the DB and when to edit templates.

### Dead forms
Homepage forms with `action=""` that submit nowhere. Contact forms with broken webhook wiring. CORS errors that make successful submissions look like failures. The skill provides the full URL-param-handoff + native-POST-to-n8n pattern, environment-portable via `home_url()`.

## How to use

### As a Claude skill (recommended)

Claude.ai supports skills — instructions loaded into context when matching work comes up.

1. Download `wp-content-liberator.skill` from the [Releases page](../../releases) (or package it yourself with `skill-creator`)
2. In Claude Desktop/mobile, go to **Settings → Capabilities → Skills** and upload
3. Start a conversation mentioning your trapped-content WordPress site — Claude will consult the skill automatically

### As a reference (no Claude needed)

Clone the repo and read the markdown files. They stand alone as technical documentation.

```bash
git clone https://github.com/<your-username>/wp-content-liberator.git
cd wp-content-liberator
less SKILL.md
less references/bulletproof-overrides.md
```

The `scripts/check_balance.py` is a standalone tool you can use to validate PHP files before/after edits:

```bash
python3 scripts/check_balance.py path/to/functions.php -2 0 0
```

## Core concepts in 60 seconds

### The bulletproof override pattern

When your CSS loses to a later-loaded stylesheet and `!important` isn't enough, inject the rules inline in the page `<head>` at `wp_head` priority 9999. Inline `<style>` in `<head>` always wins over external stylesheets regardless of their load order:

```php
add_action( 'wp_head', function () {
    ?>
<style id="my-critical-overrides">
@media (max-width: 768px) {
  ul.nav-links { /* rules that must win */ }
}
</style>
    <?php
}, 9999 );
```

### The Customizer refactor pattern

Use theme mods + Customizer sections for every hardcoded string. Naming convention:
`<theme_prefix>_<page>_<section>_<field>` (e.g., `dabster_home_hero_heading`).

Registration:
```php
$wp_customize->add_setting( 'dabster_home_hero_heading', [
    'default'           => 'Automate more. Build faster.',
    'sanitize_callback' => 'sanitize_text_field',
] );
```

Template:
```php
<h1><?php echo esc_html( get_theme_mod( 'dabster_home_hero_heading', 'Automate more. Build faster.' ) ); ?></h1>
```

### The form handoff pattern

Homepage form uses `method="get" action="/contact"` — browser auto-appends name/email as URL params. Contact page reads `URLSearchParams` and prefills. Contact form POSTs natively to n8n with hidden `redirect_success`/`redirect_error` fields generated by `home_url()` so redirects work in any environment.

## Who wrote this?

This skill emerged from a real project — rescuing a WPConvert-generated theme for Dabster Labs (AI automation agency in Cyprus & Greece). Every pattern documented here was learned by hitting the bug in production, diagnosing it, and finding a fix that actually worked across page templates, browsers, and environments.

## Contributing

If you use this skill and find patterns that helped, or bugs the skill doesn't yet cover — open an issue or PR. The more real-world scenarios in `references/common-bugs.md`, the more useful this gets.

Good PRs:
- New entries in `references/common-bugs.md` — format: symptom, root cause, fix, verification
- Improvements to the Customizer refactor workflow for specific page types
- Alternative form-wiring recipes (Zapier, Make.com, custom REST endpoints)
- Clarity/prose improvements to existing references

Avoid PRs that:
- Add dependencies on paid plugins or SaaS tools (that's the point — liberation)
- Bundle large PHP snippets that do many things at once (surgical edits win)

## License

MIT. See [LICENSE](LICENSE).

## See also

- [Claude skills documentation](https://docs.claude.com/en/docs/build-with-claude/skills)
- [WordPress Customizer API](https://developer.wordpress.org/themes/customize-api/)
- [Better Search Replace plugin](https://wordpress.org/plugins/better-search-replace/) — free, trusted tool for DB URL migrations
