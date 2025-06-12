import flet as ft

from theme import colors as C
from pages.auth.login_page import login_page
from pages.auth.register_page import register_page


def home_page(page: ft.Page):
    def go_to_login(e):
        page.go("/login")

    def go_to_register(e):
        page.go("/register")

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Welcome to StockWatch", size=26, weight=ft.FontWeight.W_600, color=C.TEXT),
                ft.ElevatedButton("Login", on_click=go_to_login, width=220, bgcolor=C.PRIMARY, color=C.BG),
                ft.ElevatedButton("Register", on_click=go_to_register, width=220, bgcolor=C.PRIMARY, color=C.BG),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=25,
        ),
        alignment=ft.alignment.center,
        expand=True,
    )