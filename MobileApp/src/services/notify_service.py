from services.api import api_request


async def create_notification(stock_id: int, condition: str, value: float, page=None):
    payload = {
        "stock_id": stock_id,
        "condition": condition,
        "value": value,
    }
    resp = await api_request("POST", "/notify/", json=payload, page=page)
    if resp:
        if resp.status_code == 409:
            return "conflict"
        return resp.status_code == 200
    return False


async def fetch_notifications(stock_id=None, page=1, page_size=5, page_obj=None):
    params = {"page": page, "page_size": page_size}
    if stock_id is not None:
        params["stock_id"] = stock_id
    resp = await api_request("GET", "/notify/", params=params, page=page_obj)
    if resp and resp.status_code == 200:
        return resp.json()
    return []


async def deactivate_notification(alert_id: int, page=None):
    resp = await api_request("POST", f"/notify/{alert_id}/deactivate", page=page)
    return resp and resp.status_code == 200
