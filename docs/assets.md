# Frontend libraries

The shipped reviewed registry pins htmx 2.0.4, Alpine CSP 3.14.8, and Lucide 0.468.0.
These are intentional compatibility pins, not a claim to be the newest releases.
Files were retrieved from version-specific jsDelivr npm URLs and their exact bytes
SHA-256 hashed when the registry was prepared. Hashes are pinned in the shipped
registry, not trusted from the same response as each install. This verifies byte
consistency; it is not a signature from the upstream authors.

`add`, `remove`, `list`, and `update` manage static/vendor and nativestore.lock.
Downloads use approved HTTPS URLs, restricted redirects, a timeout, size limit,
verified content-addressed cache, and atomic file replacement. No JavaScript is
executed during installation. Offline add needs a populated verified cache.
Build verifies locked installed assets; it does not download missing ones automatically.

Scripts are optional. To use HTMX add:
```html
<script defer src="/static/vendor/htmx.js"></script>
```
Use alpine.js or lucide.js analogously. POST APIs must send JSON and an Origin header;
Ordinary page handlers accept URL-encoded forms as well as JSON, including HTMX form
submissions. The command bridge remains JSON-only. No automatic script injection is provided.
License metadata and links accompany each registry entry; retain upstream notices
when redistributing. See THIRD_PARTY_NOTICES.md.

Update resolves the newest *approved* version in this registry. Arbitrary versions
fail clearly. Registry updates require maintainers to inspect source/license and
pin new bytes; automatic trust-on-first-use from user version strings is not supported.
Asset changes use cross-process OS-backed project locks. Failed lock-file writes restore
the previous asset bytes. Cache and installed bytes are checked before trust.
