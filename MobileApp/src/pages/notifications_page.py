import flet as ft

from theme import colors as C
from services.notify_service import fetch_notifications, deactivate_notification
from components.bottom_nav_bar import bottom_nav_bar


PAGE_SIZE = 10


def notifications_page(page: ft.Page):
    all_alerts_list = ft.ListView(spacing=12, expand=True, on_scroll_interval=0)
    page_number = 1
    loading = False
    all_loaded = False
    alerts_data = []

    async def reload_alerts():
        nonlocal page_number, all_loaded, alerts_data
        all_alerts_list.controls.clear()
        page_number = 1
        all_loaded = False
        alerts_data.clear()
        await load_alerts_page()

    async def handle_deactivate(alert_id: int):
        ok = await deactivate_notification(alert_id, page=page)
        if ok:
            await reload_alerts()

    # --- Функция подгрузки уведомлений ---
    async def load_alerts_page():
        nonlocal loading, page_number, all_loaded
        if loading or all_loaded:
            return
        loading = True
        spinner = ft.Container(content=ft.ProgressRing(), alignment=ft.alignment.center)
        all_alerts_list.controls.append(spinner)
        page.update()
        # stock_id не передаем вообще
        new_alerts = await fetch_notifications(page=page_number, page_size=PAGE_SIZE, page_obj=page, stock_id=None)
        all_alerts_list.controls.remove(spinner)

        if not new_alerts:
            if page_number == 1:
                all_alerts_list.controls.append(ft.Text("Нет уведомлений", color=C.HINT))
            all_loaded = True
        else:
            for alert in new_alerts:
                if alert["id"] in {a["id"] for a in alerts_data}:
                    continue  # не дублируем
                alerts_data.append(alert)
                all_alerts_list.controls.append(render_alert(alert))
            if len(new_alerts) < PAGE_SIZE:
                all_loaded = True

        page_number += 1
        page.update()
        loading = False

    def render_alert(alert):
        from datetime import datetime
        icon_url = f"https://finrange.com/storage/companies/logo/svg/MOEX_{alert['symbol'].upper()}.svg"
        # стрелка above/below
        if alert["condition"] == "above":
            signal_icon = ft.Icon(name=ft.icons.ARROW_UPWARD, color=ft.colors.GREEN, size=22)
        else:
            signal_icon = ft.Icon(name=ft.icons.ARROW_DOWNWARD, color=ft.colors.RED, size=22)
        # время
        created = alert["created_at"]
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            created_fmt = dt.strftime("%M:%H  %d.%m.%Y")
        except Exception:
            created_fmt = created

        controls = [
            # тикер + иконка
            ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        content=ft.Image(
                            src=icon_url,
                            width=38,
                            height=38,
                            fit=ft.ImageFit.CONTAIN,
                        ),
                        width=38,
                        height=38,
                        border_radius=99,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                    ft.Text(
                        alert["symbol"],
                        size=20,
                        weight="bold",
                        color=C.TEXT,
                    ),
                ],
            ),
            # строка: стрелка + условие
            ft.Row(
                controls=[
                    signal_icon,
                    ft.Text(f'{alert["condition"]} {alert["value"]}', size=16, color=C.TEXT),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text(f'Создано: {created_fmt}', size=12, color=C.HINT),
        ]
        # кнопка деактивации (если алерт активен)
        if alert.get("is_active"):
            controls.append(
                ft.ElevatedButton(
                    text="Деактивировать",
                    height=32,
                    style=ft.ButtonStyle(bgcolor=C.RED, color=ft.colors.WHITE),
                    on_click=lambda e, alert_id=alert["id"]: page.run_task(handle_deactivate, alert_id),
                )
            )
        else:
            controls.append(ft.Text("Неактивно", size=12, color=C.HINT))

        return ft.Row(
            controls=[
                ft.Container(
                    expand=True,
                    padding=ft.padding.symmetric(vertical=15, horizontal=15),
                    bgcolor=ft.colors.with_opacity(0.05, C.TEXT),
                    border_radius=10,
                    content=ft.Column(
                        spacing=15,
                        controls=controls,
                        alignment=ft.MainAxisAlignment.CENTER
                    ),
                )
            ]
        )


    # --- Скролл ---
    def on_scroll(e: ft.OnScrollEvent):
        if all_loaded or loading:
            return
        if e.pixels >= e.max_scroll_extent - 100:
            page.run_task(load_alerts_page)

    all_alerts_list.on_scroll = on_scroll

    # --- Шапка ---
    header = ft.Row(
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.IconButton(
                icon=ft.icons.ARROW_BACK,
                icon_color=C.HINT,
                on_click=lambda e: page.go("/portfolio"),
                style=ft.ButtonStyle(padding=0),
            ),
            ft.Text("Все уведомления", size=20, weight="bold", color=C.TEXT),
        ]
    )

    # --- Первая загрузка ---
    page.run_task(load_alerts_page)

    return ft.Stack(
        expand=True,
        controls=[
            ft.Container(
                bgcolor=ft.colors.SURFACE,
                padding=ft.padding.only(top=20, left=20, right=20, bottom=0),
                expand=True,
                content=ft.Column(
                    expand=True,
                    spacing=20,
                    controls=[
                        header,
                        ft.Container(
                            expand=True,
                            content=all_alerts_list
                        ),
                    ]
                )
            ),
            ft.Container(
                bottom=30,
                left=0,
                right=0,
                alignment=ft.alignment.bottom_center,
                content=bottom_nav_bar(page, selected_index=1),
            ),
        ]
    )
