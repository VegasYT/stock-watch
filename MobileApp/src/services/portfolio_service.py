from app.config import BASE_URL
from state import session
from services.api import api_request
import time


__cached_portfolio: list | None = None
__last_fetch_ts = 0
__CACHE_TTL = 120  # секунд


def portfolio_cache_is_valid():
    return (
        __cached_portfolio is not None
        and (time.time() - __last_fetch_ts) < __CACHE_TTL
    )


async def fetch_portfolio(
    page=None,
    *,
    force_refresh: bool = False,
    page_number: int | None = None,
    page_size: int | None = None,
):
    """Получаем активы портфеля.

    - Если *page_number* не указан (старый режим) — используем кэш.
    - Если указан номер страницы — всегда идём в API, кэш не трогаем.
    """
    global __cached_portfolio, __last_fetch_ts
    print(f"[fetch_portfolio] page_number={page_number}, page_size={page_size}, force_refresh={force_refresh}")

    # ---- кэшируем **только** полный список ----
    if (
        page_number is None
        and not force_refresh
        and __cached_portfolio is not None
        and (time.time() - __last_fetch_ts) < __CACHE_TTL
    ):
        return __cached_portfolio

    params = {}
    if page_number is not None:
        params["page_number"] = page_number
    if page_size is not None:
        params["page_size"] = page_size

    try:
        resp = await api_request("GET", "/portfolio/", params=params, page=page)
        if resp and resp.status_code == 200:
            data = resp.json()
            # сохраняем только полный список
            if page_number is None:
                __cached_portfolio = data
                __last_fetch_ts = time.time()
            return data

        return []
    except Exception as e:
        print(f"[fetch_portfolio] Ошибка: {e}")
        return []


async def add_to_portfolio(stock_id: int, quantity: float, page=None):
    resp = await api_request(
        "POST", "/portfolio/", json={"stock_id": stock_id, "quantity": quantity}, page=page
    )
    if resp and resp.status_code == 201:
        return True
    # В случае ошибки пробуем вернуть detail, если есть
    try:
        data = resp.json() if resp is not None and resp.content else {}
    except Exception:
        data = {}
    return {"ok": False, "data": data}


async def delete_asset(asset_id: int, page=None):
    resp = await api_request("DELETE", f"/portfolio/{asset_id}", page=page)
    return resp and resp.status_code == 204


async def update_portfolio_with_transactions(
    asset_id: int,
    quantity: float,
    add: list,
    delete: list,
    update: list,
    page=None,
):
    payload = {
        "quantity": quantity,
        "add_transactions": add,
        "delete_transaction_ids": delete,
        "update_transactions": update,
    }
    resp = await api_request("PATCH", f"/portfolio/{asset_id}", json=payload, page=page)
    return resp and resp.status_code == 200


def invalidate_portfolio_cache():
    global __cached_portfolio, __last_fetch_ts
    __cached_portfolio = None
    __last_fetch_ts = 0
    session.cached_portfolio = None


async def search_stocks(query: str, page=None):
    resp = await api_request("GET", "/stocks/search", params={"q": query}, page=page)
    if resp and resp.status_code == 200:
        return resp.json()
    return []


async def fetch_asset_info(asset_id: int, page=None) -> dict:
    resp = await api_request("GET", f"/portfolio/{asset_id}/info", page=page)
    if resp and resp.status_code == 200:
        return resp.json()
    return {}
