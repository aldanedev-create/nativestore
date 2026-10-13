from app.services import ExpenseService

from nativestore import App

app = App(title="Expense Desk", name="expense-desk")
service = ExpenseService(app.data_dir / "expenses.sqlite3")


@app.command()
def add_expense(description: str, amount_cents: int, category: str = "Other") -> dict[str, int]:
    return {"id": service.add(description, amount_cents, category)}


@app.command()
def list_expenses() -> list[dict[str, str | int]]:
    return service.list()


@app.command()
def delete_expense(expense_id: int) -> dict[str, bool]:
    return {"deleted": service.delete(expense_id)}


if __name__ == "__main__":
    app.run()
