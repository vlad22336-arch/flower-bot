import aiosqlite

DB_PATH = "data/orders.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
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
        await db.commit()


async def add_order(user_id: int, username: str, full_name: str, phone: str, items: str, total: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO orders (user_id, username, full_name, phone, items, total) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, full_name, phone, items, total)
        )
        await db.commit()
        return cursor.lastrowid


async def get_orders(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_order_by_id(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_order_status(order_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status = ? WHERE id = ?", (status, order_id)
        )
        await db.commit()


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*), COALESCE(SUM(total), 0) FROM orders")
        count, total = await cursor.fetchone()
        return count, total