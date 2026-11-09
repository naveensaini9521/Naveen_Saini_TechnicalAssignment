// Dynamic order builder.
// - Adds/removes item rows.
// - Fetches product price via data attributes (already rendered server-side).
// - Live-calculates amounts, subtotal, discount, grand total.
// - Client-side validation mirrors backend rules.

(function () {
  const body      = document.getElementById("items-body");
  const addBtn    = document.getElementById("add-row");
  const discountEl= document.getElementById("discount");
  const subtotalEl= document.getElementById("subtotal");
  const discEl    = document.getElementById("discount-amt");
  const grandEl   = document.getElementById("grand-total");
  const form      = document.getElementById("order-form");

  if (!body || !form) return;

  const money = (n) => n.toFixed(2);

  function recalc() {
    let subtotal = 0;
    body.querySelectorAll("tr").forEach(row => {
      const sel = row.querySelector(".product-select");
      const qty = parseInt(row.querySelector(".qty").value, 10);
      const price = parseFloat(sel?.selectedOptions[0]?.dataset.price || "0");
      const amount = (qty > 0 ? qty : 0) * price;

      const rateEl   = row.querySelector(".rate");
      const amountEl = row.querySelector(".amount");
      if (rateEl) rateEl.textContent = money(price);
      if (amountEl) amountEl.textContent = money(amount);
      subtotal += amount;
    });

    let pct = parseFloat(discountEl.value || "0");
    if (isNaN(pct) || pct < 0) pct = 0;
    if (pct > 20) pct = 20;

    const discAmt = subtotal * pct / 100;
    const grand   = subtotal - discAmt;

    subtotalEl.textContent = money(subtotal);
    discEl.textContent = money(discAmt);
    grandEl.innerHTML = "<strong>" + money(grand) + "</strong>";
  }

  function bindRow(row) {
    row.querySelector(".product-select").addEventListener("change", () => {
      // Enforce stock limit client-side
      const sel = row.querySelector(".product-select");
      const stock = parseInt(sel.selectedOptions[0]?.dataset.stock || "0", 10);
      const qtyEl = row.querySelector(".qty");
      qtyEl.max = stock;
      recalc();
    });
    row.querySelector(".qty").addEventListener("input", recalc);
    row.querySelector(".remove-row").addEventListener("click", () => {
      row.remove();
      if (body.querySelectorAll("tr").length === 0) addRow();
      recalc();
    });
  }

  function addRow() {
    const tpl = body.querySelector("tr");
    const clone = tpl.cloneNode(true);
    clone.querySelectorAll("select, input").forEach(el => {
      if (el.tagName === "SELECT") el.value = "";
      if (el.classList.contains("qty")) el.value = "1";
    });
    body.appendChild(clone);
    bindRow(clone);
    recalc();
  }

  addBtn.addEventListener("click", addRow);
  discountEl.addEventListener("input", recalc);
  body.querySelectorAll("tr").forEach(bindRow);

  // Prevent duplicate submit
  form.addEventListener("submit", (e) => {
    const btn = document.getElementById("save-btn");
    const rows = [...body.querySelectorAll("tr")];
    const validRows = rows.filter(r => {
      const pid = r.querySelector(".product-select")?.value;
      const qty = parseInt(r.querySelector(".qty")?.value, 10);
      return pid && qty > 0;
    });
    if (validRows.length === 0) {
      e.preventDefault();
      alert("Add at least one product with quantity > 0.");
      return;
    }
    if (new Set(rows.map(r => r.querySelector(".product-select")?.value)).size !== rows.length) {
      // duplicate products in the same order
      e.preventDefault();
      alert("Each product may appear only once.");
      return;
    }
    if (btn) { btn.disabled = true; btn.textContent = "Saving…"; }
  });

  // Initial calculation
  recalc();
})();