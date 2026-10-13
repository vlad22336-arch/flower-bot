import aiosqlite

DB_PATH = "data/orders.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Заказы
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                items TEXT,
                total INTEGER,
                status TEXT DEFAULT 'Новый',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Товары
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                name TEXT,
                price INTEGER,
                description TEXT,
                image TEXT
            )
        """)
        # Клиенты
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Настройки
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.commit()


# ===== ЗАКАЗЫ =====

async def add_order(user_id: int, username: str, full_name: str, phone: str, items: str, total: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO orders (user_id, username, full_name, phone, items, total) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, full_name, phone, items, total)
        )
        await db.commit()
        return cursor.lastrowid


async def get_orders(limit: int = 20, status: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute(
                "SELECT * FROM orders WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_order_by_id(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_order_status(order_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        await db.commit()


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*), COALESCE(SUM(total), 0) FROM orders")
        count, total = await cursor.fetchone()
        cursor2 = await db.execute("SELECT COUNT(*) FROM orders WHERE status = 'Новый'")
        new_count = (await cursor2.fetchone())[0]
        return count, total, new_count


# ===== ТОВАРЫ =====

async def add_product(category: str, name: str, price: int, description: str, image: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO products (category, name, price, description, image) VALUES (?, ?, ?, ?, ?)",
            (category, name, price, description, image)
        )
        await db.commit()
        return cursor.lastrowid


async def get_products(category: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if category:
            cursor = await db.execute("SELECT * FROM products WHERE category = ? ORDER BY id", (category,))
        else:
            cursor = await db.execute("SELECT * FROM products ORDER BY category, id")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_product_by_id(product_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_product(product_id: int, name: str = None, price: int = None, description: str = None, image: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        fields, values = [], []
        if name is not None:
            fields.append("name = ?"); values.append(name)
        if price is not None:
            fields.append("price = ?"); values.append(price)
        if description is not None:
            fields.append("description = ?"); values.append(description)
        if image is not None:
            fields.append("image = ?"); values.append(image)
        values.append(product_id)
        if fields:
            await db.execute(f"UPDATE products SET {', '.join(fields)} WHERE id = ?", values)
            await db.commit()


async def delete_product(product_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()


async def count_products():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM products")
        return (await cursor.fetchone())[0]


# ===== КЛИЕНТЫ =====

async def save_client(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO clients (user_id, username, full_name, last_seen)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                last_seen = CURRENT_TIMESTAMP
        """, (user_id, username or "", full_name))
        await db.commit()


async def get_clients():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM clients ORDER BY last_seen DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def count_clients():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM clients")
        return (await cursor.fetchone())[0]


# ===== НАСТРОЙКИ =====

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, value))
        await db.commit()


async def get_setting(key: str, default: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else default