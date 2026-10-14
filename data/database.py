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
                comment TEXT,
                items TEXT,
                total INTEGER,
                status TEXT DEFAULT 'Новый',
                promo TEXT,
                discount INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                name TEXT,
                price INTEGER,
                old_price INTEGER,
                description TEXT,
                image TEXT,
                is_hit INTEGER DEFAULT 0,
                is_new INTEGER DEFAULT 0,
                in_stock INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                birthday TEXT,
                note TEXT,
                is_blacklisted INTEGER DEFAULT 0,
                orders_count INTEGER DEFAULT 0,
                total_spent INTEGER DEFAULT 0,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promos (
                code TEXT PRIMARY KEY,
                discount INTEGER,
                uses_left INTEGER,
                is_active INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                name TEXT,
                emoji TEXT,
                sort_order INTEGER DEFAULT 0
            )
        """)
        await db.commit()


# ===== ЗАКАЗЫ =====

async def add_order(user_id, username, full_name, phone, comment, items, total, promo=None, discount=0):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO orders (user_id, username, full_name, phone, comment, items, total, promo, discount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, username, full_name, phone, comment, items, total, promo, discount)
        )
        await db.commit()
        return cursor.lastrowid


async def get_orders(limit=20, status=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute("SELECT * FROM orders WHERE status = ? ORDER BY id DESC LIMIT ?", (status, limit))
        else:
            cursor = await db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_all_orders():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM orders ORDER BY id DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_order_by_id(order_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_order_status(order_id, status):
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


async def delete_old_orders(days=90):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM orders WHERE created_at < DATE('now', ?)", (f'-{days} days',))
        await db.commit()


# ===== ТОВАРЫ =====

async def add_product(category, name, price, description, image=None, old_price=None, is_hit=0, is_new=0):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO products (category, name, price, old_price, description, image, is_hit, is_new)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (category, name, price, old_price, description, image, is_hit, is_new))
        await db.commit()
        return cursor.lastrowid


async def get_products(category=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if category:
            cursor = await db.execute("SELECT * FROM products WHERE category = ? ORDER BY sort_order, id", (category,))
        else:
            cursor = await db.execute("SELECT * FROM products ORDER BY category, sort_order, id")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_product_by_id(product_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_product(product_id, **kwargs):
    async with aiosqlite.connect(DB_PATH) as db:
        fields, values = [], []
        for key, val in kwargs.items():
            if val is not None:
                fields.append(f"{key} = ?")
                values.append(val)
        if fields:
            values.append(product_id)
            await db.execute(f"UPDATE products SET {', '.join(fields)} WHERE id = ?", values)
            await db.commit()


async def delete_product(product_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()


async def count_products():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM products")
        return (await cursor.fetchone())[0]


# ===== КЛИЕНТЫ =====

async def save_client(user_id, username, full_name):
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


async def get_client(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM clients WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_client(user_id, **kwargs):
    async with aiosqlite.connect(DB_PATH) as db:
        fields, values = [], []
        for key, val in kwargs.items():
            if val is not None:
                fields.append(f"{key} = ?")
                values.append(val)
        if fields:
            values.append(user_id)
            await db.execute(f"UPDATE clients SET {', '.join(fields)} WHERE user_id = ?", values)
            await db.commit()


async def count_clients():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM clients")
        return (await cursor.fetchone())[0]


# ===== ПРОМОКОДЫ =====

async def add_promo(code, discount, uses_left):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO promos (code, discount, uses_left) VALUES (?, ?, ?)", (code.upper(), discount, uses_left))
        await db.commit()


async def get_promo(code):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM promos WHERE code = ? AND is_active = 1", (code.upper(),))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_promos():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM promos ORDER BY code")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def use_promo(code):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE promos SET uses_left = uses_left - 1 WHERE code = ?", (code.upper(),))
        await db.execute("UPDATE promos SET is_active = 0 WHERE uses_left <= 0")
        await db.commit()


async def delete_promo(code):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM promos WHERE code = ?", (code.upper(),))
        await db.commit()


# ===== НАСТРОЙКИ =====

async def set_setting(key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
        await db.commit()


async def get_setting(key, default=""):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else default
        

# ===== МИГРАЦИЯ (обновление старой базы) =====

async def migrate_db():
    """Добавляет недостающие колонки в таблицы (если база старая)."""
    async with aiosqlite.connect(DB_PATH) as db:
        # orders
        cursor = await db.execute("PRAGMA table_info(orders)")
        cols = [row[1] for row in await cursor.fetchall()]
        if "comment" not in cols:
            await db.execute("ALTER TABLE orders ADD COLUMN comment TEXT")
        if "promo" not in cols:
            await db.execute("ALTER TABLE orders ADD COLUMN promo TEXT")
        if "discount" not in cols:
            await db.execute("ALTER TABLE orders ADD COLUMN discount INTEGER DEFAULT 0")

        # products
        cursor = await db.execute("PRAGMA table_info(products)")
        cols = [row[1] for row in await cursor.fetchall()]
        if "old_price" not in cols:
            await db.execute("ALTER TABLE products ADD COLUMN old_price INTEGER")
        if "is_hit" not in cols:
            await db.execute("ALTER TABLE products ADD COLUMN is_hit INTEGER DEFAULT 0")
        if "is_new" not in cols:
            await db.execute("ALTER TABLE products ADD COLUMN is_new INTEGER DEFAULT 0")
        if "in_stock" not in cols:
            await db.execute("ALTER TABLE products ADD COLUMN in_stock INTEGER DEFAULT 1")
        if "sort_order" not in cols:
            await db.execute("ALTER TABLE products ADD COLUMN sort_order INTEGER DEFAULT 0")

        # clients
        cursor = await db.execute("PRAGMA table_info(clients)")
        cols = [row[1] for row in await cursor.fetchall()]
        if "birthday" not in cols:
            await db.execute("ALTER TABLE clients ADD COLUMN birthday TEXT")
        if "note" not in cols:
            await db.execute("ALTER TABLE clients ADD COLUMN note TEXT")
        if "is_blacklisted" not in cols:
            await db.execute("ALTER TABLE clients ADD COLUMN is_blacklisted INTEGER DEFAULT 0")
        if "orders_count" not in cols:
            await db.execute("ALTER TABLE clients ADD COLUMN orders_count INTEGER DEFAULT 0")
        if "total_spent" not in cols:
            await db.execute("ALTER TABLE clients ADD COLUMN total_spent INTEGER DEFAULT 0")

        await db.commit()


# ===== МАССОВОЕ ИЗМЕНЕНИЕ ЦЕН =====

async def change_all_prices(percent: int):
    """Изменяет все цены на указанный процент (может быть отрицательным)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE products SET price = CAST(price * ? / 100 AS INTEGER)", (100 + percent,))
        await db.commit()


# ===== АНАЛИТИКА =====

async def get_top_products(limit: int = 10):
    """Возвращает топ товаров по количеству заказов."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT items FROM orders")
        rows = await cursor.fetchall()
        counts = {}
        for row in rows:
            for line in (row[0] or "").split("\n"):
                if "×" in line:
                    name = line.split("×")[0].strip()
                    counts[name] = counts.get(name, 0) + 1
        sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:limit]


async def get_avg_check():
    """Возвращает средний чек."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COALESCE(AVG(total), 0) FROM orders")
        avg = (await cursor.fetchone())[0]
        return int(avg)


async def get_orders_by_days(days: int = 7):
    """Возвращает количество заказов и сумму по дням."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT DATE(created_at), COUNT(*), COALESCE(SUM(total), 0)
            FROM orders
            WHERE created_at >= DATE('now', ?)
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at)
        """, (f'-{days} days',))
        rows = await cursor.fetchall()
        return rows


# ===== КАТЕГОРИИ =====

async def add_category(code: str, name: str, emoji: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO categories (code, name, emoji) VALUES (?, ?, ?)",
            (code, name, emoji)
        )
        await db.commit()


async def get_categories():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM categories ORDER BY sort_order, id")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_category(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM categories WHERE code = ?", (code,))
        await db.commit()


# ===== РЕЗЕРВНОЕ КОПИРОВАНИЕ =====

async def backup_db():
    """Возвращает путь к файлу базы для скачивания."""
    return DB_PATH