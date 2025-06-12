import flet as ft
from theme import colors as C

def chart_interval_selector(current_days_ref, reload_callback):
    interval_days = {
        "Д": 2,
        "Н": 8,
        "М": 35,
        "6М": 180,
        "Г": 365,
        "Все": 0,
    }

    def build_buttons():
        buttons = []
        for label, days in interval_days.items():
            def on_click(e, days=days):
                current_days_ref.value = days
                # Сбросить стили всех кнопок
                for b in interval_row.controls:
                    b.style.bgcolor = ft.colors.TRANSPARENT
                    b.style.color = C.TEXT
                e.control.style.bgcolor = C.TEXT
                e.control.style.color = ft.colors.BACKGROUND
                e.control.update()
                reload_callback()
            btn = ft.TextButton(
                text=label,
                style=ft.ButtonStyle(
                    bgcolor=ft.colors.TRANSPARENT,
                    color=C.TEXT,
                    padding=ft.padding.symmetric(horizontal=8, vertical=6),
                    shape=ft.RoundedRectangleBorder(radius=50),
                ),
                width=42,
                on_click=on_click,
            )
            buttons.append(btn)
        return buttons

    interval_row = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        spacing=1,
        controls=build_buttons()
    )

    return interval_row
