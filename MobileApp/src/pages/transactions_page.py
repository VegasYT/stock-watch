import flet as ft

from theme import colors as C
from services.portfolio_service import fetch_asset_info, update_portfolio_with_transactions
from components.bottom_nav_bar import bottom_nav_bar
from pages.edit_asset_page import build_transaction_row, map_tx_type_for_dropdown

PAGE_SIZE = 5

def transactions_page(page: ft.Page):
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
            # portfolio_id = -1 для всех транзакций (тут нужен весь список)
            fresh = await fetch_asset_info(-1, page=page)
            new_transactions = fresh.get("transactions", []) or []
            new_transactions.sort(key=lambda tx: tx["timestamp"], reverse=True)
            transactions_list.controls.remove(spinner)

            count = 0
            for tx in new_transactions:
                if tx["id"] in {t["id"] for t in transactions_data}:
                    continue
                transactions_data.append(tx)

                row = build_transaction_row(page, tx_data=tx, on_delete=None)

                async def on_save(e, row=row, tx=tx):
                    tx_data = row.get_tx_data()
                    if tx_data and "id" in tx_data:
                        ok = await update_portfolio_with_transactions(
                            asset_id=tx["portfolio_id"],
                            quantity=0,
                            add=[],
                            delete=[],
                            update=[tx_data],
                            page=page
                        )
                        if ok:
                            page.snack_bar = ft.SnackBar(ft.Text("Изменения сохранены!"), open=True)
                        else:
                            page.snack_bar = ft.SnackBar(ft.Text("Ошибка при сохранении"), open=True)
                        page.update()

                # Кнопка "Сохранить" — на всю ширину блока (expand + Row)
                save_btn_row = ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            text="Сохранить",
                            bgcolor=C.GREEN,
                            color=ft.colors.WHITE,
                            height=28,
                            expand=True,
                            on_click=on_save
                        )
                    ],
                    expand=True,
                )

                # Тикер по центру, снизу блока
                ticker_row = ft.Row(
                    controls=[
                        ft.Text(f"Тикер: {tx.get('symbol','')}", size=12, color=C.HINT)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    expand=True,
                )

                # Вставляем В КОНЕЦ блока
                if isinstance(row.content, ft.Column):
                    row.content.controls.append(save_btn_row)
                    row.content.controls.append(ticker_row)
                elif hasattr(row.content, "controls"):
                    row.content.controls.append(save_btn_row)
                    row.content.controls.append(ticker_row)
                else:
                    if hasattr(row, "controls"):
                        row.controls.append(save_btn_row)
                        row.controls.append(ticker_row)


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

    async def refresh_page(e=None):
        nonlocal tx_all_loaded, tx_loading, tx_page, transactions_data
        tx_all_loaded = False
        tx_loading = False
        tx_page = 1
        transactions_data.clear()
        transactions_list.controls.clear()
        page.update()
        await load_transactions_page()

    transactions_list.on_scroll = on_tx_scroll
    page.run_task(load_transactions_page)

    # ---- Header с кнопкой обновления у правого края
    header = ft.Row(
        spacing=20,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.IconButton(
                        icon=ft.icons.ARROW_BACK,
                        icon_color=C.HINT,
                        on_click=lambda e: page.go("/portfolio"),
                        style=ft.ButtonStyle(padding=0),
                    ),
                    ft.Text("Все транзакции", size=20, weight="bold", color=C.TEXT),
                ],
            ),
            ft.IconButton(
                icon=ft.icons.REFRESH,
                icon_color=C.HINT,
                bgcolor=ft.colors.with_opacity(0.13, C.TEXT),
                style=ft.ButtonStyle(
                    padding=2,
                    shape=ft.CircleBorder(),
                ),
                tooltip="Обновить",
                on_click=lambda e: page.run_task(refresh_page),
            ),
        ]
    )

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
                            content=transactions_list
                        ),
                    ]
                )
            ),
            ft.Container(
                bottom=30,
                left=0,
                right=0,
                alignment=ft.alignment.bottom_center,
                content=bottom_nav_bar(page, selected_index=2),
            ),
        ]
    )
