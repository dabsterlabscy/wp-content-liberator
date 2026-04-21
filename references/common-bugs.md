# Common WPConvert theme bugs — signatures and fixes

A catalog of specific bugs encountered in WPConvert-generated themes, with their distinctive signatures and proven fixes. Use this as a lookup when a user reports symptoms that sound familiar.

## 1. FAQ accordion toggles once then breaks

### Symptom

Native `<details>/<summary>` FAQ items: first tap works, second tap does nothing. Or, page loads with some items visible and others hidden in a seemingly random state. DevTools shows inline `height: 0px; opacity: 0` on the questions, but only on some of them.

### Root cause

The `WPCONVERT_JS` inline block (in functions.php, huge heredoc with tag `<<<'WPCONVERT_JS'`) contains a jQuery accordion handler bound to `summary` elements, plus a plain-JS scanner that iterates every `<details>` on the page and appends its own `+` icon while applying inline height/opacity styles for "smooth" animation.

When your FAQ uses native `<details>`, this handler hijacks it and fights the browser's native toggle behavior. On page load, it "primes" the first few items with `height: 0; opacity: 0` but fails to complete the full pass, leaving a mixed state.

### Fix

Add an early-exit guard at the top of each offending handler:

```javascript
$(document).on("click", "button[aria-controls], ..., summary", function(e) {
    var $trigger = $(this);
    // DABSTER OVERRIDE: Skip our own native <details> accordions.
    if ($trigger.closest(".dabster-faq-item, .dabster-footer-col").length) {
        return; // Let the browser handle the toggle natively
    }
    // ... original handler code ...
});
```

Three handlers typically need guarding:

1. jQuery `.on("click", "...selector list...summary")` handler
2. CSS max-height accordion handler (`$(document).on("click", "button")`)
3. The `wpconvert_accordion_enqueue` → `EC-ACCORDION-007` block that scans `document.querySelectorAll('details')`

Search for these patterns: `grep -n "EC-ACCORDION\|summary.*click\|querySelectorAll.*details" functions.php`

### Verification

After deploying, tap an FAQ item. It should open instantly on first tap, close cleanly on second tap, with no inline styles leaking in. DevTools on the `<details>` should show only the `open` attribute, no inline `style=""`.

## 2. Mobile nav phantom menu

### Symptom

Tap the hamburger (☰) on mobile. Expected: side/slide menu appears. Actual: a second nav bar appears below the sticky top tab, showing nav items inline. Sometimes you see BOTH a proper side menu AND the inline one. Tapping X once closes one; a second tap is needed for the other.

### Root cause

WPConvert leaves behind a complete secondary mobile nav system: `#wpconvert-mobile-nav` markup + its own backdrop + its own hamburger click handler. The JS attaches to any `<button>` that looks like a hamburger — including your custom one.

Result: your click opens YOUR menu, AND WPConvert's handler opens its phantom menu. Two menus, two close interactions needed.

### Fix (two parts)

**Part A: Make the WPConvert handler skip your hamburger:**

```javascript
// In the mobile nav click handler in functions.php
if ($btn.attr("onclick") && $btn.attr("onclick").indexOf("wpconvert-mobile-nav") !== -1) {
    return; // existing skip
}
// DABSTER OVERRIDE: Skip our clean in-header nav toggle.
if ($btn.attr("onclick") && $btn.attr("onclick").indexOf("nav-links") !== -1) {
    return;
}
if ($btn.hasClass("nav-toggle")) {
    return;
}
```

**Part B: Force-hide `#wpconvert-mobile-nav` via CSS** (since it's still in the DOM, anything could try to open it):

```css
#wpconvert-mobile-nav,
#wpconvert-mobile-nav.open,
#wpconvert-mobile-nav-backdrop {
    display: none !important;
    visibility: hidden !important;
    pointer-events: none !important;
}
body.mobile-nav-open {
    overflow: auto !important; /* undo scroll lock */
}
```

## 3. Mobile nav works on some pages but not others

### Symptom

The mobile slide-down menu works correctly on Home and About, but on Pricing, Services, or Contact it renders as inline horizontal items below the sticky nav.

### Root cause

WPConvert themes enqueue multiple CSS files from `assets/css/`. Their load order depends on WordPress's internal dependency resolution, which can vary by page template. On some pages your CSS override is the last loaded (wins); on others a WPConvert stylesheet loads later (loses).

### Fix

Move the critical CSS inline via `wp_head` at priority 9999. See `references/bulletproof-overrides.md` for the full pattern. Short version:

```php
add_action( 'wp_head', function () {
    ?>
<style id="dabster-critical-overrides">
@media (max-width: 768px) {
  nav.navbar ul.nav-links, ul.nav-links, ul#wpconvert-primary-ul.nav-links {
    position: fixed !important;
    top: 80px !important;
    transform: translateY(-120%) !important;
    /* ... full mobile accordion style ... */
  }
  ul.nav-links.nav-open { transform: translateY(0) !important; }
}
</style>
    <?php
}, 9999 );
```

Inline `<style>` in `<head>` beats all external stylesheets regardless of enqueue order.

## 4. Pricing card "featured" treatment is lavender instead of dark

### Symptom

The featured pricing card (usually the middle one, "Growth" / "Pro" / etc.) shows a light lavender background instead of the intended dark purple. Text is pale purple-on-purple, hard to read.

### Root cause

Usually a cascading conflict: your `.pricing-featured { background: dark-gradient }` rule loses to an earlier rule (sometimes a Tailwind utility class on the HTML element like `bg-brand-purple/20`, sometimes an inline `style=""` attribute from the original React output, sometimes a duplicate `.pricing-featured` declaration in a later-loaded CSS file).

### Fix

Use the bulletproof inline override (`wp_head` priority 9999). Include:

1. Background + gradient border on `.pricing-featured`
2. Override for any inline style: `div.pricing-featured[style*="background"] { background: dark-gradient !important; }`
3. Text color overrides for children using attribute selectors to catch all Tailwind variants:
   ```css
   .pricing-featured [class*="text-off-white"],
   .pricing-featured [class*="text-pure-white"],
   .pricing-featured [class*="text-muted-gray"] {
     color: #FFFFFF !important;
   }
   ```

Dark gradient recommendation: `linear-gradient(165deg, #2b1b4d 0%, #1a1030 50%, #0e0722 100%)` — looks rich, not flat, high contrast with white text.

## 5. Footer column layout broken on one page

### Symptom

Footer works as 4-column desktop layout on most pages, but on one specific page (e.g., Pricing) it renders as a "catalog" — column headings present, content underneath hidden/empty.

### Root cause

Footer columns use native `<details>` for mobile-collapse behavior. On desktop, CSS forces them visible via `display: block !important` on `:not(summary)` children. But browsers' native `<details>` hiding operates at a level CSS can't always override cleanly — and if the `<details>` renders in "closed" state, the CSS might not beat it reliably.

### Fix

Set `open` attribute on desktop via an inline script right after the `</footer>` tag in footer.php. Runs synchronously before first paint:

```html
<script>
(function () {
  try {
    var cols = document.querySelectorAll('details.dabster-footer-col');
    if (!cols.length) return;
    var mq = window.matchMedia('(min-width: 768px)');
    function sync() {
      for (var i = 0; i < cols.length; i++) {
        if (mq.matches) cols[i].setAttribute('open', '');
        else cols[i].removeAttribute('open');
      }
    }
    sync();
    if (mq.addEventListener) mq.addEventListener('change', sync);
    else if (mq.addListener) mq.addListener(sync);
  } catch (e) {}
})();
</script>
```

Desktop: all details get `open` attribute → content visible via native browser behavior, no CSS override battle.
Mobile: `open` attribute removed → user taps summary to toggle each section.

## 6. Contact form "submits successfully but user sees error page"

### Symptom

User fills out contact form, submits, lands on `/form-error/` page. You check n8n — the submission actually arrived. Lead is in your CRM. But the user thinks the form broke.

### Root cause

JS fetch-based submission with CORS blocking. The request fires, reaches n8n, n8n processes it correctly, BUT n8n's response lacks the `Access-Control-Allow-Origin` header. The browser blocks JS from reading the response. Your JS treats that as a failed request and redirects to form-error.

### Fix

Two options:

**Easy:** Switch to native form POST (remove the fetch intercept). n8n responds with HTTP 302 redirect to thank-you/form-error pages. No CORS involved. See `references/form-wiring.md` for the full pattern.

**If you must keep fetch():** Configure n8n to send CORS headers. In the Webhook node → Options → Response Headers:

```
Access-Control-Allow-Origin: https://your-domain.com
Access-Control-Allow-Methods: POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

## 7. Buttons redirect to `/wpstage2/` after site migration

### Symptom

Site was built on staging at `https://example.com/wpstage2/`, then moved to production at `https://example.com/`. Site mostly works, but some buttons and internal links still go to `/wpstage2/` URLs, 404ing.

### Root cause

Multiple possible sources:

1. **Theme has hardcoded `/wpstage2/` strings.** Usually not if the theme uses `home_url()` / `esc_url(home_url(...))` everywhere — but grep to confirm: `grep -rn "wpstage2" --include="*.php" --include="*.js" --include="*.css"`
2. **Database still has `/wpstage2/` URLs stored.** Customizer values, post content, menu URLs, serialized options.
3. **n8n workflow redirect nodes** have hardcoded `/wpstage2/thank-you/` URLs.

### Fix

If theme is clean (no hardcoded strings), the fix is database-only:

1. Back up the database (cPanel → phpMyAdmin → Export)
2. Install "Better Search Replace" plugin
3. Run passes:
   - `https://example.com/wpstage2` → `https://example.com` (all tables, dry run first)
   - `http://example.com/wpstage2` → `https://example.com`
   - `http://example.com` → `https://example.com` (to force HTTPS everywhere)
4. **Settings → Permalinks → Save** (regenerates .htaccess rewrite rules)
5. Clear caches

For n8n redirects, don't hardcode — have the form send `redirect_success` / `redirect_error` as hidden fields generated by `home_url()`, and configure n8n to use those values. See `references/form-wiring.md`.

## 8. "Book a Call" appears twice in mobile menu

### Symptom

On mobile, the sticky top bar shows the "Book a Call" CTA correctly. When user opens the slide-down nav menu, a second "Book a Call" appears at the bottom of the menu list — duplicated CTA.

### Root cause

The CTA `<li>` is appended to `<ul class="nav-links">` via `items_wrap` in the `wp_nav_menu()` call. That's correct for desktop (where the CTA sits inline on the right). On mobile it's visible inside the expanded accordion menu.

### Fix

Give the CTA `<li>` a distinct class, hide it via CSS on mobile:

**In header.php**, add `nav-cta-item` class:

```php
$nav_cta_li = '<li class="ml-2 nav-cta-item"><a href="..." class="nav-cta ...">Book a Call</a></li>';
```

**In critical CSS override** (wp_head 9999):

```css
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
```

Add a JS fallback for browsers without `:has()` support (older iOS/Android Safari) — iterate links, find one with text "book a call", hide its parent.

## 9. Homepage form submits but goes nowhere

### Symptom

Homepage has a "Ready to automate?" form with name + email. User fills it in, submits, the form reloads the page (or does nothing visible). No lead captured.

### Root cause

Default WPConvert markup has `<form action="" method="post">` — an empty action which POSTs back to the current page. WordPress has no handler for this, so the POST is silently dropped.

### Fix

Decide the hand-off destination, then change the form:

```html
<form action="<?php echo esc_url( home_url( '/contact' ) ); ?>" method="get">
```

`method="get"` means the name/email are passed as URL parameters, contact page pre-fills the full form from those params. See `references/form-wiring.md`.
