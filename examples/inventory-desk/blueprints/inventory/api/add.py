from nativestore import Field, Form
from ..services import Inventory

method = "POST"


def handler(ctx):
    form = ctx.validate(Form(name=Field(min_length=1, max_length=80), quantity=Field(kind="integer", minimum=0)))
    service = Inventory(ctx.data_dir)
    if form.valid:
        service.add(form.data["name"], form.data["quantity"])
    return ctx.render("List.html" if ctx.is_htmx else "Index.html", items=service.list(), form=form, status=200 if form.valid else 422)
