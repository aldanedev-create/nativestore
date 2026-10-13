def handler(ctx):
    result = ctx.app.invoke({"protocol": 1, "command": "list_expenses", "args": {}})
    return ctx.json(result["result"] if result["ok"] else result, 200 if result["ok"] else 500)
