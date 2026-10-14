from nativestore import FormResult
from ...services import Inventory

method = "POST"


def handler(ctx):
    service = Inventory(ctx.data_dir)
    service.delete(int(ctx.params["id"]))
    return ctx.render("List.html" if ctx.is_htmx else "Index.html", items=service.list(), form=FormResult())
