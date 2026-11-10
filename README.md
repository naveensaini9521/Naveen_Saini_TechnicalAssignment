# Sales Order & Inventory Management

A small trading company's web application for managing customers, products, sales orders and stock — replacing spreadsheets with a proper database.

Built for the Savyant Systems Fresher / Trainee Software Developer assignment.

---

## Stack

| Layer    | Technology                              |
| -------- | --------------------------------------- |
| Backend  | Python 3.11+ / Flask 3.0                |
| Database | MySQL 8.0.16+                           |
| ORM      | Flask-SQLAlchemy 3.1                    |
| Frontend | HTML / CSS / vanilla JavaScript         |
| Auth     | Flask-Login + Werkzeug password hashing |
| Tests    | pytest 8                                |

---

## Features

- **Auth** — login/logout; Admin and Sales User roles enforced server-side.
- **Customers** — CRUD, search, active/inactive filter, safe-delete.
- **Products** — CRUD, search, unique code, non-negative price/stock, safe-delete.
- **Sales Orders** — multi-item Draft orders, backend totals, discount 0–20%, rate frozen at creation, duplicate product rejected.
- **Order lifecycle** — Draft → Confirmed → Cancelled, transactional and concurrency-safe.
- **Inventory** — Admin stock adjustments with mandatory reason + movement record.
- **Reports** — Customer Sales, Product Sales, Low Stock, Stock Movement History + 5 standalone SQL queries.
- **CSV Import** — Admin-only, all-or-nothing, row-level errors, opening stock as movements.
- **REST API** — `/api/products`, `/api/orders`, `/api/orders/{id}`, `/api/orders/{id}/confirm`, `/api/orders/{id}/cancel`.

---

## How to Start the Project (from a fresh clone)

### Prerequisites

- Python 3.11+
- MySQL 8.0.16+

### Step 1 — Clone and install

```bash
git clone https://github.com/naveensaini9521/sales-inventory-management.git
cd sales-inventory-management
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2 — Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
SECRET_KEY=<paste a long random string>
FLASK_DEBUG=1
DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/sales_inventory
```

Generate a strong `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Step 3 — Create the database

```bash
mysql -u root -p < sql/schema.sql
```

### Step 4 — Seed sample data

```bash
python scripts/seed.py
```

### Step 5 — Run

```bash
python run.py
```

Open <http://localhost:5000>

### Sample accounts

| Role       | Email             | Password  |
| ---------- | ----------------- | --------- |
| Admin      | admin@example.com | Admin@123 |
| Sales User | sales@example.com | Sales@123 |

---

## Running tests

```bash
pytest -v
```

Tests use in-memory SQLite — no MySQL required. All 148 tests should pass.

---

## Project structure

```text
app/
├── __init__.py        # app factory
├── extensions.py      # db, login_manager
├── models/            # 6 models
├── routes/            # 9 blueprints
├── services/          # business logic
├── utils/             # helpers, calculations, validators, decorators
├── templates/         # Jinja templates
└── static/            # CSS + JS

sql/
├── schema.sql
└── required_queries.sql

scripts/seed.py
sample_data/
tests/
docs/
```

---

## Database design — key decisions

- Money fields are `DECIMAL(10,2)` / `DECIMAL(12,2)`, rounded with `ROUND_HALF_UP`.
- FK `ON DELETE RESTRICT` on customers referenced by orders and products referenced by orders/movements — deactivate instead of delete.
- `UNIQUE(sales_order_id, product_id)` enforces no duplicate products per order.
- `CHECK` constraints on discount 0–20, quantity > 0, rate ≥ 0, price ≥ 0, stock ≥ 0, quantity_change ≠ 0.
- Indexes on every searchable/filterable field.
- `order_date` is `DATE` — matches the report requirements.

---

## Concurrency — how stock stays consistent

Confirm/cancel use one transaction with `SELECT ... FOR UPDATE` on product rows:

1. `BEGIN`
2. `SELECT * FROM products WHERE id IN (...) FOR UPDATE`
3. Check stock for every line — abort if any is insufficient
4. Deduct (or restore) stock; write `stock_movements`
5. Update order status
6. `COMMIT`

A second concurrent confirmation blocks until the first commits, then sees the updated quantity. No overselling, no negative stock.

**Idempotency:** confirming an already-Confirmed order is a no-op; cancelling an already-Cancelled order is a no-op.

---

## CSV import format

```text
product_code,product_name,category,price,stock_quantity,status
PRD-001,Keyboard,Accessories,1500,20,Active
```

Rules:

- All rows validated before insert
- Any error → nothing imported; error lists every row with reason
- Duplicate codes rejected (within file or already in DB)
- Negative/non-numeric values rejected
- Invalid status rejected
- Each imported product gets an _Opening stock_ movement

Samples: `sample_data/valid_products.csv`, `sample_data/invalid_products.csv`.

---

## Assumptions

- Single currency, single stock location
- Whole-number quantities
- Taxes, delivery, purchasing, payment out of scope
- Only Confirmed orders in sales reports
- Product edit excludes `stock_quantity` — changes go through Inventory

---

## Known limitations

- No CSRF protection
- CSV import is synchronous
- Session-based auth (no JWT)
- Demo video is a separate deliverable

---

## Debugging exercise

See [`docs/DEBUGGING_EXERCISE.md`](docs/DEBUGGING_EXERCISE.md). Tests in `tests/test_debugging.py`.

## API documentation

See [`docs/API_DOCUMENTATION.md`](docs/API_DOCUMENTATION.md).

## AI usage disclosure

See [`AI_USAGE.md`](AI_USAGE.md).

## video
