-- ------------------------------------------------------------
-- Q1: Top three customers by Confirmed order grand total
-- ------------------------------------------------------------
SELECT
    c.id               AS customer_id,
    c.name             AS customer_name,
    SUM(o.grand_total) AS total_confirmed_sales
FROM customers c
JOIN sales_orders o
    ON o.customer_id = c.id
   AND o.status      = 'Confirmed'
GROUP BY c.id, c.name
ORDER BY total_confirmed_sales DESC
LIMIT 3;


-- ------------------------------------------------------------
-- Q2: Top three products by quantity sold in Confirmed orders
-- ------------------------------------------------------------
SELECT
    p.id                         AS product_id,
    p.product_code,
    p.name                       AS product_name,
    SUM(oi.quantity)             AS total_qty_sold
FROM products p
JOIN sales_order_items oi ON oi.product_id = p.id
JOIN sales_orders o       ON o.id = oi.sales_order_id
                         AND o.status = 'Confirmed'
GROUP BY p.id, p.product_code, p.name
ORDER BY total_qty_sold DESC
LIMIT 3;


-- ------------------------------------------------------------
-- Q3: Customers who have never placed any order
-- ------------------------------------------------------------
SELECT
    c.id,
    c.name,
    c.email,
    c.mobile
FROM customers c
LEFT JOIN sales_orders o ON o.customer_id = c.id
WHERE o.id IS NULL
ORDER BY c.name ASC;


-- ------------------------------------------------------------
-- Q4: Month-wise Confirmed sales totals (year + month)
-- ------------------------------------------------------------
SELECT
    YEAR(o.order_date)  AS year,
    MONTH(o.order_date) AS month,
    SUM(o.grand_total)  AS total_sales,
    COUNT(*)            AS order_count
FROM sales_orders o
WHERE o.status = 'Confirmed'
GROUP BY YEAR(o.order_date), MONTH(o.order_date)
ORDER BY year DESC, month DESC;


-- ------------------------------------------------------------
-- Q5: Products below a supplied stock threshold
-- Replace the :threshold placeholder with the desired number
-- ------------------------------------------------------------
SELECT
    id,
    product_code,
    name,
    stock_quantity
FROM products
WHERE stock_quantity < :threshold
  AND is_active      = 1
ORDER BY stock_quantity ASC;