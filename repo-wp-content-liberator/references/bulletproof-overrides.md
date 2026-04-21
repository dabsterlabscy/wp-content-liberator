# Bulletproof CSS overrides in WPConvert themes

## The problem

WPConvert themes enqueue multiple stylesheets whose load order cannot be guaranteed:

- `wpconvert-style` (root `style.css`)
- `wpconvert-site-styles` (`assets/css/style.css`, depends on wpconvert-style)
- `wpconvert-asset-index-*-css` (other files from `assets/css/`, alphabetical order, also depend on wpconvert-style)

Because the `assets/css/*` files only declare `wpconvert-style` as a dependency (not each other), WordPress can output them in any order at runtime — and this order may differ between page templates.

Consequence: if `front-page.php` and `page-pricing.php` cause different enqueue orderings, the same CSS rule might win on one page and lose on the other. Users see "it works on Home but breaks on Pricing" and vice versa.

**No amount of `!important` in a stylesheet can reliably beat this**, because a later-loaded stylesheet's non-`!important` rule still loses to an earlier-loaded `!important` rule — BUT two `!important` rules at tied specificity go to last-loaded. Since you can't predict last-loaded, you can't predict the winner.

## The solution: inline CSS in wp_head priority 9999

An inline `<style>` block emitted directly in `<head>` always loads after every `<link rel="stylesheet">` tag. WordPress's `wp_head` action runs before `</head>` closes; by registering at priority 9999 you ensure your inline CSS is among the very last things written.

Inline CSS rules with `!important` at the same specificity beat external stylesheets' `!important` rules with the same specificity, because they are "last in source order."

## The pattern

Add this to `functions.php` at the end (or wherever is conventional in the theme):

```php
/**
 * Critical CSS overrides that must win across every page template.
 * Injected inline at wp_head priority 9999 — after all enqueued stylesheets.
 */
function <prefix>_critical_css_override() {
    ?>
<style id="<prefix>-critical-overrides">
/* Rules go here. Use !important where needed. These rules beat any
   external stylesheet because inline <style> in <head> is last in source order. */

.my-component {
  background: #hexvalue !important;
  color: #hexvalue !important;
}

@media (max-width: 768px) {
  .mobile-scoped-override {
    display: none !important;
  }
}
</style>
    <?php
}
add_action( 'wp_head', '<prefix>_critical_css_override', 9999 );
```

Replace `<prefix>` with a theme-specific identifier (e.g., `dabster`, `acme`). The ID on the `<style>` element makes it easy to find in DevTools.

## When to use this pattern

Reach for the inline override when:

- A CSS change must work identically on every page template
- You've already tried editing the relevant stylesheet and it works on some pages but not others
- Multiple `!important` rules are competing and you can't trace which one wins
- You need to defeat an inline-style attribute added by a WPConvert JS handler (combine with the DABSTER OVERRIDE JS pattern for belt-and-braces)

Do NOT use this pattern for:

- Normal cosmetic work that fits in the theme's stylesheet with no cascade conflict
- Rules specific to one page template (put those in the relevant template's `<style>` block or a page-specific stylesheet)
- Large blocks of CSS (inline CSS is bytes the browser must parse before first paint — keep it focused)

## Combining with JS fallback

Some selectors (like `:has()`) have limited older-browser support. If a critical rule uses modern CSS features, add a JavaScript fallback in the same `wp_head` function:

```php
function <prefix>_critical_css_override() {
    ?>
<style id="<prefix>-critical-overrides">
/* ...CSS rules including :has()... */
</style>
<script>
/* JS fallback: match elements and apply styles imperatively for older browsers. */
(function () {
  function apply() {
    /* selector logic that doesn't use :has() */
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', apply);
  } else {
    apply();
  }
  window.addEventListener('resize', apply);
})();
</script>
    <?php
}
```

## Practical example: hiding a duplicate mobile CTA

Real case from the Dabster Labs project. A nav CTA `<li>` was appended to `<ul class="nav-links">` via `items_wrap`. On mobile, the nav slides down as an accordion, and having the CTA inside it duplicated the one in the sticky top bar. The fix:

```php
function dabster_critical_css_override() {
    ?>
<style id="dabster-critical-overrides">
@media (max-width: 768px) {
  ul.nav-links > li.nav-cta-item,
  ul.nav-links > li:has(a.nav-cta),
  ul.nav-links > li.ml-2 {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
  }
}
</style>
<script>
/* Fallback for browsers without :has() support */
(function () {
  function hideNavCtaOnMobile() {
    if (window.matchMedia && !window.matchMedia('(max-width: 768px)').matches) return;
    var cta = document.querySelector('ul.nav-links > li.nav-cta-item') ||
              document.querySelector('ul.nav-links > li.ml-2') ||
              (function () {
                var links = document.querySelectorAll('ul.nav-links > li > a');
                for (var i = 0; i < links.length; i++) {
                  if (links[i].textContent.trim().toLowerCase() === 'book a call') {
                    return links[i].parentElement;
                  }
                }
                return null;
              })();
    if (cta) cta.style.cssText = 'display:none !important;visibility:hidden !important;';
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', hideNavCtaOnMobile);
  } else {
    hideNavCtaOnMobile();
  }
  window.addEventListener('resize', hideNavCtaOnMobile);
})();
</script>
    <?php
}
add_action( 'wp_head', 'dabster_critical_css_override', 9999 );
```

Layered defense: CSS for modern browsers (with `:has()`), JS fallback with 3 selector strategies for older ones, and `display: none` supplemented by multiple collapse properties in case one property is overridden.

## Why not just dequeue the competing stylesheets?

Tempting, but risky. The `assets/css/index-*.css` files are WPConvert's bundled Tailwind utilities and base styles — dequeuing them breaks a huge amount of layout and typography. The inline override pattern lets you win specific battles without losing the war.

If you genuinely need to dequeue a stylesheet, do it from a `wp_enqueue_scripts` action with priority 100+ using `wp_dequeue_style( 'handle-name' )`, and test every page template exhaustively afterward.
