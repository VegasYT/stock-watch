import flet as ft
from datetime import datetime

from theme import colors as C
from services.notify_service import create_notification, fetch_notifications, deactivate_notification
from pages.asset_page import asset_page


PAGE_SIZE = 5


def strip_emoji_from_condition(val: str) -> str:
    return val.replace("📈", "").replace("📉", "").strip()


def notify_asset_page(page: ft.Page):
    asset = page.client_storage.get("selected_asset") or {}
    stock_id = asset.get("stock_id")
    symbol = asset.get("symbol", "")

    value_field = ft.TextField(label="Значение", expand=True)
    condition_dd = ft.Dropdown(
        label="Условие",
        options=[ft.dropdown.Option("📈 above"), ft.dropdown.Option("📉 below")],
        # options=[ft.dropdown.Option("📈 above"), ft.dropdown.Option("📉 below")],
        expand=True
    )
    result_text = ft.Text("", color=C.HINT)
    submit_btn = ft.ElevatedButton(
        text="Создать уведомление",
        disabled=True,
        on_click=lambda e: page.run_task(on_submit)
    )

    # --- Состояние уведомлений ---
    alerts_list = ft.ListView(spacing=10, expand=True, on_scroll_interval=0)
    alerts_data = []  # Храним все алерты, чтобы не было дублей
    page_number = 1
    loading = False
    all_loaded = False

    def validate_inputs(e=None):
        try:
            val = float(value_field.value.strip())
            cond = condition_dd.value
            submit_btn.disabled = not cond or val is None
        except:
            submit_btn.disabled = True
        submit_btn.update()

    value_field.on_change = validate_inputs
    condition_dd.on_change = validate_inputs

    async def load_alerts_page():
        nonlocal loading, page_number, all_loaded
        if loading or all_loaded:
            return
        loading = True
        # Добавим заглушку-спиннер
        spinner = ft.Container(content=ft.ProgressRing(), alignment=ft.alignment.center)
        alerts_list.controls.append(spinner)
        page.update()
        new_alerts = await fetch_notifications(stock_id=stock_id, page=page_number, page_size=PAGE_SIZE, page_obj=page)
        alerts_list.controls.remove(spinner)

        if not new_alerts:
            if page_number == 1:
                alerts_list.controls.append(ft.Text("Нет уведомлений для этого актива", color=C.HINT))
            all_loaded = True
        else:
            for alert in new_alerts:
                if alert["id"] in {a["id"] for a in alerts_data}:
                    continue  # не дублируем
                alerts_data.append(alert)
                alerts_list.controls.append(render_alert(alert))

            if len(new_alerts) < PAGE_SIZE:
                all_loaded = True

        page_number += 1
        page.update()
        loading = False

    def render_alert(alert):
        # Определяем иконку
        if alert["condition"] == "above":
            icon = ft.Icon(
                name=ft.icons.ARROW_UPWARD,
                color=ft.colors.GREEN,
                size=22,
            )
        else:
            icon = ft.Icon(
                name=ft.icons.ARROW_DOWNWARD,
                color=ft.colors.RED,
                size=22,
            )
            
        # Преобразуем строку времени в нужный формат
        created = alert["created_at"]
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            created_fmt = dt.strftime("%M:%H  %d.%m.%Y")
        except Exception:
            created_fmt = created  # если вдруг не парсится, показываем как есть
            
        controls = [
            ft.Row(
                controls=[
                    icon,
                    ft.Text(f'{alert["condition"]} {alert["value"]}', size=16, color=C.TEXT),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            ft.Text(f'Создано: {created_fmt}', size=12, color=C.HINT),
        ]
        
        if alert["is_active"]:
            controls.append(
                ft.ElevatedButton(
                    text="Деактивировать",
                    height=30,
                    style=ft.ButtonStyle(bgcolor=C.RED, color=C.BG),
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
                    content=ft.Column(spacing=10, controls=controls, alignment=ft.MainAxisAlignment.CENTER),
                )
            ]
        )

    async def handle_deactivate(alert_id: int):
        ok = await deactivate_notification(alert_id, page=page)
        if ok:
            await reload_alerts()

    async def reload_alerts():
        nonlocal page_number, all_loaded, alerts_data
        alerts_list.controls.clear()
        page_number = 1
        all_loaded = False
        alerts_data.clear()
        await load_alerts_page()

    async def on_submit():
        try:
            value = float(value_field.value.strip())
            condition = strip_emoji_from_condition(condition_dd.value)
            if not condition:
                result_text.value = "Выберите условие"
                result_text.update()
                return
            result = await create_notification(stock_id, condition, value, page=page)
            if result == "conflict":
                result_text.value = "⚠️ Такой алерт уже есть"
            elif result:
                result_text.value = "✅ Уведомление создано"
                value_field.value = ""
                condition_dd.value = None
                value_field.update()
                condition_dd.update()
                validate_inputs()
                await reload_alerts()
            else:
                result_text.value = "❌ Ошибка при создании"
            result_text.update()
        except Exception as ex:
            result_text.value = f"Ошибка: {ex}"
            result_text.update()

    # --- Скролл обработчик ---
    def on_scroll(e: ft.OnScrollEvent):
        if all_loaded or loading:
            return
        # Если близко к концу списка — подгружаем следующую страницу
        if e.pixels >= e.max_scroll_extent - 100:
            page.run_task(load_alerts_page)

    alerts_list.on_scroll = on_scroll

    # Первая загрузка
    page.run_task(load_alerts_page)

    def on_cancel(e):
        # Просто закрываем текущий view — возвращаемся к прежнему asset_page
        if len(page.views) > 1:
            page.views.pop()
            page.update()

    return ft.Container(
        bgcolor=ft.colors.SURFACE,
        padding=ft.padding.only(top=30, left=20, right=20, bottom=10),
        expand=True,
        content=ft.Column(
            spacing=20,
            controls=[
                ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(
                            icon=ft.icons.ARROW_BACK,
                            icon_color=C.HINT,
                            on_click=on_cancel,
                            style=ft.ButtonStyle(padding=0),
                        ),
                        ft.Text(f"Уведомления для {symbol}", size=20, weight="bold", color=C.TEXT),
                    ]
                ),
                ft.Row(
                    spacing=5,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Container(content=condition_dd, expand=1, height=48, padding=0, margin=0),
                        ft.Container(content=value_field, expand=1, height=48, padding=0, margin=0),
                    ]
                ),
                ft.Row(
                    # spacing=5,
                    controls=[
                        submit_btn,
                    ]
                ),
                result_text,
                ft.Divider(height=1, color=ft.colors.with_opacity(0.1, C.TEXT)),
                ft.Container(
                    expand=True,
                    content=alerts_list
                ),
            ]
        )
    )
