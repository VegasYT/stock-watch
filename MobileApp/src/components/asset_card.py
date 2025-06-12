import flet as ft
import flet.canvas as cv
from theme import colors as C


# ---------- helpers ----------

def format_quantity(qty: int | float) -> str:
    """Форматируем количество: 1.2k, 1kk и т.д."""
    if qty >= 1_000_000:
        val = qty / 1_000_000
        suffix = "кк"
    elif qty >= 1_000:
        val = qty / 1_000
        suffix = "к"
    else:
        val = qty
        suffix = ""

    # Убираем .0, если целое
    return f"{int(val)}{suffix}" if val == int(val) else f"{val:.1f}{suffix}"


def format_price(price: float | None) -> str:
    if price is None:
        return "—"
    # Округляем до 2 знаков
    rounded = round(price, 2)

    # Разделение на целую и дробную часть
    parts = f"{rounded:.1f}".split(".")
    int_part = parts[0]
    frac_part = parts[1]

    # Вставляем тонкий пробел (U+202F) каждые 3 цифры с конца
    int_with_spaces = ""
    for i, c in enumerate(reversed(int_part)):
        if i and i % 3 == 0:
            int_with_spaces = "\u202F" + int_with_spaces  # тонкий неразрывный пробел
        int_with_spaces = c + int_with_spaces

    return f"{int_with_spaces} ₽" if frac_part == "00" else f"{int_with_spaces}.{frac_part} ₽"


def sparkline(prices: list[float], up: bool) -> ft.LineChart:
    if len(prices) < 2:
        return ft.LineChart(data_series=[], width=70, height=24)

    base_color = C.GREEN if up else C.RED

    # Flet хочет точки от меньшего X к большему, поэтому разворачиваем
    prices = list(reversed(prices))

    data = [
        ft.LineChartDataPoint(x, y) for x, y in enumerate(prices)
    ]

    return ft.LineChart(
        data_series=[
            ft.LineChartData(
                data_points=data,
                color=base_color,
                stroke_width=1,
                curved=True,
                stroke_cap_round=True,
            )
        ],
        min_x=0,
        max_x=len(prices) - 1,
        min_y=min(prices),
        max_y=max(prices),
        left_axis=None,
        bottom_axis=None,
        interactive=False,
        tooltip_bgcolor="transparent",
        expand=False,
        width=50,
        height=24,
    )

# ---------- главный виджет карточки ----------

def asset_card(asset: dict, on_click=None) -> ft.Container:
    """Карточка актива в портфеле"""

    price_per_share_text = format_price(asset["price"])
    total_sum: float | None = (
        None if asset["price"] is None else asset["price"] * asset.get("quantity", 0)
    )
    total_sum_text = format_price(total_sum)

    prices = asset.get("last_10_closes", [])
    is_up = str(asset["change"]).startswith("+")

    symbol = asset["symbol"].upper()
    image_url = f"https://finrange.com/storage/companies/logo/svg/MOEX_{symbol}.svg"

    content = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            # --- Логотип и название ---
            ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        content=ft.Image(
                            src=image_url,
                            fit=ft.ImageFit.COVER,
                            width=40,
                            height=40,
                        ),
                        width=40,
                        height=40,
                        border_radius=100,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                    ft.Column(
                        spacing=3,
                        controls=[
                            # Tикер + количество
                            ft.Row(
                                spacing=4,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Text(
                                        symbol,
                                        size=14,
                                        weight=ft.FontWeight.W_600,
                                        color=C.TEXT,
                                    ),
                                    ft.Text(
                                        f"· {format_quantity(asset.get('quantity', 0))} шт",
                                        size=10,
                                        color=C.HINT,
                                    ),
                                ],
                            ),
                            ft.Text(price_per_share_text, size=10, color=C.HINT),
                        ],
                    ),
                ],
            ),
            # --- Sparkline ---
            sparkline(prices, is_up),
            # --- Сумма и изменение ---
            ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.END,
                spacing=0,
                controls=[
                    ft.Text(total_sum_text, size=14, color=C.TEXT),
                    ft.Text(
                        f"{asset['change']} ({asset.get('change_rub', 0):+.2f} ₽)",
                        size=10,
                        color=C.GREEN if asset.get("change_rub", 0) >= 0 else C.RED,
                    ),
                ],
            ),
        ],
    )

    return ft.Container(
        # padding=ft.padding.only(left=10, top=5, right=10, bottom=20),
        padding=ft.padding.symmetric(horizontal=10, vertical=20),

        border=ft.Border(
            bottom=ft.BorderSide(width=1, color=ft.colors.with_opacity(0.05, C.TEXT))
        ),
        content=content,
        on_click=on_click,
    )