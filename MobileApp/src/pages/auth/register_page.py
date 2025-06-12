import flet as ft

from theme import colors as C
from services.auth_service import register_user


def register_page(page: ft.Page):
    result_text = ft.Text("", color=C.HINT, size=14)

    ERROR_TRANSLATIONS = {
        "value is not a valid email address": "Некорректный формат email",
        "An email address must have an @-sign.": "Адрес должен содержать знак @",
        "field required": "Поле обязательно для заполнения",
        "Пароль должен быть не короче 8 символов": "Пароль должен быть не короче 8 символов",
        "Пользователь с таким email уже существует": "Пользователь с таким email уже существует",
        "Ник должен быть не короче 3 символов": "Ник должен быть не короче 3 символов",
        "Ник должен содержать только латинские буквы и цифры, без пробелов и спецсимволов": "Ник должен содержать только латинские буквы и цифры, без пробелов и спецсимволов",
        "Ник должен быть не длиннее 16 символов": "Ник должен быть не длиннее 16 символов",
        "Пароль должен быть не длиннее 32 символов": "Пароль должен быть не длиннее 32 символов",
    }

    def translate_error(msg):
        for eng, rus in ERROR_TRANSLATIONS.items():
            if eng in msg:
                return rus
        return msg

    async def handle_register(e):
        res = await register_user(email.value, nickname.value, password_field.value)
        if res["ok"]:
            result_text.value = "Регистрация успешна!"
            result_text.color = C.GREEN
        else:
            detail = res["data"].get("detail")
            error_text = ""
            if isinstance(detail, list) and len(detail) > 0:
                msg = detail[0].get("msg") or detail[0].get("reason") or "Ошибка валидации"
                error_text = translate_error(msg)
            elif isinstance(detail, str):
                error_text = translate_error(detail)
            else:
                error_text = "Ошибка регистрации"
            result_text.value = error_text
            result_text.color = C.RED
        result_text.update()


    def go_back(e):
        page.go("/home")

    back_btn = ft.TextButton("← Home", on_click=go_back, style=ft.ButtonStyle(color=C.HINT))

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
    )

    nickname = ft.TextField(
        label="Ник",
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
    )

    def toggle_password_visibility(e):
        password_field.password = not password_field.password
        icon_button.icon = (
            ft.Icons.VISIBILITY if not password_field.password else ft.Icons.VISIBILITY_OFF
        )
        password_field.update()
        icon_button.update()

    icon_button = ft.IconButton(icon=ft.Icons.VISIBILITY_OFF, icon_color=C.HINT, on_click=toggle_password_visibility)
    password_field.suffix_icon = icon_button

    register_btn = ft.ElevatedButton(
        text="Создать аккаунт",
        on_click=handle_register,
        color=C.BG,
        bgcolor=C.PRIMARY,
        width=220,
        height=50,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20)),
    )

    return ft.Container(
        padding=10,
        content=ft.Column(
            controls=[
                back_btn,
                ft.Text("Создать аккаунт", size=28, weight=ft.FontWeight.W_500, color=C.TEXT),
                ft.Text("Регистрация", size=36, weight=ft.FontWeight.BOLD, color=C.PRIMARY),
                email,
                nickname,
                password_field,
                ft.Row([register_btn], alignment=ft.MainAxisAlignment.CENTER),
                result_text,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=25,
        )
    )
