from nativestore import App, Field, Form

app = App(title='Angular Desk', name='angular-desk')

@app.page("/greet", method="POST")
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


if __name__ == "__main__":
    app.run()
