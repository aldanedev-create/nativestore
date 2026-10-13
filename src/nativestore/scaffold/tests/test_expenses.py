from app.services import ExpenseService


def test_persistence_and_delete(tmp_path):
    database = tmp_path / "expenses.sqlite3"
    service = ExpenseService(database)
    identity = service.add("Bus fare", 250, "Transport")
    other = ExpenseService(database)
    assert other.list()[0]["amount_cents"] == 250
    assert other.delete(identity)
    assert other.list() == []
