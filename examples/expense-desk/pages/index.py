def page(ctx):
    return ctx.render("pages/Index.html", title=ctx.app.config.title)
