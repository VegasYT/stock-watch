import threading
import asyncio
from typing import Set
import time
import math
import random

import flet as ft
from flet import DragUpdateEvent, OnScrollEvent

from pages.asset_page import asset_page
from components.asset_card import asset_card
from components.spinner import loading_spinner
from services.onesignal_service import send_onesignal_id_to_server
from services.portfolio_service import (
    add_to_portfolio,
    fetch_portfolio,
    invalidate_portfolio_cache,
    portfolio_cache_is_valid,
    search_stocks,
    delete_asset,
)
from services.token_storage import save as save_to_storage
from state import session
from theme import colors as C


PAGE_SIZE = 12
load_sem = threading.Semaphore()


def portfolio_page(page: ft.Page):
    # локальное состояние
    drag_start_y = 0
    is_refreshing = False
    current_page = 1
    loading_more = False
    all_loaded = False
    loaded_ids: Set[int] = set()
    is_search_mode = False

    if not hasattr(page, "portfolio_selection_mode"):
        page.portfolio_selection_mode = False
    if not hasattr(page, "portfolio_highlighted_ids"):
        page.portfolio_highlighted_ids = set()
    
    highlighted_ids = page.portfolio_highlighted_ids

    card_refs: dict[int, ft.Ref] = {}
    pending_updates: set[int] = set()
    update_scheduled = False
    click_lock = False

    shake_anim_timer = None
    shake_anim_phase = 0
    shake_angles = {}

    if not portfolio_cache_is_valid():
        session.cached_portfolio = None
    cached_assets = session.cached_portfolio

    # базовый UI
    page.theme = ft.Theme(
        font_family="IBMPlexSans",
        scrollbar_theme=ft.ScrollbarTheme(thickness=0, thumb_color=ft.colors.TRANSPARENT),
    )

    search_ref = ft.Ref[ft.TextField]()
    title = ft.Text("Активы", size=14, weight=ft.FontWeight.W_600, color=C.TEXT)

    modal_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Ошибка"),
        content=ft.Text("", selectable=True),  # Текст ошибки будем менять динамически
        actions=[ft.TextButton("OK", on_click=lambda e: close_modal())],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    def close_modal():
        modal_dialog.open = False
        page.dialog = None
        page.update()

    list_view = ft.ListView(
        expand=True,
        spacing=2,
        auto_scroll=False,
        padding=0,
        on_scroll_interval=0,
        controls=[title],
    )

    spinner_container = ft.Container(
        content=loading_spinner(),
        alignment=ft.alignment.center,
        padding=20,
        visible=False,
    )
    list_view.controls.append(spinner_container)

    # Создаем ссылку на кнопку удаления для обновления её видимости
    delete_bar_ref = ft.Ref[ft.Container]()

    def update_delete_bar_visibility():
        """Обновляет видимость кнопки удаления"""
        try:
            if delete_bar_ref.current:
                delete_bar_ref.current.visible = page.portfolio_selection_mode
                delete_bar_ref.current.update()
        except Exception as e:
            print(f"[update_delete_bar_visibility] Error: {e}")

    def on_delete_selected(e):
        """Обработчик удаления выбранных элементов"""
        if not page.portfolio_highlighted_ids:
            return
        
        async def delete_assets():
            from services.portfolio_service import delete_asset, invalidate_portfolio_cache
            
            # Останавливаем анимацию перед удалением
            stop_shake_anim()
            
            # Показываем спиннер во время удаления
            spinner_container.visible = True
            if spinner_container not in list_view.controls:
                list_view.controls.append(spinner_container)
            page.update()
            
            # Удаляем каждый выбранный актив
            deleted_count = 0
            total_count = len(page.portfolio_highlighted_ids)
            
            for asset_id in list(page.portfolio_highlighted_ids):
                try:
                    success = await delete_asset(asset_id, page=page)
                    if success:
                        deleted_count += 1
                        print(f"[delete] Успешно удален актив {asset_id}")
                    else:
                        print(f"[delete] Ошибка удаления актива {asset_id}")
                except Exception as ex:
                    print(f"[delete] Исключение при удалении актива {asset_id}: {ex}")
            
            # Сбрасываем кэш и обновляем страницу
            invalidate_portfolio_cache()
            
            # Сброс режима выделения
            page.portfolio_selection_mode = False
            page.portfolio_highlighted_ids.clear()
            
            # Очищаем ссылки на карточки
            card_refs.clear()
            
            update_delete_bar_visibility()
            
            # Полное обновление списка
            await load_page_async(1, reset=True)
            
            print(f"[delete] Удалено {deleted_count} из {total_count} активов")
        
        # Запускаем асинхронное удаление
        page.run_task(delete_assets)

    def create_delete_bar():
        """Создает кнопку удаления"""
        return ft.Container(
            ref=delete_bar_ref,
            top=30,
            left=0,
            right=0,
            alignment=ft.alignment.top_center,
            visible=page.portfolio_selection_mode,
            content=ft.Container(
                margin=ft.margin.symmetric(horizontal=80),
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
                bgcolor=ft.colors.with_opacity(0.93, C.RED),
                border_radius=20,
                shadow=ft.BoxShadow(blur_radius=12, color=ft.colors.BLACK26),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(name=ft.icons.DELETE, color=ft.colors.WHITE),
                        ft.Text("Удалить", color=ft.colors.WHITE, size=16, weight="bold", ),
                    ],
                ),
                on_click=on_delete_selected
            )
        )

    def start_shake_anim():
        nonlocal shake_anim_timer
        if shake_anim_timer:
            return

        def tick():
            nonlocal shake_anim_timer
            if not page.portfolio_selection_mode:
                shake_anim_timer = None
                return

            # Проверяем, что card_refs не пустой и контролы все еще существуют
            if not card_refs:
                shake_anim_timer = None
                return

            for aid in list(card_refs.keys()):  # Создаем копию ключей
                try:
                    deg = random.uniform(-0.7, 0.7)
                    shake_angles[aid] = deg * math.pi / 180
                    ref = card_refs.get(aid)
                    if ref and ref.current:
                        ref.current.rotate = shake_angles[aid]
                        ref.current.update()
                except Exception as e:
                    print(f"[shake_anim] Error updating card {aid}: {e}")
                    # Удаляем проблемную ссылку
                    if aid in card_refs:
                        del card_refs[aid]
                    if aid in shake_angles:
                        del shake_angles[aid]

            # Планируем следующий тик только если режим выделения все еще активен
            if page.portfolio_selection_mode and card_refs:
                shake_anim_timer = threading.Timer(0.07, tick)
                shake_anim_timer.start()
            else:
                shake_anim_timer = None

        shake_anim_timer = threading.Timer(0.07, tick)
        shake_anim_timer.start()

    def stop_shake_anim():
        nonlocal shake_anim_timer
        if shake_anim_timer:
            shake_anim_timer.cancel()
            shake_anim_timer = None
        
        # Безопасно сбрасываем углы поворота
        for aid in list(card_refs.keys()):
            try:
                shake_angles[aid] = 0
                ref = card_refs.get(aid)
                if ref and ref.current:
                    ref.current.rotate = 0
                    ref.current.update()
            except Exception as e:
                print(f"[stop_shake_anim] Error resetting card {aid}: {e}")
                # Удаляем проблемную ссылку
                if aid in card_refs:
                    del card_refs[aid]
        
        # Очищаем углы поворота
        shake_angles.clear()

    async def flush_updates():
        nonlocal update_scheduled
        await asyncio.sleep(0.01)
        for asset_id in list(pending_updates):  # Создаем копию
            try:
                update_card(asset_id)
            except Exception as e:
                print(f"[flush_updates] Error updating card {asset_id}: {e}")
        pending_updates.clear()
        update_scheduled = False

    def update_card(asset_id: int):
        try:
            ref = card_refs.get(asset_id)
            if ref and ref.current:
                ref.current.bgcolor = (
                    ft.colors.with_opacity(0.18, C.RED) if asset_id in highlighted_ids else None
                )
                ref.current.rotate = shake_angles.get(asset_id, 0)
                ref.current.update()
        except Exception as e:
            print(f"[update_card] Error updating card {asset_id}: {e}")
            # Удаляем проблемную ссылку
            if asset_id in card_refs:
                del card_refs[asset_id]

    def make_on_long_press(asset_id):
        def _handler(_):
            page.portfolio_selection_mode = True
            highlighted_ids.add(asset_id)
            update_card(asset_id)
            start_shake_anim()
            update_delete_bar_visibility()
        return _handler

    def add_assets(items: list[dict]):
        insert_at = (
            list_view.controls.index(spinner_container)
            if spinner_container in list_view.controls
            else len(list_view.controls)
        )

        for a in items:
            if a["id"] in loaded_ids:
                continue

            bgcolor = ft.colors.with_opacity(0.18, C.RED) if a["id"] in highlighted_ids else None
            ref = ft.Ref[ft.Container]()
            card_refs[a["id"]] = ref

            def make_on_click(asset):
                def _handler(_):
                    nonlocal update_scheduled, click_lock

                    async def unlock_click():
                        nonlocal click_lock
                        await asyncio.sleep(0.15)
                        click_lock = False

                    if click_lock:
                        return

                    click_lock = True
                    page.run_task(unlock_click)

                    if page.portfolio_selection_mode:
                        if asset["id"] in highlighted_ids:
                            highlighted_ids.remove(asset["id"])
                        else:
                            highlighted_ids.add(asset["id"])

                        if not highlighted_ids:
                            page.portfolio_selection_mode = False
                            stop_shake_anim()
                            update_delete_bar_visibility()

                        pending_updates.add(asset["id"])
                        if not update_scheduled:
                            update_scheduled = True
                            page.run_task(flush_updates)
                    else:
                        page.client_storage.set("selected_asset", asset)

                        # Удаляем все предыдущие /asset, чтобы не было дубликатов в стеке
                        for i in reversed(range(len(page.views))):
                            if getattr(page.views[i], "route", "") == "/asset":
                                page.views.pop(i)

                        view = ft.View("/asset", controls=[asset_page(page)], padding=0)
                        page.views.append(view)
                        page.update()

                return _handler

            rotation_angle = shake_angles.get(a["id"], 0)

            list_view.controls.insert(
                insert_at,
                ft.GestureDetector(
                    on_tap=make_on_click(a),
                    on_long_press_start=make_on_long_press(a["id"]),
                    content=ft.Container(
                        ref=ref,
                        bgcolor=bgcolor,
                        border_radius=8,
                        content=asset_card(a),
                        rotate=rotation_angle,
                        animate_rotation=ft.animation.Animation(80, "easeInOut"),
                    ),
                )
            )
            insert_at += 1
            loaded_ids.add(a["id"])

    # основная загрузка
    async def load_page_async(page_num: int, *, reset: bool = False):
        nonlocal loading_more, current_page, all_loaded
        if loading_more:
            return
        loading_more = True

        try:
            first_page = page_num == 1

            use_mem_cache = first_page and not reset and session.cached_portfolio
            if use_mem_cache:
                assets = session.cached_portfolio
            else:
                if spinner_container not in list_view.controls:
                    list_view.controls.append(spinner_container)
                spinner_container.visible = True
                page.update()

                assets = await fetch_portfolio(
                    page=page,
                    page_number=None if first_page else page_num,
                    page_size=None if first_page else PAGE_SIZE,
                    force_refresh=reset,
                )

                if first_page:
                    
                    session.cached_portfolio = assets
                    loaded_ids.clear()
                else:
                    if session.cached_portfolio is None:
                        session.cached_portfolio = []
                    known = {a["id"] for a in session.cached_portfolio}
                    session.cached_portfolio.extend(a for a in assets if a["id"] not in known)

            if reset:
                # Останавливаем анимацию и очищаем ссылки перед сбросом
                stop_shake_anim()
                card_refs.clear()
                
                list_view.controls.clear()
                list_view.controls.append(title)
                list_view.controls.append(spinner_container)
                loaded_ids.clear()
                all_loaded = False

            add_assets(sorted(assets, key=lambda a: a.get("added_at", "")))

            if spinner_container in list_view.controls:
                list_view.controls.remove(spinner_container)

            if len(assets) < PAGE_SIZE and not first_page:
                all_loaded = True
                if not any(
                    isinstance(c, ft.Container) and getattr(c, "height", None) == 50
                    for c in list_view.controls[-2:]
                ):
                    list_view.controls.append(ft.Container(height=50))

            page.update()

        finally:
            loading_more = False
            current_page = page_num

    # показать полный список
    async def show_full_portfolio():
        nonlocal current_page, loaded_ids, all_loaded
        if session.cached_portfolio:
            assets = session.cached_portfolio
            
            # Останавливаем анимацию и очищаем ссылки
            stop_shake_anim()
            card_refs.clear()
            
            list_view.controls.clear()
            list_view.controls.append(title)
            loaded_ids.clear()
            all_loaded = len(assets) < PAGE_SIZE

            add_assets(sorted(assets, key=lambda a: a.get("added_at", "")))

            current_page = max(1, len(assets) // PAGE_SIZE)
            spinner_container.visible = False
            page.update()

            if not all_loaded:
                page.run_task(load_page_async, current_page + 1)
        else:
            await load_page_async(1, reset=True)

    # поиск
    async def handle_search_async(query: str):
        query = query.strip()
        if not query:
            await show_full_portfolio()
            return

        # Останавливаем анимацию при поиске
        stop_shake_anim()
        card_refs.clear()

        stocks = await search_stocks(query, page=page)
        list_view.controls.clear()
        list_view.controls.append(title)
        loaded_ids.clear()

        for stock in stocks:
            def make_on_click(s):
                def _handler(_):
                    async def do_add():
                        res = await add_to_portfolio(s["id"], 1)
                        if res is True:
                            invalidate_portfolio_cache()
                            search_field.value = ""
                            search_field.update()
                            page.go("/_refresh")
                            page.go("/portfolio")
                        else:
                            # Извлекаем detail, если есть
                            detail = None
                            if isinstance(res, dict):
                                # сначала пытаемся data.detail (наш патч)
                                if "data" in res and isinstance(res["data"], dict) and "detail" in res["data"]:
                                    detail = res["data"]["detail"]
                                # затем просто detail
                                elif "detail" in res:
                                    detail = res["detail"]
                            if not detail:
                                detail = "Не удалось добавить актив"
                            if hasattr(page, "dialog") and page.dialog is not None:
                                page.dialog.open = False
                            modal_dialog.content.value = str(detail)
                            modal_dialog.open = True
                            page.dialog = modal_dialog
                            page.update()
                    page.run_task(do_add)
                return _handler

            list_view.controls.append(
                ft.Container(
                    padding=12,
                    bgcolor=ft.colors.with_opacity(0.04, C.TEXT),
                    border_radius=10,
                    on_click=make_on_click(stock),
                    content=ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(stock["symbol"], color=C.PRIMARY, size=18),
                            ft.Text(stock["shortname"], color=C.HINT, size=14),
                        ],
                    ),
                )
            )

        page.update()

    # UI-обработчики
    def clear_search(_):
        search_ref.current.value = ""
        search_ref.current.update()
        page.run_task(show_full_portfolio)

    def on_search_change(e):
        nonlocal is_search_mode
        query = e.control.value.strip()
        is_search_mode = bool(query)
        page.run_task(handle_search_async, query)

    async def refresh_async():
        nonlocal is_refreshing
        if is_refreshing:
            return
        is_refreshing = True
        try:
            invalidate_portfolio_cache()
            await load_page_async(1, reset=True)
        finally:
            is_refreshing = False

    def on_scroll(e: OnScrollEvent):
        if e.event_type != "update" or is_search_mode or all_loaded:
            return
        if e.pixels >= e.max_scroll_extent - 100:
            if load_sem.acquire(blocking=False):
                try:
                    page.run_task(load_page_async, current_page + 1)
                finally:
                    load_sem.release()

    def on_vertical_drag_update(e: DragUpdateEvent):
        nonlocal drag_start_y
        if drag_start_y == 0:
            drag_start_y = e.global_y
            return
        if e.global_y - drag_start_y > 60:
            drag_start_y = 0
            page.run_task(refresh_async)

    def on_vertical_drag_end(_):
        nonlocal drag_start_y
        drag_start_y = 0

    list_view.on_scroll = on_scroll

    # search-field
    search_field = ft.TextField(
        ref=search_ref,
        hint_text="Поиск…",
        hint_style=ft.TextStyle(color=ft.colors.GREY_500, size=14),
        text_style=ft.TextStyle(color=ft.colors.GREY_300),
        text_vertical_align=ft.VerticalAlignment.CENTER,
        height=38,
        focused_border_color=C.PRIMARY,
        border_radius=22,
        border_color=ft.colors.TRANSPARENT,
        bgcolor=ft.colors.with_opacity(0.12, ft.colors.GREY_300),
        content_padding=10,
        prefix_icon=ft.Icon(name=ft.Icons.SEARCH, size=20, color=ft.colors.GREY_500),
        suffix=ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_color=ft.colors.GREY_500,
            icon_size=14,
            on_click=clear_search,
            style=ft.ButtonStyle(padding=0),
            tooltip="Очистить",
        ),
        on_change=on_search_change,
    )

    # начальная отрисовка
    if cached_assets:
        add_assets(sorted(cached_assets, key=lambda a: a.get("added_at", "")))
        current_page = max(1, len(cached_assets) // PAGE_SIZE)
        all_loaded = len(cached_assets) < current_page * PAGE_SIZE
        if all_loaded and spinner_container in list_view.controls:
            list_view.controls.remove(spinner_container)
        page.update()
        if not all_loaded:
            page.run_task(load_page_async, current_page + 1)
    else:
        spinner_container.visible = True
        page.update()
        page.run_task(load_page_async, 1)

    # push-ID (моб.)
    if page.platform.value in ("android", "ios"):
        pid = session.onesignal.get_onesignal_id()

        async def push_sync():
            try:
                if pid and session.onesignal_id != pid:
                    await send_onesignal_id_to_server(pid)
                    session.onesignal_id = pid
                    await save_to_storage(page, {"onesignal_id": pid})
            except Exception as ex:
                print("[OneSignal] sync error:", ex)

        page.run_task(push_sync)

    # возврат контейнера
    from components.bottom_nav_bar import bottom_nav_bar

    return ft.Container(
        expand=True,
        padding=0,
        content=ft.Stack(
            controls=[
                # Основной контент
                ft.Container(
                    expand=True,
                    padding=10,
                    content=ft.Column(
                        expand=True,
                        controls=[
                            ft.Container(content=search_field, margin=ft.margin.only(top=20)),
                            ft.Container(
                                expand=True,
                                content=ft.GestureDetector(
                                    on_vertical_drag_update=on_vertical_drag_update,
                                    on_vertical_drag_end=on_vertical_drag_end,
                                    content=list_view,
                                ),
                            ),
                        ]
                    ),
                ),
                # Кнопка удаления поверх контента
                create_delete_bar(),
                # Навбар внизу
                ft.Container(
                    bottom=30,
                    left=0,
                    right=0,
                    alignment=ft.alignment.bottom_center,
                    content=bottom_nav_bar(page, selected_index=0),
                ),
                modal_dialog,
            ]
        )
    )
