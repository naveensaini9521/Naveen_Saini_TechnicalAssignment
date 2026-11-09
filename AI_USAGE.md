# AI Usage Disclosure (Part 14)

## Tools Used

- **ChatGPT / Claude (Anthropic)** — assisted with scaffolding, boilerplate, and reviewing edge cases.

## Usage

AI assistance was used for:

- Generating the initial Flask app factory, extensions file, and route blueprint skeletons.
- Drafting SQLAlchemy model classes from the schema in Part 3 of the assignment.
- Generating repetitive test scaffolding for the Part 12 scenarios.
- Reviewing the concurrency approach for order confirmation (`SELECT ... FOR UPDATE`).
- Drafting the README structure and this disclosure.

The author reviewed and understands every line of submitted code and made all design decisions:

- Choice of Flask-SQLAlchemy for ORM, PyMySQL for the MySQL driver.
- `schema.sql` instead of Alembic (justified — Part 3 explicitly allows `schema.sql`).
- Decimal-based money math with `ROUND_HALF_UP`.
- `SELECT ... FOR UPDATE` for confirm/cancel transactions.
- Model / service / route separation.
- Use of `extract()` instead of MySQL `YEAR()` / `MONTH()` in Python code, so tests run on SQLite.

## Example Prompts

1. **Schema design**

   > "Given this assignment schema (Part 3) with users, customers, products, sales_orders, sales_order_items, stock_movements, generate SQLAlchemy model classes with proper `__tablename__`, unique constraints, `CheckConstraint`s, `Enum` columns, and `db.Numeric` for money. Use Flask-SQLAlchemy."

2. **Concurrency**

   > "How do I make the confirm-order step idempotent and safe under concurrent confirmation of the same product? Give me a pattern using `SELECT ... FOR UPDATE` inside a single transaction with SQLAlchemy, and explain why this prevents overselling."

3. **Testing**

   > "Generate pytest tests for an order service that cover: multi-item with discount, insufficient stock rolls back entirely, repeated confirm is idempotent, cancel of confirmed restores stock once, and sales users cannot access another user's orders."

## Review

- All AI-generated code was read line by line, run locally, and covered by automated tests (`pytest -v` — all tests pass).
- Money math was cross-checked against the worked example on page 8 of the assignment (subtotal 4500, discount 450, grand total 4050).
- Schema was cross-checked against `sql/schema.sql` to ensure models and DB agree on `DECIMAL(10,2)`, `ENUM`s, and FK `ON DELETE RESTRICT` behaviour.

## Corrections / Limitations

- **AI initially suggested `YEAR()` / `MONTH()` in the monthly-sales ORM query.** This breaks when tests run against SQLite. Corrected to use SQLAlchemy `extract()`, which compiles per-dialect. The MySQL-native `YEAR()` / `MONTH()` SQL was kept only in `sql/required_queries.sql` for the standalone deliverable.
- **AI's initial `_pagination.html` used `**dict_unpack`inside a Jinja`url_for()`.\*\* Jinja does not support that syntax. Corrected to rebuild the query string manually in the template.
- **AI placed a password in the `config.py` fallback string.** Rejected — credentials must live only in `.env`. Kept `config.py` password-less; `.env.example` contains placeholders only.
- **AI's `low_stock_report` assumed `to_int` returned a `(value, err)` tuple.** `to_int` in `helpers.py` raises instead. Replaced with an inline try/except in `low_stock_report`.
