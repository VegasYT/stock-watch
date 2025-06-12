import flet as ft

from theme import colors as C


def loading_spinner() -> ft.ProgressRing:
    return ft.ProgressRing(
        stroke_width=3,
        width=36,
        height=36,
        color=C.PRIMARY,
        bgcolor=ft.colors.with_opacity(0.05, C.TEXT),
    )
