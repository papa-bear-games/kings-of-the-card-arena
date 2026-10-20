# 0041. Open the free web game only from scottcoxdev.com

- **Status:** Accepted
- **Date:** 2026-10-15

## Context

Scottie is making a separate, paid Android version of the game in its own repo. The web version
stays free, as a portfolio piece reached from his developer site, https://scottcoxdev.com. He asked
that it only open for people who come from that site.

## Decision

On the live host (`play.scottcoxdev.com`), `wwwroot/js/gate.js` runs before Blazor starts
(`autostart="false"`, started by `js/start.js`). It starts the game when the visitor arrived from
`scottcoxdev.com` or any of its subdomains (by `document.referrer`), and remembers that in
`localStorage`, so refreshes and return visits work. Anyone else sees a short page with a button to
https://scottcoxdev.com/. Pages that emails link to (confirm email, reset and forgot password) and
the privacy, terms and status pages always open. Local runs, PR previews, staging and the browser
tests use other hosts and are not gated.

Alongside it: `X-Robots-Tag: noindex` asks search engines not to list the game's pages, the
existing `frame-ancestors 'none'` keeps other sites from framing it, and the API's CORS list
(`Cors:AllowedOrigins`) already answers only the game's own pages.

## Alternatives considered

- A signed, short-lived launch link minted by scottcoxdev.com: harder to get around, but it needs a
  shared secret and code in both sites, and a shared link still works until it expires. Too much for
  a free game.
- Checking the referrer at the edge: Azure Static Web Apps can't route on the `Referer` header.

## Consequences

The check runs in the browser, so it stops casual visits and copycat links, not a determined person
(the referrer can be faked, or the API called directly as before). Links to the game from GitHub or
elsewhere land on the gate page, so the ReadMe and case study link to scottcoxdev.com instead.
Browsers that send no referrer, or block storage, see the gate until they come in from the site.
