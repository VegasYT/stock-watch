import flet as ft
import asyncio

from services.onesignal_service import send_onesignal_id_to_server, try_register_push
import flet_onesignal as fos
from services.token_storage import save as save_tokens
from theme import colors as C
from services.auth_service import login_user
from state import session


def login_page(page: ft.Page):
    result_text = ft.Text("", color=C.HINT, size=14)

    email_ref = ft.Ref[ft.TextField]()
    password_ref = ft.Ref[ft.TextField]()
    login_btn_ref = ft.Ref[ft.ElevatedButton]()

    def toggle_password_visibility(e):
        password_field.password = not password_field.password
        icon_button.icon = (
            ft.Icons.VISIBILITY if not password_field.password else ft.Icons.VISIBILITY_OFF
        )
        password_field.update()
        icon_button.update()

    ERROR_TRANSLATIONS = {
        "value is not a valid email address": "Некорректный формат email",
        # "An email address must have an @-sign.": "Адрес должен содержать знак @",
        # "field required": "Поле обязательно для заполнения", 
        "Неверный логин или пароль": "Неверный логин или пароль",
        # "Пароль слишком короткий": "Пароль слишком короткий",
    }

    def translate_error(msg):
        for eng, rus in ERROR_TRANSLATIONS.items():
            if eng in msg:
                return rus
        return msg  # если перевод не найден — отдать оригинал

    async def handle_login(e):
        login_btn_ref.current.focus()
        page.update()
        
        res = await login_user(email.value, password_field.value)
        error_text = ""
        if not res["ok"]:
            detail = res["data"].get("detail")
            if isinstance(detail, list) and len(detail) > 0:
                # Берём сообщение из первого элемента detail
                first = detail[0]
                msg = first.get("msg") or first.get("reason") or "Ошибка валидации"
                error_text = translate_error(msg)
            elif isinstance(detail, str):
                error_text = translate_error(detail)
            else:
                error_text = "Ошибка авторизации"
            result_text.value = error_text
            result_text.color = C.RED
            result_text.update()
            return

        result_text.value = ""
        result_text.update()
        # сохраняем токены
        data = res["data"]
        session.jwt_token = data["access_token"]
        session.refresh_token = data["refresh_token"]
        await save_tokens(page, {"jwt": session.jwt_token, "refresh": session.refresh_token})

        # сразу показываем портфель
        page.go("/portfolio")

        # регистрируем пуш, если ID уже получен
        page.run_task(try_register_push)

    def go_back(e):
        page.go("/home")

    email = ft.TextField(
        label="Почта",
        label_style=ft.TextStyle(color=C.HINT),
        cursor_color=C.PRIMARY,
        border_color=C.HINT,
        focused_border_color=C.PRIMARY,
        text_style=ft.TextStyle(color=C.TEXT),
        border_radius=15,
        filled=True,
        bgcolor=ft.Colors.TRANSPARENT,
        focused_bgcolor=ft.Colors.TRANSPARENT,
        hover_color=ft.Colors.TRANSPARENT,
        ref=email_ref
    )

    password_field = ft.TextField(
        label="Пароль",
        password=True,
        label_style=ft.TextStyle(color=C.HINT),
        cursor_color=C.PRIMARY,
        border_color=C.HINT,
        focused_border_color=C.PRIMARY,
        text_style=ft.TextStyle(color=C.TEXT),
        border_radius=15,
        filled=True,
        bgcolor=ft.Colors.TRANSPARENT,
        focused_bgcolor=ft.Colors.TRANSPARENT,
        hover_color=ft.Colors.TRANSPARENT,
        ref=password_ref
    )

    icon_button = ft.IconButton(
        icon=ft.Icons.VISIBILITY_OFF,
        icon_color=C.HINT,
        on_click=toggle_password_visibility,
    )
    password_field.suffix_icon = icon_button

    login_btn = ft.ElevatedButton(
        text="Log In",
        color=C.BG,
        bgcolor=C.PRIMARY,
        width=220,
        height=50,
        on_click=handle_login,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20)),
        ref=login_btn_ref
    )

    return ft.Container(
        padding=20,
        content=ft.Column(
            controls=[
                ft.TextButton("← Home", on_click=go_back, style=ft.ButtonStyle(color=C.HINT)),
                ft.Text("Добро пожаловать", size=28, weight=ft.FontWeight.W_500, color=C.TEXT),
                ft.Text("Вход", size=36, weight=ft.FontWeight.BOLD, color=C.PRIMARY),
                email,
                password_field,
                ft.Row([login_btn], alignment=ft.MainAxisAlignment.CENTER),
                result_text,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=25,
        )
    )