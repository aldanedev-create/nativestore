# Reusable blueprints

A Blueprint is trusted application code bundling Python handlers/services, JinjaX
components and local assets. It reuses NativeStore's router/server/bridge and is not
a sandbox. Small apps do not need blueprints.

```python
# blueprints/inventory/__init__.py
from nativestore import Blueprint
blueprint = Blueprint(name='inventory', root=__file__, defaults={'currency': 'USD'})

@blueprint.command()
def greet(name: str) -> str:
    return f'Hello, {name}'
```

```python
# main.py
from blueprints.inventory import blueprint
app.mount_blueprint(blueprint, prefix='/inventory', config={'currency': 'JMD'})
```

Pages and api folders use the normal file routing conventions. Commands become
`inventory.greet`. Templates are registered under the `inventory:` JinjaX namespace;
`ctx.render('Index.html')` automatically selects that namespace. Use
`<inventory:ItemCard />` from outside the feature. Blueprint templates can reuse the
application's Layout component. Context includes immutable top-level `config`, the mount
`prefix`, `blueprint_prefix` template input, and `static_url` (`/static/blueprints/inventory`).
Declare template inputs using JinjaX's `{#def ... #}` syntax. Build action URLs using
blueprint_prefix so the feature remains mountable under a different prefix.

Duplicate blueprint names, colliding routes, adapter overlaps and native capabilities
not explicitly enabled by the application are rejected. Configuration merges declared
defaults with mount overrides. `@blueprint.startup` and `@blueprint.shutdown` functions
receive `(app, config)`; application close invokes shutdown in reverse registration
order. Mounting failure rolls back routes/commands and attempts feature cleanup.

Local `blueprints/` source and resources are included in installer staging; Python files
are discovered for hidden imports. Keep service code under the package and use relative
imports. Do not hide feature resources in arbitrary external directories. Third-party
installed blueprint distributions must ship their resources and configure the build's
hidden_imports/extra_resources explicitly; automatic installed-package discovery and
resource collection are not advertised.

See examples/inventory-desk for SQLite, validation, namespaced templates, HTMX forms,
and tests. Native feature behavior still requires native platform acceptance tests.
