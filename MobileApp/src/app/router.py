import flet as ft

# from pages.terminal_page import terminal_page
from pages.auth.login_page import login_page
from pages.auth.register_page import register_page
from pages.home_page import home_page
from pages.portfolio_page import portfolio_page
from pages.asset_page import asset_page
from pages.edit_asset_page import edit_asset_page
from pages.notify_asset_page import notify_asset_page
from pages.notifications_page import notifications_page
from pages.transactions_page import transactions_page


routes = {
    "/": portfolio_page,
    "/home": home_page,
    # "/": tradingview_page,
    "/login": login_page,
    "/register": register_page,
    "/portfolio": portfolio_page,
    "/asset": asset_page,
    "/edit_asset": edit_asset_page,
    "/notify_asset": notify_asset_page,

    "/notifications": notifications_page,
    "/transactions": transactions_page,

    "/_refresh": lambda page: ft.Container(),
}


# routes["/terminal"] = terminal_page