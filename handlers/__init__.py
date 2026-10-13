from aiogram import Router
from . import start, catalog, cart, other

def setup_routers() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(catalog.router)
    router.include_router(cart.router)
    router.include_router(other.router)
    return router
