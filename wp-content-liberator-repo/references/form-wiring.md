# Form wiring: homepage → contact handoff + n8n webhook

## The two-step funnel pattern

Common in WPConvert-derived themes (and funnel sites generally):

1. **Homepage has a short "quick-capture" form** — just name + email in a final CTA section
2. **Contact page has the full form** — name, email, phone, company, message, package selection
3. **User submits the homepage form** → redirects to contact page with name/email pre-filled → user sees less friction to complete the full form

Reduces drop-off because users feel "almost done" on the contact page.

## URL param handoff (simplest approach)

No backend needed between the two forms. The homepage form uses `method="get"` pointing at `/contact/`. The browser appends form fields as URL params. The contact page reads the params on load and pre-fills matching inputs.

### Homepage form

```html
<form action="<?php echo esc_url( home_url( '/contact' ) ); ?>" method="get">
    <input type="text" name="customer_name" placeholder="Your name">
    <input type="email" name="email" placeholder="your@email.com" required>
    <!-- Honeypot — bots fill every field; humans never see this -->
    <input type="text" name="website_url_hp" tabindex="-1" autocomplete="off"
           style="position:absolute;left:-9999px;top:auto;width:1px;height:1px;overflow:hidden"
           aria-hidden="true">
    <button type="submit">Book a Call</button>
</form>
```

Why `method="get"`: GET submissions append form fields to the URL. That IS the hand-off mechanism. POST wouldn't work because the contact page wouldn't see the values.

### Contact page prefill

Inline script right before `get_footer()`:

```html
<script>
(function () {
  'use strict';
  function init() {
    var form = document.getElementById('dabster-contact-form');
    if (!form) return;

    try {
      var params = new URLSearchParams(window.location.search);
      ['customer_name', 'email'].forEach(function (key) {
        var val = params.get(key);
        if (!val) return;
        var field = form.querySelector('[name="' + key + '"]');
        // Don't overwrite if user has already typed something
        if (field && !field.value) field.value = val;
      });
    } catch (e) { /* old browser without URLSearchParams */ }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
</script>
```

## Contact form → n8n webhook

The contact form needs to actually submit somewhere (n8n, Zapier, a CRM, etc.).

### Design decision: fetch() vs. native form POST

| Approach | Pros | Cons |
|---|---|---|
| **Native form POST** | No CORS. Works everywhere. n8n returns 302 redirect to thank-you or form-error. | User leaves the page mid-submit. No loading indicator unless you add JS. |
| **fetch() intercept** | Can show loading state, detect errors, keep user on page until resolution. | Requires CORS headers on n8n. Opaque responses (no-cors mode) can't detect failures. |

**Recommended: Native form POST.** Simpler, no CORS headaches, n8n handles the redirect. Use JS only for the submit-button disable to prevent double-clicks.

### Form markup

```php
<form id="dabster-contact-form"
      action="<?php echo esc_url( get_theme_mod( 'dabster_contact_webhook',
                                                  'https://n8n.example.com/webhook/dabster-contact' ) ); ?>"
      method="post">

    <input type="text" name="customer_name" required>
    <input type="email" name="email" required>
    <!-- ... other fields ... -->
    <textarea name="message"></textarea>

    <!-- Hidden fields: tell n8n where to redirect after processing.
         Using home_url() means this auto-adapts between staging and production. -->
    <input type="hidden" name="redirect_success"
           value="<?php echo esc_url( home_url( '/thank-you/' ) ); ?>">
    <input type="hidden" name="redirect_error"
           value="<?php echo esc_url( home_url( '/form-error/' ) ); ?>">

    <!-- Honeypot -->
    <input type="text" name="website_url_cf" tabindex="-1" autocomplete="off"
           style="position:absolute;left:-9999px;top:auto;width:1px;height:1px;overflow:hidden"
           aria-hidden="true">

    <button type="submit">Send message</button>
</form>
```

### Submit button UX

Inline script to disable the button during submit:

```html
<script>
(function () {
  var form = document.getElementById('dabster-contact-form');
  if (!form) return;
  form.addEventListener('submit', function () {
    var btn = form.querySelector('button[type="submit"]');
    if (btn) {
      btn.disabled = true;
      btn.style.opacity = '0.6';
      btn.style.cursor = 'wait';
    }
  });
})();
</script>
```

## n8n workflow expectations

The minimum n8n workflow:

```
[Webhook] → [Normalize Fields] → [Valid Submission?] → true  → [Respond Redirect: redirect_success]
                                                     → false → [Respond Redirect: redirect_error]
```

Key configuration:

1. **Webhook node** — accept POST, multipart/form-data
2. **Normalize Fields** — extract and clean fields from `$json.body.customer_name` etc.
3. **Valid Submission? (IF node)** — checks:
   - Required fields are non-empty
   - `website_url_cf` (honeypot) is empty — if ANY value, route to error (or drop silently)
   - Email format valid
4. **Respond Redirect (success)** — a "Respond to Webhook" node set to:
   - Response Code: `302`
   - Response Headers: `Location: {{ $('Webhook').item.json.body.redirect_success }}`
5. **Respond Redirect (error)** — same, but using `redirect_error`

## Environment portability

By sending `redirect_success` and `redirect_error` as hidden form fields (generated via `home_url()`), your n8n workflow doesn't need environment-specific configuration. The form tells n8n where to redirect based on which site is sending the submission.

This means:
- Staging sends `https://example.com/wpstage2/thank-you/`
- Production sends `https://example.com/thank-you/`
- The n8n workflow is identical in both cases

If the n8n node config hardcodes URLs instead of reading from the submitted form, you'll have to update n8n at every environment change. Don't do that.

## Anti-spam: honeypot

The hidden `website_url_*` field:

- Positioned off-screen via inline CSS (`left: -9999px`)
- `tabindex="-1"` so keyboard users can't focus it
- `autocomplete="off"` so browsers don't pre-fill it
- `aria-hidden="true"` so screen readers skip it

Humans never see it. Bots scrape the form HTML and fill every field they find, including this one. n8n's "Valid Submission?" node checks: if the honeypot has ANY value, reject the submission (either silently drop it, or redirect to a page that 200s but doesn't trigger your actual flow).

**Don't tell the bot the submission failed** — silent success is better. Failed submissions may retry with variations; successful-looking submissions don't.

## CORS notes (if you insist on fetch-based submission)

If you genuinely need JS-based submission (e.g., to display inline success without a page navigation):

1. Configure n8n to respond with CORS headers:
   ```
   Access-Control-Allow-Origin: https://your-domain.com
   Access-Control-Allow-Methods: POST, OPTIONS
   Access-Control-Allow-Headers: Content-Type
   ```
   Add via Webhook node → Options → Response Headers, OR via a "Respond to Webhook" node at the end of the workflow.

2. Use `mode: 'cors'` in fetch — then you can read the response status and decide success/error.

3. If CORS setup is out of your control, fall back to `mode: 'no-cors'` — the request fires but you can never detect failure. Assume success and redirect to thank-you. Monitor n8n uptime externally.

### Common CORS failure pattern

User submits → data reaches n8n → browser can't read response because of CORS → JS catch block fires → user redirected to form-error page. But the lead actually DID arrive. Confusing for both user and developer.

If you see this pattern ("form looked like it failed but the lead is in the CRM"), that's CORS. The native-form-POST approach above avoids it entirely.

## Proxy through WordPress (bulletproof but more work)

If you need full reliability regardless of n8n's CORS config, add a custom WP REST endpoint that receives the form server-side and forwards to n8n:

```php
add_action( 'rest_api_init', function () {
    register_rest_route( 'dabster/v1', '/contact', [
        'methods'  => 'POST',
        'callback' => function ( $request ) {
            $data = $request->get_params();
            if ( ! empty( $data['website_url_cf'] ) ) {
                return new WP_REST_Response( [ 'ok' => true ], 200 ); // silent honeypot
            }
            $response = wp_remote_post( get_theme_mod( 'dabster_contact_webhook' ), [
                'body' => $data,
                'timeout' => 10,
            ] );
            if ( is_wp_error( $response ) ) {
                return new WP_REST_Response( [ 'ok' => false ], 500 );
            }
            return new WP_REST_Response( [ 'ok' => true ], 200 );
        },
        'permission_callback' => '__return_true',
    ] );
} );
```

Form action becomes `/wp-json/dabster/v1/contact` (same origin, no CORS). The PHP endpoint hits n8n server-to-server (no CORS). Use this only when native form POST isn't an option.
