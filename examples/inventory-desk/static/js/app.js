"use strict";
const form = document.querySelector("#expense-form");
if (form) {
  const message = document.querySelector("#message");
  const money = cents => new Intl.NumberFormat("en-US", {style: "currency", currency: "USD"}).format(cents / 100);
  async function refresh() {
    const expenses = await NativeStore.invoke("list_expenses");
    document.querySelector("#total").textContent = money(expenses.reduce((sum, item) => sum + item.amount_cents, 0));
    document.querySelector("#count").textContent = expenses.length;
    document.querySelector("#empty").hidden = expenses.length > 0;
    const tbody = document.querySelector("#expenses");
    tbody.replaceChildren();
    expenses.forEach(item => {
      const row = document.createElement("tr");
      [item.description, item.category, money(item.amount_cents)].forEach(value => {
        const cell = document.createElement("td"); cell.textContent = value; row.append(cell);
      });
      const cell = document.createElement("td"), button = document.createElement("button");
      button.className = "delete"; button.textContent = "Delete";
      button.setAttribute("aria-label", `Delete ${item.description}`);
      button.addEventListener("click", async () => {
        try {await NativeStore.invoke("delete_expense", {expense_id: item.id}); await refresh();}
        catch (error) {message.textContent = error.message;}
      });
      cell.append(button); row.append(cell); tbody.append(row);
    });
  }
  form.addEventListener("submit", async event => {
    event.preventDefault(); const button = form.querySelector("button[type=submit]"); button.disabled = true;
    try {
      const data = new FormData(form);
      const amount = String(data.get("amount"));
      if (!/^\d+(?:\.\d{1,2})?$/.test(amount)) throw new Error("Use an amount with up to two decimal places.");
      const [whole, fraction = ""] = amount.split(".");
      const cents = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
      await NativeStore.invoke("add_expense", {description: data.get("description"), amount_cents: cents, category: data.get("category")});
      form.reset(); message.textContent = "Expense saved."; await refresh();
    } catch (error) {message.textContent = error.message;} finally {button.disabled = false;}
  });
  refresh().catch(error => {message.textContent = error.message;});
}
