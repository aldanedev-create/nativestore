# JinjaX integration

The dependency is **jinjax**, not jinax. NativeStore uses its real Catalog adapter
with `file_ext=".html"`, `add_folder` and `render`. A custom Jinja environment enables
HTML escaping and StrictUndefined. Rendering is serialized around each catalog to
avoid interleaved asset collection. Template values are escaped unless explicitly
marked trusted HTML.

```html
{#def title #}
<Layout title={{ title }}>
  <h1>{{ title }}</h1>
</Layout>
```

Layout.html declares `{#def title #}` and inserts `{{ content }}`. These are JinjaX
components and content composition, not a second template language. NativeStore renders
`pages/Index.html` as the component `pages.Index`.

Use `/static/` URLs for local application assets, and include
`/__nativestore/bridge.js` before application JavaScript. NativeStore serves co-located component CSS/JS through /static/components/.
Use JinjaX catalog.render_assets() to emit the collected external asset tags.
Template source and other file extensions cannot be requested through that asset route. The CSP
requires external scripts/styles. Alpine support uses its CSP build; normal Alpine
expression evaluation would require loosening CSP and is not the default.

Public API reference: https://jinjax.scaletti.dev/api/
