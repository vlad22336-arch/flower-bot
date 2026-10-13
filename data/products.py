"""
Демо-каталог товаров цветочного магазина.
Картинки лежат в папке images/
"""

from pathlib import Path

IMAGES_DIR = Path(__file__).parent.parent / "images"

CATEGORIES = {
    "bouquets": {
        "name": "💐 Букеты",
        "emoji": "💐",
        "description": "Авторские букеты из свежих цветов"
    },
    "boxes": {
        "name": "🎁 Цветы в коробке",
        "emoji": "🎁",
        "description": "Элегантные композиции в коробках"
    },
    "plants": {
        "name": "🪴 Растения",
        "emoji": "🪴",
        "description": "Комнатные растения и горшечные цветы"
    },
}

PRODUCTS = {
    "bouquets": [
        {
            "id": "b1",
            "name": "Розовый рассвет",
            "price": 3500,
            "description": "Нежный букет из розовых роз, эустомы и гипсофилы. 25 стеблей.",
            "image": str(IMAGES_DIR / "bouquet1.jpg"),
        },
        {
            "id": "b2",
            "name": "Красная страсть",
            "price": 4200,
            "description": "Классический букет из 21 красной розы с зеленью.",
            "image": str(IMAGES_DIR / "bouquet2.jpg"),
        },
        {
            "id": "b3",
            "name": "Летний сад",
            "price": 2800,
            "description": "Яркий микс из гербер, хризантем и альстромерий.",
            "image": str(IMAGES_DIR / "bouquet3.jpg"),
        },
        {
            "id": "b4",
            "name": "Белая нежность",
            "price": 3900,
            "description": "Изысканный букет из белых пионов и эустомы.",
            "image": str(IMAGES_DIR / "bouquet4.jpg"),
        },
    ],
    "boxes": [
        {
            "id": "x1",
            "name": "Коробка «Нежность»",
            "price": 4500,
            "description": "Розы и эустома в шляпной коробке. Идеально для подарка.",
            "image": str(IMAGES_DIR / "box1.jpg"),
        },
        {
            "id": "x2",
            "name": "Коробка «Романтика»",
            "price": 5200,
            "description": "Красные и розовые розы в круглой коробке.",
            "image": str(IMAGES_DIR / "box2.jpg"),
        },
        {
            "id": "x3",
            "name": "Коробка «Весна»",
            "price": 3800,
            "description": "Тюльпаны и нарциссы в квадратной коробке.",
            "image": str(IMAGES_DIR / "box1.jpg"),
        },
    ],
    "plants": [
        {
            "id": "p1",
            "name": "Орхидея Фаленопсис",
            "price": 2500,
            "description": "Белая орхидея в керамическом горшке. Высота 50-60 см.",
            "image": str(IMAGES_DIR / "plant1.jpg"),
        },
        {
            "id": "p2",
            "name": "Монстера",
            "price": 1800,
            "description": "Популярное комнатное растение в горшке 15 см.",
            "image": str(IMAGES_DIR / "plant2.jpg"),
        },
        {
            "id": "p3",
            "name": "Суккуленты микс",
            "price": 1200,
            "description": "Набор из 3 разных суккулентов в декоративных горшочках.",
            "image": str(IMAGES_DIR / "plant1.jpg"),
        },
        {
            "id": "p4",
            "name": "Фикус Бенджамина",
            "price": 2200,
            "description": "Элегантный фикус в кашпо. Высота около 40 см.",
            "image": str(IMAGES_DIR / "plant2.jpg"),
        },
    ],
}

EXTRAS = [
    {
        "id": "e1",
        "name": "Открытка",
        "price": 150,
        "description": "Красивая открытка с вашим текстом",
        "image": None,
    },
    {
        "id": "e2",
        "name": "Шоколад Lindt",
        "price": 450,
        "description": "Плитка премиум-шоколада",
        "image": None,
    },
    {
        "id": "e3",
        "name": "Воздушный шар",
        "price": 300,
        "description": "Фольгированный шар с гелием",
        "image": None,
    },
]


def get_product_by_id(product_id: str) -> dict | None:
    for category_products in PRODUCTS.values():
        for product in category_products:
            if product["id"] == product_id:
                return product
    for extra in EXTRAS:
        if extra["id"] == product_id:
            return extra
    return None


def get_category_products(category_id: str) -> list:
    return PRODUCTS.get(category_id, [])
