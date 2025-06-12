import threading
import flet as ft
from datetime import datetime

from state import session
from theme import colors as C
from services.portfolio_service import (
    fetch_asset_info,
    invalidate_portfolio_cache,
    update_portfolio_with_transactions,
    delete_asset,
)
from pages.asset_page import asset_page


PAGE_SIZE = 5


def validate_input(field: ft.TextField):
    text = field.value.strip().replace(",", ".")
    try:
        num = float(text)
        if num < 0:
            field.error_text = "Число не может быть отрицательным"
        elif num > 999_999_999:
            field.error_text = "Максимум 999 999 999"
        else:
            parts = text.split(".")
            if len(parts) == 2 and len(parts[1]) > 5:
                field.error_text = "Не более 5 знаков после запятой"
            else:
                field.error_text = None
    except ValueError:
        field.error_text = "Введите корректное число"
    field.update()


def map_tx_type_for_dropdown(tx_type: str) -> str:
    # Для новых (с эмодзи) — ничего не делаем
    if tx_type in ("🔴buy", "🟢sell"):
        return tx_type
    # Для старых — маппим вручную
    if tx_type == "buy":
        return "🔴buy"
    if tx_type == "sell":
        return "🟢sell"
    return tx_type  # если вдруг какой-то неожиданный вариант


def strip_emoji_from_tx_type(val: str) -> str:
    return val.replace("🔴", "").replace("🟢", "")


def build_transaction_row(page, tx_data=None, on_delete=None, is_new=False):
    is_editing = tx_data is not None

    tx_type = ft.Dropdown(
        value=map_tx_type_for_dropdown(tx_data["type"]) if is_editing else None,
        options=[ft.dropdown.Option("🔴buy"), ft.dropdown.Option("🟢sell")],
        expand=1
    )
    price = ft.TextField(value=tx_data["price"] if is_editing else "", expand=1)
    qty = ft.TextField(value=tx_data["quantity"] if is_editing else "", expand=1)

    if is_editing:
        dt = datetime.fromisoformat(tx_data["timestamp"].replace("Z", "+00:00"))
        date_val = dt.strftime("%Y-%m-%d")
        time_val = dt.strftime("%H:%M")
    else:
        date_val = ""
        time_val = ""

    date_field = ft.TextField(value=date_val, expand=1, read_only=is_new)
    time_field = ft.TextField(value=time_val, expand=1)

    error_text = ft.Text(value="", color=ft.colors.RED, size=12)

    def combined_time_handler(original_val):
        def handler(e):
            val = ''.join(filter(str.isdigit, e.control.value))[:4]
            if len(val) >= 3:
                val = val[:2] + ':' + val[2:]
            e.control.value = val

            error_msg = ""
            if len(val) == 5 and ':' in val:
                try:
                    h, m = map(int, val.split(":"))
                    if not (0 <= h <= 23 and 0 <= m <= 59):
                        error_msg = "Неверное время: допустимо 00:00 – 23:59"
                except:
                    error_msg = "Неверный формат времени"
            elif val != "":
                error_msg = "Формат: ЧЧ:ММ"

            error_text.value = error_msg

            if is_editing:
                current = val.strip()
                e.control.border_color = ft.colors.AMBER_300 if current != original_val else None

            page.update()
        return handler

    time_field.on_change = combined_time_handler(time_val)

    def highlight_border(field, original_val):
        def handler(e):
            if is_editing:
                current = field.value.strip()
                field.border_color = ft.colors.AMBER_300 if current != original_val else None
                field.update()
        return handler

    if is_editing:
        price.on_change = highlight_border(price, tx_data["price"])
        qty.on_change = highlight_border(qty, tx_data["quantity"])
        date_field.on_change = highlight_border(date_field, date_val)
        tx_type.on_change = lambda e: tx_type.update()

    date_picker = ft.DatePicker()

    def pick_date(e):
        date_picker.open = True
        page.update()

    def on_date_change(e):
        if date_picker.value:
            date_field.value = date_picker.value.strftime("%Y-%m-%d")
            page.update()

    date_picker.on_change = on_date_change
    pick_date_btn = ft.IconButton(icon=ft.icons.CALENDAR_MONTH, on_click=pick_date)
    page.overlay.append(date_picker)

    delete_control = ft.Row([
        ft.ElevatedButton(
            text="Удалить",
            bgcolor=C.RED,
            color=ft.colors.WHITE,
            expand=True,
            height=25,
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(vertical=4),
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
            on_click=on_delete
        )
    ], expand=True)

    container = ft.Container(
        padding=10,
        bgcolor=ft.colors.with_opacity(0.05, C.TEXT),
        border_radius=10,
        content=ft.Column(spacing=8, controls=[
            ft.Row(spacing=10, controls=[
                ft.Column(expand=1, controls=[ft.Text("Тип транзакции", size=12, color=C.HINT), tx_type]),
                ft.Column(expand=1, controls=[ft.Text("Цена", size=12, color=C.HINT), price]),
                ft.Column(expand=1, controls=[ft.Text("Количество", size=12, color=C.HINT), qty]),
            ]),
            ft.Row(spacing=10, controls=[
                ft.Column(expand=1, controls=[ft.Text("Дата", size=12, color=C.HINT), date_field]),
                ft.Column(expand=1, controls=[ft.Text("Время", size=12, color=C.HINT), time_field]),
                ft.Column(expand=1, controls=[ft.Text("Календарь", size=12, color=C.HINT), pick_date_btn]),
            ]),
            error_text,
            delete_control
        ])
    )

    def get_tx_data():
        try:
            full_dt = datetime.strptime(f"{date_field.value} {time_field.value}", "%Y-%m-%d %H:%M")
            tx = {
                "type": strip_emoji_from_tx_type(tx_type.value),
                "price": float(price.value),
                "quantity": float(qty.value),
                "timestamp": full_dt.isoformat() + "Z"
            }
            if is_editing:
                tx["id"] = tx_data["id"]
            return tx
        except Exception as err:
            print("Ошибка парсинга транзакции:", err)
            return None

    container.get_tx_data = get_tx_data
    return container

def edit_asset_page(page: ft.Page):
    asset = page.client_storage.get("selected_asset") or {}
    asset_id = asset.get("id")
    quantity = asset.get("quantity")
    deleted_transaction_ids = []

    quantity_field = ft.TextField(
        label="Количество",
        value=str(quantity),
        width=200,
        on_change=lambda e: validate_input(quantity_field),
    )

    transactions_list = ft.ListView(spacing=10, expand=True, on_scroll_interval=0)
    transactions_data = []
    tx_page = 1
    tx_loading = False
    tx_all_loaded = False

    async def load_transactions_page():
        nonlocal tx_loading, tx_page, tx_all_loaded
        if tx_loading or tx_all_loaded:
            return
        tx_loading = True
        spinner = ft.Container(content=ft.ProgressRing(), alignment=ft.alignment.center)
        transactions_list.controls.append(spinner)
        page.update()

        try:
            fresh = await fetch_asset_info(asset_id, page=page)
            new_transactions = fresh.get("transactions", []) or []
            new_transactions.sort(key=lambda tx: tx["timestamp"], reverse=True)
            transactions_list.controls.remove(spinner)

            count = 0
            for tx in new_transactions:
                if tx["id"] in {t["id"] for t in transactions_data}:
                    continue
                transactions_data.append(tx)

                row_ref = {}
                def handle_delete(e, ref=row_ref, tx_id=tx["id"]):
                    row = ref["row"]
                    if row in transactions_list.controls:
                        transactions_list.controls.remove(row)
                    deleted_transaction_ids.append(tx_id)
                    page.update()

                row = build_transaction_row(page, tx_data=tx, on_delete=handle_delete)
                row_ref["row"] = row
                transactions_list.controls.append(row)
                count += 1

            if count < PAGE_SIZE:
                tx_all_loaded = True
        except Exception as ex:
            print("Ошибка загрузки транзакций:", ex)
        page.update()
        tx_loading = False

    def on_tx_scroll(e: ft.OnScrollEvent):
        if tx_all_loaded or tx_loading:
            return
        if e.pixels >= e.max_scroll_extent - 100:
            page.run_task(load_transactions_page)

    transactions_list.on_scroll = on_tx_scroll
    page.run_task(load_transactions_page)

    def add_transaction_field():
        row = build_transaction_row(
            page,
            tx_data=None,
            is_new=True,
            on_delete=lambda e: (
                transactions_list.controls.remove(row),
                page.update()
            )
        )
        transactions_list.controls.insert(0, row)
        return row

    def on_add_transaction(e):
        add_transaction_field()
        page.update()

    async def on_save_async(e):
        try:
            validate_input(quantity_field)
            if quantity_field.error_text:
                return
            new_qty = float(quantity_field.value.strip().replace(",", "."))
            add_tx, update_tx = [], []

            for row in transactions_list.controls:
                if not hasattr(row, "get_tx_data"):
                    continue
                tx = row.get_tx_data()
                if tx:
                    (update_tx if "id" in tx else add_tx).append(tx)

            ok = await update_portfolio_with_transactions(
                asset_id,
                new_qty,
                add_tx,
                deleted_transaction_ids,
                update_tx,
                page=page
            )

            if not ok:
                return
            invalidate_portfolio_cache()
            fresh = await fetch_asset_info(asset_id, page=page) or {}
            merged = {**asset, **fresh}
            merged["quantity"] = new_qty

            def delayed_finalize():
                try:
                    page.client_storage.set("selected_asset", merged)
                except Exception as ex:
                    print("Ошибка записи client_storage:", ex)
                if page.views:
                    page.views.pop()
                page.views.append(ft.View("/asset", controls=[asset_page(page)], padding=0))
                page.update()

            threading.Timer(0.1, delayed_finalize).start()

        except Exception as ex:
            print("Ошибка при сохранении:", ex)
            quantity_field.error_text = "Ошибка ввода"
            page.update()

    def on_save(e):
        page.run_task(on_save_async, e)

    confirm_dialog = ft.AlertDialog(modal=True)

    async def _delete_asset_async(e=None):
        confirm_dialog.open = False
        page.dialog = None
        page.update()

        ok = await delete_asset(asset_id, page=page)
        if ok:
            invalidate_portfolio_cache()
            page.go("/portfolio")

    def on_delete_asset(e):
        confirm_dialog.title = ft.Text("Удалить актив?")
        confirm_dialog.content = ft.Text("Вы уверены, что хотите удалить актив из портфеля?")
        confirm_dialog.actions = [
            ft.TextButton("Отмена", on_click=lambda e: _close_dialog()),
            ft.TextButton(
                "Удалить",
                style=ft.ButtonStyle(color=C.RED),
                on_click=lambda e: page.run_task(_delete_asset_async)
            ),
        ]
        confirm_dialog.actions_alignment = ft.MainAxisAlignment.END
        if confirm_dialog not in page.overlay:
            page.overlay.append(confirm_dialog)
        page.dialog = confirm_dialog
        confirm_dialog.open = True
        page.update()

    def _close_dialog():
        page.dialog.open = False
        page.update()

    def on_cancel(e):
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
                        ft.Text("Редактировать актив", size=20, weight="bold"),
                    ]
                ),
                quantity_field,
                ft.Row(
                    spacing=10,
                    controls=[
                        ft.ElevatedButton("Сохранить", on_click=on_save),
                        ft.TextButton("Удалить актив", on_click=on_delete_asset, style=ft.ButtonStyle(color=C.RED)),
                    ],
                ),
                ft.ElevatedButton("Добавить транзакцию", on_click=on_add_transaction),
                ft.Container(
                    content=transactions_list,
                    # height=400,
                    expand=True,
                    # bgcolor=ft.colors.with_opacity(0.02, C.TEXT),
                    # border_radius=10,
                    # padding=10,
                )
            ]
        )
    )
