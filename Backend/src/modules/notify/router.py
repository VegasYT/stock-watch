from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_session
from src.core.dependencies import UserIdDep
from src.modules.notify.service import AlertService
from src.modules.notify.schemas import AlertCreate, AlertOut


router = APIRouter(prefix="/notify", tags=["Notify"])


@router.post("/", response_model=AlertOut)
async def create_alert(
    data: AlertCreate,
    user_id: UserIdDep,
    session: AsyncSession = Depends(get_async_session),
):
    service = AlertService(session)
    try:
        return await service.create_alert(user_id, data)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[AlertOut])
async def list_alerts(
    user_id: UserIdDep,
    stock_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_async_session),
):
    service = AlertService(session)
    return await service.list_alerts(user_id, stock_id, page, page_size)


@router.post("/{alert_id}/deactivate")
async def deactivate_alert(
    alert_id: int,
    user_id: UserIdDep,
    session: AsyncSession = Depends(get_async_session),
):
    service = AlertService(session)
    await service.deactivate(alert_id, user_id)
    return {"status": "ok"}


@router.post("/alerts/test/check")
async def test_check_alerts(
    user_id: UserIdDep,
    session: AsyncSession = Depends(get_async_session),
):
    from src.modules.notify.service import AlertService
    service = AlertService(session)
    await service.check_all()
    # await service._send_push(user_id, 387, 100)
    return {"status": "done"}
