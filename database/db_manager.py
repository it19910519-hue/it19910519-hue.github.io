import os
import aiosqlite

# =============================================================
# ПУТЬ К БАЗЕ ДАННЫХ
# =============================================================
DB_PATH = os.path.join(os.path.dirname(__file__), "axioma_shop.db")

# =============================================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# =============================================================
async def init_db():
    """Создание всех таблиц базы данных и проверка необходимых колонок"""
    async with aiosqlite.connect(DB_PATH) as db:

        # ================= USERS =================
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                role TEXT DEFAULT 'user'
            )
        """)

        # ================= PRODUCTS =================
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                image_url TEXT,
                category TEXT DEFAULT 'Без категории',
                stock INTEGER DEFAULT 0
            )
        """)

        # ================= ORDERS =================
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                customer_name TEXT,
                address TEXT,
                items TEXT,
                total_price REAL,
                comment TEXT,
                status TEXT DEFAULT 'pending',
                courier_id INTEGER DEFAULT NULL,
                phone TEXT DEFAULT NULL,
                delivery_time TEXT DEFAULT NULL,
                cooking_started_at TEXT DEFAULT NULL,
                created_at TEXT DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.commit()

        # Подушка безопасности (дописывает колонки, если база уже создана)
        columns_to_check = {
            "products": [
                ("stock", "INTEGER DEFAULT 0"),
                ("category", "TEXT DEFAULT 'Без категории'")
            ],
            "orders": [
                ("phone", "TEXT DEFAULT NULL"),
                ("delivery_time", "TEXT DEFAULT NULL"),
                ("cooking_started_at", "TEXT DEFAULT NULL"),
                ("created_at", "TEXT DEFAULT NULL")
            ]
        }
        
        for table, cols in columns_to_check.items():
            for col_name, col_type in cols:
                try:
                    await db.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                    await db.commit()
                except aiosqlite.OperationalError:
                    pass


# =============================================================
# USERS / ROLES
# =============================================================
async def add_user(user_id: int, username: str, role: str = "user"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, role)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET username = ?
            """,
            (user_id, username, role, username)
        )
        await db.commit()

async def get_user_role(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT role FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "user"

async def update_user_role(user_id: int, new_role: str):
    async with aiosqlite.connect(DB_PATH) as db:
        
        await db.execute(
            """
            INSERT INTO users (user_id, username, role)
            VALUES (?, 'Пользователь', ?)
            ON CONFLICT(user_id)
            DO UPDATE SET role = ?
            """,
            (user_id, new_role, new_role)
        )
        await db.commit()


# =============================================================
# ADMIN STATS
# =============================================================
async def get_users_count():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_users_by_role(role: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE role = ?",
            (role,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_admin_sales_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT SUM(total_price) FROM orders WHERE status = 'delivered'"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row[0] is not None else 0.0

async def get_orders_count_by_status(status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM orders WHERE status = ?",
            (status,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


# =============================================================
# PRODUCTS
# =============================================================
async def add_product(title: str, description: str, price: float, category: str = "Без категории", stock: int = 0, photo: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO products (title, description, price, category, stock, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, description, price, category, stock, photo)
        )
        await db.commit()

async def get_all_products():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_product_by_id(product_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def delete_product(product_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()

async def reduce_product_stock(product_id: int, quantity: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE products SET stock = MAX(0, stock - ?) WHERE id = ?",
            (quantity, product_id)
        )
        await db.commit()


# =============================================================
# ORDERS / CHEF / COURIER
# =============================================================
async def create_order(user_id: int, customer_name: str, address: str, items: str, total_price: float, comment: str = "", phone: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            INSERT INTO orders (
                user_id, customer_name, address, items, total_price, comment, phone, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', DATETIME('now', 'localtime'))
            RETURNING id
            """,
            (user_id, customer_name, address, items, total_price, comment, phone)
        ) as cursor:
            row = await cursor.fetchone()
            await db.commit()
            return row[0] if row else None

async def get_order_by_id(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE id = ?",
            (order_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_orders_by_status(status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE status = ?",
            (status,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def start_cooking_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status = 'cooking', cooking_started_at = DATETIME('now', 'localtime') WHERE id = ?",
            (order_id,)
        )
        await db.commit()

async def ready_for_delivery_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status = 'ready_for_delivery' WHERE id = ?",
            (order_id,)
        )
        await db.commit()

# ЗАКРЕПЛЕНИЕ ЗА КУРЬЕРОМ СТРОГО ПО НОМЕРУ ЗАКАЗА
async def assign_order_to_courier(order_id: int, courier_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET courier_id = ?, status = 'delivering' WHERE id = ?",
            (courier_id, order_id)
        )
        await db.commit()

# ЗАКРЫТИЕ ЗАКАЗА СТРОГО ПО НОМЕРУ ЗАКАЗА КАК ВЫПОЛНЕННЫЙ
async def complete_order_delivery(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status = 'delivered' WHERE id = ?",
            (order_id,)
        )
        await db.commit()

async def get_courier_orders(courier_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE courier_id = ? AND status = ?",
            (courier_id, status)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_courier_active_orders_count(courier_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM orders WHERE courier_id = ? AND status = 'delivering'",
            (courier_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_courier_total_earnings(courier_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT SUM(total_price) FROM orders WHERE courier_id = ? AND status = 'delivered'",
            (courier_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row[0] is not None else 0.0

# ДОБАВЛЕННАЯ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ДЕТАЛЕЙ ВЫПОЛНЕННЫХ ЗАКАЗОВ КУРЬЕРА
async def get_courier_delivered_orders_details(courier_id: int):
    """
    Возвращает список всех выполненных заказов курьера 
    (id, address, total_price) для детальной статистики.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, address, total_price 
            FROM orders 
            WHERE courier_id = ? AND status = 'delivered'
            ORDER BY id DESC
            """, 
            (courier_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def update_order_delivery_time(order_id: int, delivery_time: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET delivery_time = ? WHERE id = ?",
            (delivery_time, order_id)
        )
        await db.commit()

async def update_order_cooking_time(order_id: int, cooking_time: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET cooking_started_at = ? WHERE id = ?",
            (cooking_time, order_id)
        )
        await db.commit()


# =============================================================
# ПОДУШКА БЕЗОПАСНОСТИ ДЛЯ АЛЬТЕРНАТИВНЫХ ВЫЗОВОВ И СТАРЫХ ИМЕН
# =============================================================
start_delivery_order = assign_order_to_courier
take_order_in_db = assign_order_to_courier
take_order = assign_order_to_courier

complete_order_in_db = complete_order_delivery
complete_order = complete_order_delivery

get_counter_active_orders_count = get_courier_active_orders_count
get_counter_total_earnings = get_courier_total_earnings