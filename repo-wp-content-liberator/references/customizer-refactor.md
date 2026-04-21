# Customizer refactor pattern

## Goal

Convert hardcoded markup (headings, body copy, button labels, prices, testimonial quotes, etc.) in a WPConvert theme's page templates into fields editable from **Appearance → Customize** in WP Admin.

## Why not the block editor?

WPConvert themes use template files (e.g., `front-page.php`, `page-pricing.php`) that hardcode content directly. Converting each page to Gutenberg blocks would require:

1. Creating a block pattern per section
2. Migrating existing content into block posts
3. Retraining the user on block editing

The Customizer is a better fit because:

- It preserves the visual template structure (no layout shifts from the user editing raw HTML)
- Changes are immediately previewable in the Customizer live preview
- Non-technical users can edit copy without touching markup
- Fields can have validation, defaults, and type coercion

## Naming convention

Use a three-part snake_case identifier:

```
<theme_prefix>_<page>_<field>
```

Examples:

- `dabster_home_hero_heading`
- `dabster_home_hero_subheading`
- `dabster_home_final_cta_button`
- `dabster_pricing_faq_q1`
- `dabster_pricing_faq_a1`
- `dabster_about_mission_paragraph`

This pattern keeps related fields sorted together in the wp_options table, makes it easy to grep all fields for a given page, and avoids name collisions between pages.

## Registration pattern

Each page gets its own `dabster_customize_<page>()` function, all hooked into `customize_register`.

```php
function dabster_customize_home_page( $wp_customize ) {

    // Helper to add text field quickly (reduces ceremony)
    $add = function( $id, $default, $label, $section, $type = 'text' ) use ( $wp_customize ) {
        $wp_customize->add_setting( $id, [
            'default'           => $default,
            'transport'         => 'refresh',  // or 'postMessage' for live preview
            'sanitize_callback' => $type === 'textarea' ? 'sanitize_textarea_field' : 'sanitize_text_field',
        ] );
        $wp_customize->add_control( $id, [
            'label'   => $label,
            'section' => $section,
            'type'    => $type,
        ] );
    };

    // Section: Home > Hero
    $wp_customize->add_section( 'dabster_home_hero', [
        'title'    => 'Home — Hero',
        'priority' => 30,
    ] );

    $add( 'dabster_home_hero_heading',
          'Automate more. Build faster.',
          'Main heading',
          'dabster_home_hero' );

    $add( 'dabster_home_hero_subheading',
          'AI automation for SMBs in Cyprus & Greece.',
          'Subheading',
          'dabster_home_hero',
          'textarea' );

    // Section: Home > Final CTA
    $wp_customize->add_section( 'dabster_home_final_cta', [
        'title'    => 'Home — Final CTA',
        'priority' => 50,
    ] );

    $add( 'dabster_home_final_cta_button',
          'Book Discovery Call',
          'Button label',
          'dabster_home_final_cta' );
}
add_action( 'customize_register', 'dabster_customize_home_page' );
```

## Template usage

In the page template (e.g., `front-page.php`), pull values with `get_theme_mod()`. Use the same default as in registration so the field is "seeded" even before the user edits.

```php
<?php
$hero_heading    = get_theme_mod( 'dabster_home_hero_heading', 'Automate more. Build faster.' );
$hero_subheading = get_theme_mod( 'dabster_home_hero_subheading', 'AI automation for SMBs in Cyprus & Greece.' );
$cta_label       = get_theme_mod( 'dabster_home_final_cta_button', 'Book Discovery Call' );
?>

<h1><?php echo esc_html( $hero_heading ); ?></h1>
<p><?php echo esc_html( $hero_subheading ); ?></p>

<button><?php echo esc_html( $cta_label ); ?></button>
```

## Escaping rules

Pick the right escaper based on field content type:

| Field content | Escaper |
|---|---|
| Plain text (headings, labels, prices) | `esc_html()` |
| URLs | `esc_url()` |
| HTML attributes | `esc_attr()` |
| Rich text with allowed tags (paragraphs, emphasis, links) | `wp_kses_post()` |
| Raw HTML (dangerous — avoid unless you control the input) | No escaping (but sanitize on save) |

For rich text fields, pair a `wp_kses_post` sanitization callback with `wp_kses_post` output escaping:

```php
$wp_customize->add_setting( 'dabster_home_hero_body', [
    'default'           => 'Default rich text...',
    'sanitize_callback' => 'wp_kses_post',
] );
```

```php
echo wp_kses_post( get_theme_mod( 'dabster_home_hero_body', 'Default...' ) );
```

## Field types

Common ones:

- **text** — single-line input (headings, labels)
- **textarea** — multi-line (body copy, quotes)
- **select** — with `choices` array (enum-like fields)
- **url** — validated URL input
- **checkbox** — boolean
- **color** — WP color picker
- **image** — `WP_Customize_Image_Control` (more boilerplate — see WP docs)

For select:

```php
$wp_customize->add_control( 'dabster_pricing_featured_tier', [
    'label'   => 'Which tier is featured',
    'section' => 'dabster_pricing_general',
    'type'    => 'select',
    'choices' => [
        'starter' => 'Starter',
        'growth'  => 'Growth',
        'premium' => 'Premium',
    ],
] );
```

## Refactor workflow

When the user asks to make a page editable:

1. **Read the template file.** Identify every piece of hardcoded human-readable text. Write down the list — it will be long (a home page might have 40+ fields).

2. **Group by semantic section.** Hero, features, pricing, testimonials, FAQ, final CTA, etc. Each section becomes a Customizer Section.

3. **Write the `dabster_customize_<page>()` function first.** Get the full field list registered before touching the template. Don't go back and forth.

4. **Run Customizer** (mental check via the code — or ask user to visit Appearance → Customize after deploy) and confirm sections appear with all fields and correct defaults.

5. **Update the template**, one section at a time. Pull values at the top of the section, then inline them in the markup. Keep the original hardcoded text as the `get_theme_mod()` default — that way if a user deletes a value, they get the original content back instead of blank space.

6. **Verify the rendered page still looks identical** before any user has made changes. The whole point of the refactor is zero visual change until the user deliberately edits.

## Common mistakes

- **Forgetting the `default` in `get_theme_mod()`.** If the setting hasn't been saved, `get_theme_mod($id)` returns `false`. `esc_html(false)` is empty string. Your page suddenly has missing content. Always pass the same default in both registration AND retrieval.

- **Using `get_option()` instead of `get_theme_mod()`.** Theme mods are scoped to the active theme; options are global. For theme-specific content, always use theme_mod.

- **Skipping `sanitize_callback`.** Without one, WordPress stores the raw input. Even for plain text fields, `sanitize_text_field` prevents accidental HTML injection.

- **Not escaping on output.** Even if the input was sanitized on save, always escape on output — it's a defense-in-depth practice, and it means the template code is safe even if someone later removes the sanitize callback.

- **Registering too many top-level Sections.** 5+ top-level sections per page is hard to navigate. Group related fields into fewer sections with clearer labels, or use `add_panel()` to create a collapsible parent (e.g., "Home Page" panel contains Hero, Features, CTA sections).

## Estimating effort

Rough rule of thumb for a WPConvert page with ~50 hardcoded strings:

- Reading/cataloging: 30 min
- Writing registration function: 45 min (or less with the `$add` helper)
- Refactoring template: 60–90 min
- Testing: 30 min
- **Total: 2–3 hours per page**

A sparse page (about, thank-you) takes 30 min. A dense page (services with 6 services × features each) can take 4+ hours.
