import flet as ft
import time
from datetime import datetime, timedelta
from threading import Timer
from flet import ChartCirclePoint, LineChartData, LineChartDataPoint
from flet import GestureDetector, DragEndEvent

from services.portfolio_service import fetch_asset_info, portfolio_cache_is_valid
from theme import colors as C
from services.price_history_service import fetch_price_history
from components.chart_interval_selector import chart_interval_selector
from components.spinner import loading_spinner
# from pages.edit_asset_page import edit_asset_page


def asset_page(page: ft.Page):
    # asset = page.client_storage.get("selected_asset") or {}
    raw_asset = page.client_storage.get("selected_asset") or {}
    asset = dict(raw_asset)  # локальная копия
    stock_id = asset.get("stock_id")

    is_active = True  # флаг, жива ли страница
    last_event_timer = None  # таймер для hover

    symbol = asset.get("symbol", "")
    name = asset.get("shortname", "")
    price = asset.get("price")
    change = asset.get("change", "")
    is_up = str(change).startswith("+")
    change_color = C.GREEN if is_up else C.RED

    change_text_ref = ft.Ref[ft.Text]()
    current_days = ft.Ref[int]()
    current_days.value = 35

    def handle_swipe_end(e: DragEndEvent):
        try:
            if e.velocity_x and e.velocity_x > 1000:
                safe_pop_to_portfolio()
        except Exception as ex:
            print("Ошибка обработки свайпа:", ex)

    # Шапка с GestureDetector
    top_bar = ft.Container(
        bgcolor=ft.colors.with_opacity(0.9, ft.colors.SURFACE_VARIANT),
        # padding=20,
        padding=ft.padding.only(top=40, left=20, right=20, bottom=20),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.START,
            controls=[
                ft.IconButton(
                    icon=ft.icons.ARROW_BACK,
                    icon_color=C.TEXT,
                    # on_click=lambda e: page.go("/portfolio"),
                    on_click=lambda e: safe_pop_to_portfolio(),
                ),
                ft.Container(
                    margin=ft.margin.only(left=10),
                    expand=True,
                    content=ft.Column(
                        spacing=2,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Text(name, size=18, weight="bold", color=C.TEXT),
                            ft.Text(symbol, size=12, color=ft.colors.with_opacity(0.7, C.TEXT)),
                        ],
                    ),
                ),
                ft.IconButton(
                    icon=ft.icons.NOTIFICATIONS,
                    icon_color=C.TEXT,
                    on_click=lambda e: push_notify_asset_view(),
                ),
                ft.IconButton(
                    icon=ft.icons.EDIT,
                    icon_color=C.TEXT,
                     on_click=lambda e: push_edit_asset_view()
                ),
            ],
        ),
    )

    color_hex = asset.get("dominant_color")
    if color_hex:
        top_bar.bgcolor = ft.colors.with_opacity(0.5, color_hex)

    top_bar_swipe = GestureDetector(
        # on_horizontal_drag_start=lambda e: setattr(page, "swipe_start_x", e.global_position.x),
        on_horizontal_drag_end=handle_swipe_end,
        content=top_bar,
    )

    price_block = ft.Column(
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        visible=True,
        controls=[
            ft.Text(f"{price} ₽", size=22, weight="bold", color=C.TEXT),
            ft.Text(f"{change} ({asset.get('change_rub', 0):+.2f} ₽)", size=16, color=change_color, ref=change_text_ref)
        ],
    )

    hover_dt = ft.Text("", size=16, color=C.HINT, text_align=ft.TextAlign.CENTER)
    hover_price = ft.Text("", size=22, weight="bold", color=C.TEXT, text_align=ft.TextAlign.CENTER)

    hover_block = ft.Column(
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        visible=False,
        controls=[hover_dt, hover_price],
    )

    chart_container = ft.Container(
        height=250,
        expand=True,
        alignment=ft.alignment.center,
        padding=0,
        border=ft.Border(
            top=ft.BorderSide(1, ft.colors.with_opacity(0.1, C.TEXT)),
            bottom=ft.BorderSide(1, ft.colors.with_opacity(0.1, C.TEXT)),
        ),
        content=loading_spinner()
    )


    def safe_pop_to_portfolio():
        cache_valid = portfolio_cache_is_valid()

        # ---------- 1. Кэш ПРОСРОЧЕН ---------- #
        if not cache_valid:
            # Уже на портфеле ─ удаляем asset-view’ы
            while len(page.views) > 1 and page.views[-1].route == "/asset":
                page.views.pop()
            page.update()

            # Полукостыль
            if page.route == "/":
                page.go("/portfolio")
            elif page.route == "/portfolio":
                page.go("/")

        # ---------- 2. Кэш ЕЩЁ ВАЛИДЕН ---------- #
        while len(page.views) > 1 and page.views[-1].route == "/asset":
            page.views.pop()

        page.update()


    def push_edit_asset_view():
        """Открыть экран редактирования, удаляя старый /edit_asset из стека вручную."""
        from pages.edit_asset_page import edit_asset_page

        # Удалим старый /edit_asset вручную (без reassignment)
        for i in reversed(range(len(page.views))):
            if page.views[i].route == "/edit_asset":
                page.views.pop(i)

        # Добавим новый
        page.views.append(
            ft.View("/edit_asset", controls=[edit_asset_page(page)], padding=0)
        )
        page.update()


    def push_notify_asset_view():
        from pages.notify_asset_page import notify_asset_page

        for i in reversed(range(len(page.views))):
            if page.views[i].route == "/notify_asset":
                page.views.pop(i)

        page.views.append(
            ft.View("/notify_asset", controls=[notify_asset_page(page)], padding=0)
        )
        page.update()


    def get_bottom_labels(data: list[dict]):
        if not data or len(data) < 2:
            return []

        first_date = data[0]["date"]
        last_date = data[-1]["date"]
        total_range = last_date - first_date

        # Логика выбора "единицы" для уникальности подписи
        if total_range <= timedelta(days=2):
            label_getter = lambda dt: (dt.year, dt.month, dt.day, dt.hour)
            fmt = "%H:00"
        elif total_range <= timedelta(days=30):
            label_getter = lambda dt: (dt.year, dt.month, dt.day)
            fmt = "%d.%m"
        elif total_range <= timedelta(days=200):
            label_getter = lambda dt: (dt.year, dt.month, dt.day)
            fmt = "%d %b"
        elif total_range <= timedelta(days=370):
            label_getter = lambda dt: (dt.year, dt.month)
            fmt = "%b"
        else:
            label_getter = lambda dt: dt.year
            fmt = "%Y"

        # Собираем все уникальные значения и их индексы
        labels_candidates = []
        seen = set()
        for i, row in enumerate(data):
            dt = row["date"]
            key = label_getter(dt)
            if key not in seen:
                seen.add(key)
                labels_candidates.append((i, dt.strftime(fmt)))

        # Оставляем не более 5 равномерно распределённых меток
        N = min(5, len(labels_candidates))
        if N == 0:
            return []
        step = (len(labels_candidates) - 1) / (N - 1) if N > 1 else 1
        selected = [labels_candidates[round(i * step)] for i in range(N)]

        labels = [
            ft.ChartAxisLabel(
                value=idx,
                label=ft.Text(label_text, size=12, color=ft.colors.with_opacity(0.6, C.TEXT))
            )
            for idx, label_text in selected
        ]
        return labels


    async def load_chart():
        chart_container.content = loading_spinner()
        page.update()

        if not stock_id:
            chart_container.content = ft.Text("Нет stock_id", color=C.RED)
            page.update()
            return

        # raw = await fetch_price_history(stock_id, days=current_days.value, count=150)
        history = await fetch_price_history(stock_id, days=current_days.value, count=100, page=page)
        # history = await fetch_price_history(stock_id, days=current_days.value, count=150)
        raw = history.get("data", [])
        if not raw:
            chart_container.content = ft.Text("Нет данных", color=C.RED)
            page.update()
            return


        data = []
        for row in raw:
            try:
                date = datetime.fromisoformat(row["date"])
                close = float(row["close"])
                data.append({"date": date, "close": close})
            except:
                continue

        data.sort(key=lambda r: r["date"])
        tx_radius = max(1, len(data) // 30)
        points = [LineChartDataPoint(x=i, y=r["close"]) for i, r in enumerate(data)]

        transactions = asset.get("transactions", [])
        marker_data_series = []
        tx_spot_indices = {}

        min_price = min(r["close"] for r in data)
        max_price = max(r["close"] for r in data)

        if data:
            first_date = data[0]["date"]
            last_date = data[-1]["date"]

        # print("LEN DATA:", len(raw))
        # print("LEN AFTER FILTER:", len(data))
        # print("MIN:", min_price, "MAX:", max_price)
        # print("min_y:", min_y, "max_y:", max_y)

        for tx in transactions:
            try:
                dt = datetime.fromisoformat(tx["timestamp"].replace("Z", "+00:00")).replace(tzinfo=None)
                if dt < first_date or dt > last_date:
                    continue

                tx_type = tx["type"]
                tx_price = float(tx["price"])
                color = C.GREEN if tx_type == "buy" else C.RED

                min_price = min(min_price, tx_price)
                max_price = max(max_price, tx_price)

                idx = min(
                    range(len(data)),
                    key=lambda i: abs((data[i]["date"] - dt).total_seconds())
                )

                tx_spot_indices[idx] = (tx_price, tx_type)

                marker_data_series.append(
                    LineChartData(
                        data_points=[LineChartDataPoint(x=idx, y=tx_price)],
                        stroke_width=0,
                        curved=False,
                        point=ChartCirclePoint(
                            color=ft.colors.with_opacity(0.7, color),
                            radius=7,
                            stroke_color=ft.colors.with_opacity(0.7, color),
                            stroke_width=0.8,
                        ),
                        color=color,
                    )
                )

            except Exception as e:
                print("Ошибка в транзакции:", tx, e)

        price_range = max_price - min_price if max_price > min_price else 1
        min_y = min_price - price_range * 0.05
        max_y = max_price + price_range * 0.05

        bottom_labels = get_bottom_labels(data)
        

        hover_line_layer = ft.Ref[LineChartData]()

        base_series = LineChartData(
            data_points=points,
            stroke_width=2,
            curved=True,
            # curved=len(points) < 100,
            color=ft.colors.WHITE,
            stroke_cap_round=True,
        )

        def update_chart():
            if not chart_ready:
                return
            
            # if chart in page.controls or chart_container.content == chart:
            if chart_container.content == chart:
                chart.data_series = [
                    base_series,
                    *marker_data_series,
                    *([hover_line_layer.current] if hover_line_layer.current else [])
                ]
                chart.update()

        
        last_hover_update = [0]      # Список — чтобы не мучиться с nonlocal
        HOVER_THROTTLE = 0.05        # 50 мс

        def handle_chart_event(e: ft.LineChartEvent):
            nonlocal last_event_timer

            if not is_active:
                return

            reset_events = {
                "PointerExitEvent", "PanCancelEvent", "TapUpEvent", "TapCancelEvent", "LongPressEnd",
            }

            def do_reset():
                if not is_active:
                    return
                hover_block.visible = False
                price_block.visible = True
                hover_line_layer.current = None
                update_chart()
                page.update()

            # Сброс состояния при любом событии ухода с графика
            if e.type in reset_events or (e.type == "PanEndEvent" and (not e.spots or len(e.spots) == 0)):
                if last_event_timer:
                    last_event_timer.cancel()
                do_reset()
                return

            # Троттлинг наведения — обрабатываем не чаще, чем раз в 0.2 сек
            if e.spots and len(e.spots) > 0:
                now = time.monotonic()
                if now - last_hover_update[0] < HOVER_THROTTLE:
                    return
                last_hover_update[0] = now

                if last_event_timer:
                    last_event_timer.cancel()
                    last_event_timer = None

                spot = e.spots[0]
                idx = spot["spot_index"] if isinstance(spot, dict) else spot.spot_index
                r = data[idx]
                hover_dt.value = r["date"].strftime("%d.%m.%Y %H:%M")
                hover_price.value = f"{r['close']:.2f} ₽"
                hover_block.visible = True
                price_block.visible = False

                tx_hit = None
                for offset in range(-tx_radius, tx_radius + 1):
                    check_idx = idx + offset
                    if 0 <= check_idx < len(data) and check_idx in tx_spot_indices:
                        tx_hit = tx_spot_indices[check_idx]
                        break

                if tx_hit:
                    price_at_idx, tx_type = tx_hit
                    tx_color = C.GREEN if tx_type == "buy" else C.RED
                    hover_line_layer.current = LineChartData(
                        data_points=[
                            LineChartDataPoint(x=0, y=price_at_idx),
                            LineChartDataPoint(x=len(data) - 1, y=price_at_idx),
                        ],
                        stroke_width=1,
                        curved=False,
                        dash_pattern=[4, 4],
                        color=ft.colors.with_opacity(0.5, tx_color),
                    )
                else:
                    hover_line_layer.current = None

                update_chart()
                page.update()
            else:
                # Если пришёл ивент без spots — сбросить ховер
                do_reset()


        # обновим change
        if "id" in asset:
            asset["change"] = history.get("change", "—")
            asset["change_rub"] = history.get("change_rub", 0)
            change_rub = history.get("change_rub", 0)
            change_color = C.GREEN if change_rub >= 0 else C.RED
            if change_text_ref.current:
                change_text_ref.current.value = f"{asset['change']}% ({asset['change_rub']:+.2f} ₽)"
                change_text_ref.current.color = change_color

            page.update() 


        chart = ft.LineChart(
            data_series=[base_series, *marker_data_series],
            # bottom_axis=ft.ChartAxis(labels=bottom_labels, labels_size=32),
            tooltip_bgcolor=ft.colors.with_opacity(0.75, ft.colors.BLACK),
            tooltip_rounded_radius=2,
            min_y=min_y,
            max_y=max_y,
            min_x=0,
            max_x=len(data) - 1,
            interactive=True,
            expand=True,
            height=250,
            bottom_axis=ft.ChartAxis(
                labels         = bottom_labels,
                labels_interval= 1,
                labels_size    = 32,
            ),
            on_chart_event=handle_chart_event,
        )

        chart_container.content = chart
        chart_ready = True
        page.update()

    def reload_chart():
        page.run_task(load_chart)

    async def enrich_asset_data():
        if not raw_asset or "id" not in raw_asset:
            return
        extra = await fetch_asset_info(raw_asset["id"], page=page)
        if extra:
            asset.update(extra)
            # page.client_storage.set("selected_asset", asset)
            await page.client_storage.set_async("selected_asset", asset)
            page.update()

    page.run_task(enrich_asset_data)


    interval_buttons = chart_interval_selector(current_days, reload_chart)

    info_block = ft.GestureDetector(
        on_horizontal_drag_end=handle_swipe_end,
        content=ft.Row(
            controls=[
                ft.Container(
                    expand=True,
                    margin=ft.margin.only(left=20, right=20, top=12, bottom=20),
                    padding=20,
                    border_radius=12,
                    bgcolor=ft.colors.with_opacity(0.05, C.TEXT),
                    content=ft.Column(
                        spacing=14,
                        horizontal_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text("Полное название", size=12, color=ft.colors.with_opacity(0.5, C.TEXT)),
                                    ft.Text(asset.get("name", "—"), size=14, color=C.TEXT),
                                ],
                            ),
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text("ISIN", size=12, color=ft.colors.with_opacity(0.5, C.TEXT)),
                                    ft.Text(asset.get("isin", "—"), size=14, color=C.TEXT),
                                ],
                            ),
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text("Эмитент", size=12, color=ft.colors.with_opacity(0.5, C.TEXT)),
                                    ft.Text(asset.get("emitent_title", "—"), size=14, color=C.TEXT),
                                ],
                            ),
                        ],
                    ),
                )
            ]
        )
    )

    page.run_task(load_chart)

    return ft.Container(
        bgcolor=ft.colors.SURFACE,
        expand=True,
        content=ft.Column(
            spacing=0,
            controls=[
                GestureDetector(
                    on_horizontal_drag_end=handle_swipe_end,
                    content=ft.Column(
                        spacing=0,
                        controls=[
                            top_bar_swipe,
                            ft.Container(
                                padding=20,
                                content=ft.Stack(
                                    controls=[
                                        ft.Row([price_block], alignment=ft.MainAxisAlignment.START),
                                        ft.Row([hover_block], alignment=ft.MainAxisAlignment.CENTER),
                                    ]
                                ),
                            ),
                        ],
                    ),
                ),
                chart_container,
                ft.Container(height=12),
                interval_buttons,
                info_block,
            ],
        )
    )