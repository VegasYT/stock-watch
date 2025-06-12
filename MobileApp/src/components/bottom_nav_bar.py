import flet as ft

from theme import colors as C


def on_nav_click_factory(page):
    def on_nav_click(idx: int):
        if idx == 3:
            # Логаут
            from services.token_storage import clear as clear_tokens
            from state import session
            clear_tokens(page)
            session.jwt_token = None
            session.refresh_token = None
            session.onesignal_id = None
            session.push_registered = False
            page.go("/login")
        else:
            paths = ["/portfolio", "/notifications", "/transactions"]
            page.go(paths[idx])
    return on_nav_click


def bottom_nav_bar(page, selected_index=0):
    nav_items = [
        {"icon": ft.icons.ACCOUNT_BALANCE_WALLET, "label": "Портфель"},
        {"icon": ft.icons.NOTIFICATIONS, "label": "Уведомления"},
        {"icon": ft.icons.SWAP_HORIZ, "label": "Транзакции"},
        {"icon": ft.icons.LOGOUT, "label": "Выйти"},
    ]

    on_nav_click = on_nav_click_factory(page)

    buttons = []
    for i, item in enumerate(nav_items):
        btn = ft.IconButton(
            icon=item["icon"],
            icon_color=C.TEXT if i != selected_index else C.PRIMARY,
            on_click=lambda e, idx=i: on_nav_click(idx),
            tooltip=item["label"]
        )
        buttons.append(btn)

    return ft.Container(
        margin=ft.margin.symmetric(horizontal=20),
        border_radius=40,
        height=50,
        padding=0,
        content=ft.Container(
            border_radius=40,
            height=40,
            bgcolor=ft.colors.with_opacity(0.05, C.TEXT),
            blur=10,
            padding=ft.padding.symmetric(horizontal=10),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                expand=True,
                controls=buttons,
            )
        )
    )
