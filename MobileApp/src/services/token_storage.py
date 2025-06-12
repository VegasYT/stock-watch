import json
import flet as ft
from typing import TypedDict, cast


class Tokens(TypedDict, total=False):
    jwt: str
    refresh: str
    onesignal: str


_KEY = "tokens"


async def save(page: ft.Page, data: Tokens) -> None:
    try:
        current = await load(page)
        current.update({k: v for k, v in data.items() if v})
        await page.client_storage.set_async(_KEY, json.dumps(current))
    except Exception as e:
        print(f"[token_storage] ❌ async save error: {e}")


async def load(page: ft.Page) -> Tokens:
    try:
        raw = await page.client_storage.get_async(_KEY)
        return cast(Tokens, json.loads(raw)) if raw else {}
    except Exception as e:
        print(f"[token_storage] ❌ async load error: {e}")
        return {}


def clear(page: ft.Page) -> None:
    try:
        page.client_storage.remove(_KEY)
    except Exception as e:
        print(f"[token_storage] ❌ clear error: {e}")
