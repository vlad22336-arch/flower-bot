from aiogram import Router
from . import (
    start, catalog, cart, other,
    admin, admin_promo, admin_products, admin_categories,
    admin_clients, admin_analytics, promo,
)

def setup_routers() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(catalog.router)
    router.include_router(cart.router)
    router.include_router(other.router)
    router.include_router(admin.router)
    router.include_router(admin_promo.router)
    router.include_router(admin_products.router)
    router.include_router(admin_categories.router)
    router.include_router(admin_clients.router)
    router.include_router(admin_analytics.router)
    router.include_router(promo.router)
    return router