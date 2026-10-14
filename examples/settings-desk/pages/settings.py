import json
from nativestore import FormResult


def page(ctx):
    path = ctx.data_dir / "preferences.json"
    settings = json.loads(path.read_text()) if path.is_file() else {"display_name": ""}
    return ctx.render("pages/Settings.html", form=FormResult(values=settings))
