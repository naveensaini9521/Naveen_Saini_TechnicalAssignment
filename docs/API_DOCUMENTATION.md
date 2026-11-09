# REST API Documentation

Base URL: `http://localhost:5000`

All endpoints require authentication (session cookie set by `POST /login`).

Error responses are always JSON: `{ "error": "<message>" }`.

---

## Authentication

APIs use the same session cookie as the web interface.

```bash
# Login and save the cookie
curl -c cookies.txt -X POST http://localhost:5000/login \
  -d 'email=admin@example.com&password=Admin@123' -L -o /dev/null

# Then include the cookie on every API request
curl -b cookies.txt http://localhost:5000/api/products
```

---

## GET /api/products

List active products with optional search and pagination.

**Query parameters**

| Param      | Type   | Default | Description                        |
| ---------- | ------ | ------- | ---------------------------------- |
| `q`        | string | `""`    | Search in `product_code` or `name` |
| `page`     | int    | `1`     | Page number                        |
| `per_page` | int    | `20`    | Items per page (max 100)           |

**Example request**

```bash
curl -b cookies.txt 'http://localhost:5000/api/products?q=keyboard&page=1&per_page=20'
```

**Response 200**

```json
{
  "items": [
    {
      "id": 1,
      "product_code": "PRD-001",
      "name": "Keyboard",
      "category": "Accessories",
      "price": "1500.00",
      "stock_quantity": 20,
      "is_active": true
    }
  ],
  "page": 1,
  "per_page": 20,
  "total": 1,
  "pages": 1
}
```

**Errors**

| Status | Meaning       |
| ------ | ------------- |
| 401    | Not logged in |

---

## POST /api/orders

Create a Draft order.

**Example request**

```bash
curl -b cookies.txt -X POST http://localhost:5000/api/orders \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_id": 1,
    "discount_percentage": 10,
    "items": [
      {"product_id": 1, "quantity": 2},
      {"product_id": 2, "quantity": 3}
    ]
  }'
```

**Response 201**

```json
{
  "id": 7,
  "order_number": "SO-20260115-0001",
  "customer_id": 1,
  "customer_name": "Acme Traders",
  "order_date": "2026-01-15",
  "status": "Draft",
  "discount_percentage": "10.00",
  "subtotal": "4500.00",
  "discount_amount": "450.00",
  "grand_total": "4050.00",
  "created_by": 2,
  "created_at": "2026-01-15T10:00:00",
  "items": [
    {
      "id": 10,
      "product_id": 1,
      "quantity": 2,
      "rate": "1500.00",
      "amount": "3000.00"
    },
    {
      "id": 11,
      "product_id": 2,
      "quantity": 3,
      "rate": "500.00",
      "amount": "1500.00"
    }
  ]
}
```

**Errors**

| Status | Meaning                                                                  |
| ------ | ------------------------------------------------------------------------ |
| 400    | Missing customer, empty items, duplicate product, invalid discount, etc. |
| 401    | Not logged in                                                            |

---

## GET /api/orders/{id}

Retrieve an accessible order and its items.

**Example request**

```bash
curl -b cookies.txt http://localhost:5000/api/orders/7
```

**Response 200**

Same shape as the `POST /api/orders` response.

**Errors**

| Status | Meaning                                   |
| ------ | ----------------------------------------- |
| 401    | Not logged in                             |
| 403    | Sales User accessing another user's order |
| 404    | Order not found                           |

---

## POST /api/orders/{id}/confirm

Confirm a Draft order. Deducts stock atomically. Idempotent.

**Example request**

```bash
curl -b cookies.txt -X POST http://localhost:5000/api/orders/7/confirm
```

**Response 200**

```json
{
  "id": 7,
  "order_number": "SO-20260115-0001",
  "status": "Confirmed",
  "grand_total": "4050.00",
  "items": [ ... ]
}
```

**Errors**

| Status | Meaning                                   |
| ------ | ----------------------------------------- |
| 400    | Draft has no items                        |
| 401    | Not logged in                             |
| 403    | Sales User accessing another user's order |
| 404    | Order not found                           |
| 409    | Insufficient stock, or order is Cancelled |

---

## POST /api/orders/{id}/cancel

Cancel a Draft or Confirmed order. Restores stock if the order was Confirmed. Idempotent.

**Example request**

```bash
curl -b cookies.txt -X POST http://localhost:5000/api/orders/7/cancel
```

**Response 200**

```json
{
  "id": 7,
  "order_number": "SO-20260115-0001",
  "status": "Cancelled",
  "grand_total": "4050.00",
  "items": [ ... ]
}
```

**Errors**

| Status | Meaning                                   |
| ------ | ----------------------------------------- |
| 401    | Not logged in                             |
| 403    | Sales User accessing another user's order |
| 404    | Order not found                           |

---

## Status Code Reference

| Code | When                                                                    |
| ---- | ----------------------------------------------------------------------- |
| 200  | Successful GET, successful confirm/cancel                               |
| 201  | Order created                                                           |
| 400  | Validation failure                                                      |
| 401  | Not authenticated                                                       |
| 403  | Authenticated but forbidden (Sales User accessing another user's order) |
| 404  | Resource not found                                                      |
| 409  | State conflict (insufficient stock, wrong status transition)            |
| 500  | Unexpected server error (no tracebacks exposed)                         |

---

## Full Example Session

```bash
# 1. Login
curl -c cookies.txt -X POST http://localhost:5000/login \
  -d 'email=admin@example.com&password=Admin@123' -L -o /dev/null

# 2. List products
curl -b cookies.txt http://localhost:5000/api/products

# 3. Create order
curl -b cookies.txt -X POST http://localhost:5000/api/orders \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":1,"discount_percentage":10,"items":[{"product_id":1,"quantity":2}]}'

# 4. Get order
curl -b cookies.txt http://localhost:5000/api/orders/1

# 5. Confirm
curl -b cookies.txt -X POST http://localhost:5000/api/orders/1/confirm

# 6. Cancel
curl -b cookies.txt -X POST http://localhost:5000/api/orders/1/cancel
```

---

## Permission Model

| Role            | Access                                                           |
| --------------- | ---------------------------------------------------------------- |
| Admin           | All endpoints, all orders                                        |
| Sales User      | `/api/products`, own orders only (`/api/orders` created by them) |
| Unauthenticated | None — `401` on every endpoint                                   |

Attempts to access another user's order as a Sales User return `403 Forbidden` (verified in `tests/test_permissions.py`).
