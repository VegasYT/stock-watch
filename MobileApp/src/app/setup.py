import asyncio
import inspect
from pathlib import Path

import flet as ft
import flet_onesignal as fos

from app.router import routes
from components.bottom_nav_bar import bottom_nav_bar
from services.onesignal_service import send_onesignal_id_to_server
from services.token_storage import load as load_tokens, clear as clear_tokens
from state import session
from app.config import ONESIGNAL_APP_ID


async def run(page: ft.Page):
    # ---------- OneSignal ----------
    if page.platform.value in ("android", "ios"):
        session.onesignal = fos.OneSignal(
            settings=fos.OneSignalSettings(app_id=ONESIGNAL_APP_ID),
            on_error=lambda e: print("[OneSignal]", e.data),
        )
        page.overlay.append(session.onesignal)

    # ---------- токены ----------
    stored = await load_tokens(page)
    session.jwt_token = stored.get("jwt")
    session.refresh_token = stored.get("refresh")
    session.onesignal_id = stored.get("onesignal_id")
    # ---------- /токены ----------


    # ---------- оформление окна ----------
    page.title = "StockWatch"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(
        scrollbar_theme=ft.ScrollbarTheme(thumb_visibility=False, track_visibility=False)
    )
    page.window.width, page.window.height = 340, 750
    page.padding = 0
    page.scroll = True
    page.update()
    # ---------- /оформление ----------

    # ---------- нижняя навигация ----------
    # def on_nav_click(idx: int):
    #     paths = ["/portfolio", "/assets", "/news", "/analytics"]

    #     if idx == 3:  # «Аналитика» → выход
    #         clear_tokens(page)                # sync → без run_task!
    #         session.jwt_token = None
    #         session.refresh_token = None
    #         session.onesignal_id = None
    #         session.push_registered = False
    #         page.go("/login")
    #         return

    #     page.go(paths[idx])

    # nav_container = ft.Container(
    #     content=bottom_nav_bar(on_tab_change=on_nav_click),
    #     height=60,
    #     bottom=10,
    #     left=0,
    #     right=0,
    #     padding=ft.padding.only(bottom=10),
    # )
    # ---------- /нижняя навигация ----------

    def route_change(e: ft.RouteChangeEvent):
        route = page.route
        view_func = routes.get(route) or routes["/portfolio"]

        # if route in ["/", "/portfolio"]:
        # # if route == "/portfolio":
        #     if nav_container not in page.overlay:
        #         page.overlay.append(nav_container)
        # elif nav_container in page.overlay:
        #     page.overlay.remove(nav_container)

        if route in ("/", "/portfolio"):
            page.views.clear() 

        if route == "/_refresh":
            page.views.clear()
            page.views.append(ft.View(route, controls=[ft.Container()], padding=0))
            page.update()
            return

        async def _async():
            if route == "/asset":
                # Если portfolio уже в стеке — оставляем только его
                if any(getattr(v, 'route', '') == '/portfolio' for v in page.views):
                    page.views[:] = [v for v in page.views if getattr(v, 'route', '') == '/portfolio']
                else:
                    page.views.clear()
            view = ft.View(
                route,
                controls=[await view_func(page)],
                padding=0,
            )
            page.views.append(view)
            page.update()

        if inspect.iscoroutinefunction(view_func):
            page.run_task(_async)
        else:
            if route == "/asset":
                page.views[:] = [v for v in page.views if getattr(v, 'route', '') == '/portfolio']
            view = ft.View(
                route,
                controls=[view_func(page)],
                padding=0,
            )
            page.views.append(view) 
            page.update()

    page.on_route_change = route_change
    if page.route == "/":
        page.go("/portfolio")
    else:
        page.go(page.route)
