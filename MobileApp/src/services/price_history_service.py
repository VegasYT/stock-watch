from services.api import api_request


async def fetch_price_history(stock_id: int, days: int, count: int = 150, page=None):
    resp = await api_request(
        "GET",
        f"/prices/history/{stock_id}",
        params={"days": days, "count": count},
        page=page,
    )
    if resp and resp.status_code == 200:
        return resp.json()
    return {"data": [], "change": "—", "change_rub": 0}
