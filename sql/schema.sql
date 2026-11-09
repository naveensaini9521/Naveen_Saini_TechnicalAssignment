-- Sales Order & Inventory Management — Schema

DROP DATABASE IF EXISTS sales_inventory;
CREATE DATABASE sales_inventory
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE sales_inventory;

-- ------------------------------------------------------------
-- 1. users
-- ------------------------------------------------------------
CREATE TABLE users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(120)  NOT NULL,
  email         VARCHAR(190)  NOT NULL,
  password_hash VARCHAR(255)  NOT NULL,
  role          ENUM('Admin','Sales User') NOT NULL,
  created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 2. customers
-- ------------------------------------------------------------
CREATE TABLE customers (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(150) NOT NULL,
  email      VARCHAR(190) NULL,
  mobile     VARCHAR(20)  NULL,
  city       VARCHAR(100) NULL,
  is_active  TINYINT(1)   NOT NULL DEFAULT 1,
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_customers_name   (name),
  KEY idx_customers_email  (email),
  KEY idx_customers_mobile (mobile),
  KEY idx_customers_active (is_active)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 3. products
-- ------------------------------------------------------------
CREATE TABLE products (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  product_code   VARCHAR(50)   NOT NULL,
  name           VARCHAR(150)  NOT NULL,
  category       VARCHAR(100)  NOT NULL,
  price          DECIMAL(10,2) NOT NULL,
  stock_quantity INT           NOT NULL DEFAULT 0,
  is_active      TINYINT(1)    NOT NULL DEFAULT 1,
  created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_products_code (product_code),
  KEY idx_products_name     (name),
  KEY idx_products_category (category),
  KEY idx_products_active   (is_active),
  CONSTRAINT chk_products_price CHECK (price >= 0),
  CONSTRAINT chk_products_stock CHECK (stock_quantity >= 0)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 4. sales_orders
-- ------------------------------------------------------------
CREATE TABLE sales_orders (
  id                  INT AUTO_INCREMENT PRIMARY KEY,
  order_number        VARCHAR(30)   NOT NULL,
  customer_id         INT           NOT NULL,
  order_date          DATE          NOT NULL,
  status              ENUM('Draft','Confirmed','Cancelled') NOT NULL DEFAULT 'Draft',
  discount_percentage DECIMAL(5,2)  NOT NULL DEFAULT 0.00,
  subtotal            DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  discount_amount     DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  grand_total         DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  created_by          INT           NOT NULL,
  created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_orders_number (order_number),
  KEY idx_orders_customer (customer_id),
  KEY idx_orders_status   (status),
  KEY idx_orders_date     (order_date),
  KEY idx_orders_creator  (created_by),
  CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
  CONSTRAINT fk_orders_creator  FOREIGN KEY (created_by)  REFERENCES users(id)     ON DELETE RESTRICT,
  CONSTRAINT chk_orders_discount CHECK (discount_percentage BETWEEN 0 AND 20)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 5. sales_order_items
-- ------------------------------------------------------------
CREATE TABLE sales_order_items (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  sales_order_id INT           NOT NULL,
  product_id     INT           NOT NULL,
  quantity       INT           NOT NULL,
  rate           DECIMAL(10,2) NOT NULL,
  amount         DECIMAL(12,2) NOT NULL,
  UNIQUE KEY uq_items_order_product (sales_order_id, product_id),
  KEY idx_items_order   (sales_order_id),
  KEY idx_items_product (product_id),
  CONSTRAINT fk_items_order   FOREIGN KEY (sales_order_id) REFERENCES sales_orders(id) ON DELETE CASCADE,
  CONSTRAINT fk_items_product FOREIGN KEY (product_id)     REFERENCES products(id)     ON DELETE RESTRICT,
  CONSTRAINT chk_items_qty  CHECK (quantity > 0),
  CONSTRAINT chk_items_rate CHECK (rate >= 0)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 6. stock_movements
-- ------------------------------------------------------------
CREATE TABLE stock_movements (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  product_id       INT           NOT NULL,
  movement_type    ENUM('Opening','Adjustment','Order Confirm','Order Cancel') NOT NULL,
  quantity_change  INT           NOT NULL,
  related_order_id INT           NULL,
  reason           VARCHAR(255)  NULL,
  created_by       INT           NOT NULL,
  created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_mv_product (product_id),
  KEY idx_mv_order   (related_order_id),
  KEY idx_mv_type    (movement_type),
  KEY idx_mv_time    (created_at),
  CONSTRAINT fk_mv_product FOREIGN KEY (product_id)       REFERENCES products(id)     ON DELETE RESTRICT,
  CONSTRAINT fk_mv_order   FOREIGN KEY (related_order_id) REFERENCES sales_orders(id) ON DELETE RESTRICT,
  CONSTRAINT fk_mv_user    FOREIGN KEY (created_by)       REFERENCES users(id)        ON DELETE RESTRICT,
  CONSTRAINT chk_mv_qty_nonzero CHECK (quantity_change <> 0)
) ENGINE=InnoDB;