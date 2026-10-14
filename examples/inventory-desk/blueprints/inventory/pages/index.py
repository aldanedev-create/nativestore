from ..services import Inventory
from nativestore import FormResult


def page(ctx):
    return ctx.render("Index.html", items=Inventory(ctx.data_dir).list(), form=FormResult())
