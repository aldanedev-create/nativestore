"""Generate UI choices without changing the shared Python backend."""

import json
from pathlib import Path

from .assets import Assets
from .errors import NativeStoreError

UI_CHOICES = ("angular", "minimal", "htmx", "alpine", "htmx-alpine", "expense")


def configure(root: Path, ui: str) -> None:
    if ui not in UI_CHOICES:
        raise NativeStoreError("Unknown UI starter")
    if ui == "expense":
        return
    for name in ("htmx", "alpine"):
        if name in ui:
            Assets(root).add(name)
    (root / "templates/Layout.html").write_text("""{#def title #}
<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title><link rel="stylesheet" href="/static/css/app.css">
<ns:Assets /></head><body><main>{{ content }}</main></body></html>
""")
    (root / "pages/index.py").write_text("""def page(ctx):
    return ctx.render("pages/Index.html")
""")
    (root / "pages/settings.py").write_text("""def page(ctx):
    return ctx.render("pages/Settings.html", title="Settings")
""")
    (root / "templates/pages/Settings.html").write_text("""{#def title #}
<Layout title={{ title }}><h1>{{ title }}</h1><a href="/">Home</a></Layout>
""")
    greeting = """<form method="POST" action="/greet" {htmx}>
<ns:Field name="name" label="Your name" required={{ True }} />
<button type="submit">Say hello</button></form><div id="greeting" aria-live="polite"></div>"""
    greeting = greeting.replace(
        "{htmx}", 'hx-post="/greet" hx-target="#greeting"' if "htmx" in ui else ""
    )
    if "alpine" in ui:
        greeting = '<ns:Dropdown label="Greeting form">' + greeting + "</ns:Dropdown>"
    if ui == "angular":
        greeting = '<ns-greeting ngCspNonce="{{ nativestore_nonce }}"></ns-greeting>'
        angular(root)
    (root / "templates/pages/Index.html").write_text(
        '{#def nativestore_nonce #}\n<Layout title="Welcome to NativeStore"><h1>Welcome to NativeStore</h1>'
        "<p>Python business logic, JinjaX components, and a Tauri desktop window.</p>"
        + greeting
        + '<p><a href="/settings">Settings</a></p></Layout>\n'
    )
    (root / "templates/Greeting.html").write_text("""{#def form, message="" #}
{% if message %}<ns:Alert message={{ message }} />{% endif %}
{% if form.errors %}<p role="status">{{ form.errors.get('name', '') }}</p>{% endif %}
""")
    (root / "templates/GreetingPage.html").write_text("""{#def form, message="" #}
<Layout title="Greeting"><Greeting form={{ form }} message={{ message }} /><a href="/">Go back</a></Layout>
""")
    entry = root / "main.py"
    title = root.name.replace("-", " ").title()
    config = root / "nativestore.toml"
    config.write_text(config.read_text().replace("Expense Desk", title))
    for relative in ("api/expenses.py", "app/services.py", "tests/test_expenses.py"):
        (root / relative).unlink(missing_ok=True)
    original = f'from nativestore import App\n\napp = App(title={title!r}, name={root.name!r})\n\nif __name__ == "__main__":\n    app.run()\n'
    original = original.replace(
        "from nativestore import App", "from nativestore import App, Field, Form"
    )
    original = original.replace(
        'if __name__ == "__main__":',
        """@app.page("/greet", method="POST")
def greet(ctx):
    result = ctx.validate(Form(name=Field(min_length=1, max_length=80)))
    message = f"Hello, {result.data['name']}!" if result.valid else ""
    template = "Greeting.html" if ctx.is_htmx else "GreetingPage.html"
    return ctx.render(template, form=result, message=message, status=200 if result.valid else 422)


@app.command()
def greet_person(name: str) -> dict[str, str]:
    result = Form(name=Field(min_length=1, max_length=80)).validate({"name": [name]})
    if not result.valid:
        raise ValueError("Enter a name between 1 and 80 characters")
    return {"message": f"Hello, {result.data['name']}!"}


if __name__ == "__main__":""",
    )
    entry.write_text(original)
    (root / "tests/test_pages.py").write_text("""from nativestore.loader import load_app
from nativestore.testing import TestClient
from pathlib import Path


def test_starter():
    with load_app(Path(__file__).resolve().parents[1]) as app:
        client = TestClient(app)
        assert client.get("/").status == 200
        assert "Welcome to NativeStore" in client.get("/").body
        assert client.post("/greet", form={"name": "Ada"}).status == 200
        assert client.post("/greet", form={"name": ""}).status == 422
""")
    (root / "README.md").write_text(
        f"# NativeStore {ui} starter\n\nRun `nativestore dev` for a native window or "
        "`nativestore dev --browser` for browser debugging. Run `nativestore test`.\n"
        + (
            "\nAngular needs Node.js 24 LTS: `cd frontend`, `npm ci`, then return here. "
            "`nativestore dev` and `build` compile Angular automatically. End users need no Node.js.\n"
            if ui == "angular"
            else "\nPython/JinjaX handles forms; HTMX and Alpine are optional.\n"
        )
    )


def angular(root: Path) -> None:
    frontend = root / "frontend"
    (frontend / "src").mkdir(parents=True)
    package = {
        "name": "nativestore-angular-ui",
        "version": "0.1.0",
        "private": True,
        "scripts": {"build": "ng build", "watch": "ng build --watch"},
        "dependencies": {
            "@angular/core": "22.2.2",
            "@angular/common": "22.2.2",
            "@angular/platform-browser": "22.2.2",
            "rxjs": "7.8.2",
            "tslib": "2.8.1",
        },
        "devDependencies": {
            "@angular/build": "22.2.2",
            "@angular/cli": "22.2.2",
            "@angular/compiler": "22.2.2",
            "@angular/compiler-cli": "22.2.2",
            "typescript": "~6.0.0",
        },
    }
    (frontend / "package.json").write_text(json.dumps(package, indent=2) + "\n")
    (frontend / "angular.json").write_text(
        json.dumps(
            {
                "version": 1,
                "projects": {
                    "ui": {
                        "projectType": "application",
                        "root": "",
                        "sourceRoot": "src",
                        "architect": {
                            "build": {
                                "builder": "@angular/build:application",
                                "options": {
                                    "browser": "src/main.ts",
                                    "tsConfig": "tsconfig.json",
                                    "index": False,
                                    "outputPath": "../static/angular",
                                    "outputHashing": "none",
                                    "aot": True,
                                    "optimization": {
                                        "scripts": True,
                                        "styles": {"minify": True, "inlineCritical": False},
                                        "fonts": False,
                                    },
                                },
                            }
                        },
                    }
                },
            },
            indent=2,
        )
    )
    (frontend / "tsconfig.json").write_text(
        json.dumps(
            {
                "compilerOptions": {
                    "target": "ES2022",
                    "module": "preserve",
                    "moduleResolution": "bundler",
                    "experimentalDecorators": True,
                    "strict": True,
                    "skipLibCheck": True,
                    "lib": ["ES2022", "DOM"],
                },
                "angularCompilerOptions": {"strictTemplates": True},
                "files": ["src/main.ts"],
            },
            indent=2,
        )
    )
    (frontend / "src/main.ts").write_text("""import { Component, signal } from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';

declare global {
  interface Window { NativeStore: { invoke<T>(name: string, args: Record<string, unknown>): Promise<T> }; }
}

@Component({
  selector: 'ns-greeting',
  standalone: true,
  template: `<label for="angular-name">Your name</label>
    <input id="angular-name" #name maxlength="80">
    <button type="button" (click)="greet(name.value)" [disabled]="busy()">Say hello</button>
    <p aria-live="polite">{{ message() }}</p>`
})
class Greeting {
  message = signal('');
  busy = signal(false);
  async greet(name: string) {
    this.busy.set(true);
    try {
      const result = await window.NativeStore.invoke<{message: string}>('greet_person', {name});
      this.message.set(result.message);
    } catch {
      this.message.set('Enter a name between 1 and 80 characters.');
    } finally { this.busy.set(false); }
  }
}
bootstrapApplication(Greeting).catch(console.error);
""")
    lock = Path(__file__).with_name("angular-package-lock.json")
    if lock.is_file():
        (frontend / "package-lock.json").write_bytes(lock.read_bytes())
