"""Route tài khoản (lát 5a), danh mục (lát 5b), cảnh báo (lát 5c) và báo cáo AI bản ngắn (lát 7, D116) của web
hợp nhất, mục 13 và 15 của docs/PLAN_WEB_HOP_NHAT.md.

Đây là các route GHI của web mới. Chúng chỉ ghi vào tệp dữ liệu người dùng (`web_user.db`), không đụng DB
định giá, và chỉ nhận yêu cầu gửi từ chính trang web. Tài khoản: chỉ Quản trị ghi. Danh mục: mỗi người
ghi lệnh của mình; Quản trị xem được danh mục của mọi người nhưng không sửa hộ. Mức giá tự đặt: của ai
người đó thấy và sửa, Quản trị cũng không xem.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from valuation.api.web_deps import (
    AdminUser,
    ApprovedUser,
    CurrentUser,
    UserDb,
    same_origin,
)
from valuation.config import load_defaults, settings
from valuation.db.session import get_read_db
from valuation.db.web_user import VAI_QUAN_TRI, WebUser
from valuation.services import (
    web_ai_report,
    web_alerts,
    web_flow,
    web_portfolio,
    web_users,
    web_valuation,
)

router = APIRouter()

UserId = Annotated[int, Path(ge=1)]


class RoleBody(BaseModel):
    vai: str


def _act(action: Any, *args: Any) -> dict:
    try:
        return action(*args)
    except web_users.UserActionError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@router.get("/api/toi")
def toi(user: CurrentUser) -> dict:
    """Tài khoản đang đăng nhập: tên, vai, trạng thái duyệt. Người chờ duyệt hoặc bị khóa cũng gọi được."""
    cfg = load_defaults()["web"]["auth"]
    return {
        **web_users.to_dict(user),
        "che_do": settings.web_auth_mode,
        "dang_xuat": cfg["logout_path"],
        "hoi_canh_bao_giay": load_defaults()["web"]["alerts"]["poll_seconds"],
        "lien_he": load_defaults()["web"]["lien_he"],
    }


@router.get("/api/tai-khoan")
def tai_khoan(admin: AdminUser, udb: UserDb) -> dict:
    """Danh sách tài khoản đã từng mở web, chờ duyệt đứng trước (chỉ Quản trị)."""
    return {"toi": admin.id, "tai_khoan": web_users.list_users(udb)}


@router.post("/api/tai-khoan/{user_id}/duyet", dependencies=[Depends(same_origin)])
def duyet(user_id: UserId, admin: AdminUser, udb: UserDb) -> dict:
    """Duyệt một tài khoản đang chờ, hoặc mở lại tài khoản đã khóa."""
    return _act(web_users.approve, udb, admin, user_id)


@router.post("/api/tai-khoan/{user_id}/khoa", dependencies=[Depends(same_origin)])
def khoa(user_id: UserId, admin: AdminUser, udb: UserDb) -> dict:
    """Khóa một tài khoản: người đó không xem được số liệu nữa."""
    return _act(web_users.block, udb, admin, user_id)


@router.post("/api/tai-khoan/{user_id}/vai", dependencies=[Depends(same_origin)])
def doi_vai(user_id: UserId, body: RoleBody, admin: AdminUser, udb: UserDb) -> dict:
    """Đổi vai giữa Quản trị và Nhân viên."""
    return _act(web_users.set_role, udb, admin, user_id, body.vai)


# ---------- Danh mục (lát 5b) ----------
ReadDb = Annotated[Session, Depends(get_read_db)]
OrderId = Annotated[int, Path(ge=1)]
Owner = Annotated[int | None, Query(ge=1)]


class OrderBody(BaseModel):
    loai: str
    ma: str
    chieu: str
    so_luong: int
    gia: float
    ngay: str
    chot_loi: float | None = None
    cat_lo: float | None = None
    ghi_chu: str | None = None
    ma_yeu_cau: str


def _portfolio_call(action: Any, *args: Any) -> Any:
    try:
        return action(*args)
    except web_portfolio.PortfolioError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


def _owner(user: WebUser, udb: Session, nguoi: int | None) -> WebUser:
    """Danh mục của chính mình, hoặc của người khác nếu là Quản trị (chỉ để xem)."""
    if nguoi is None or nguoi == user.id:
        return user
    if user.vai != VAI_QUAN_TRI:
        raise HTTPException(
            status_code=403, detail="Chỉ Quản trị xem được danh mục của người khác."
        )
    owner = udb.get(WebUser, nguoi)
    if owner is None:
        raise HTTPException(status_code=404, detail="Không có tài khoản này.")
    return owner


@router.get("/api/danh-muc")
def danh_muc(user: ApprovedUser, udb: UserDb, db: ReadDb, nguoi: Owner = None) -> dict:
    """Vị thế, giá vốn bình quân, lãi lỗ theo giá lúc gọi của một danh mục 4 loại."""
    owner = _owner(user, udb, nguoi)
    data = _portfolio_call(web_portfolio.portfolio, udb, db, owner)
    return {**data, "cua_toi": owner.id == user.id}


@router.get("/api/danh-muc/lenh")
def danh_muc_lenh(user: ApprovedUser, udb: UserDb, nguoi: Owner = None) -> dict:
    """Sổ lệnh còn hiệu lực, mới nhất trước."""
    owner = _owner(user, udb, nguoi)
    return {
        "cua_toi": owner.id == user.id,
        "lenh": web_portfolio.list_orders(udb, owner.id),
    }


@router.get("/api/danh-muc/nguoi")
def danh_muc_nguoi(admin: AdminUser, udb: UserDb) -> dict:
    """Danh sách tài khoản kèm số lệnh, để Quản trị chọn danh mục muốn xem."""
    return {"toi": admin.id, "nguoi": web_portfolio.owners(udb)}


@router.post("/api/danh-muc/lenh", dependencies=[Depends(same_origin)])
def them_lenh(body: OrderBody, user: ApprovedUser, udb: UserDb, db: ReadDb) -> dict:
    """Ghi một lệnh mua hoặc bán vào danh mục của chính mình."""
    return _portfolio_call(web_portfolio.add_order, udb, db, user, body.model_dump())


@router.post("/api/danh-muc/lenh/{order_id}/xoa", dependencies=[Depends(same_origin)])
def xoa_lenh(order_id: OrderId, user: ApprovedUser, udb: UserDb) -> dict:
    """Xóa (xóa mềm) một lệnh của chính mình."""
    return _portfolio_call(web_portfolio.delete_order, udb, user, order_id)


# ---------- Cảnh báo (lát 5c) ----------
LevelId = Annotated[int, Path(ge=1)]


class LevelBody(BaseModel):
    ma: str
    chieu: str
    muc: float
    ghi_chu: str | None = None


def _alert_call(action: Any, *args: Any) -> Any:
    try:
        return action(*args)
    except web_alerts.AlertError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@router.get("/api/canh-bao")
def canh_bao(user: ApprovedUser, udb: UserDb) -> dict:
    """Trang Cảnh báo: bất thường đang mua được (chung) và các mức giá của người đang đăng nhập."""
    return web_alerts.page(udb, user)


@router.get("/api/canh-bao/tin")
def canh_bao_tin(user: ApprovedUser, udb: UserDb) -> dict:
    """Tin mới để trình duyệt báo; trình duyệt hỏi mỗi phút, ngoài giờ khớp lệnh không gọi giá."""
    return web_alerts.feed(udb, user)


@router.get("/api/muc-gia")
def muc_gia(user: ApprovedUser, udb: UserDb) -> dict:
    """Các mức giá của chính mình kèm giá bây giờ."""
    return web_alerts.levels(udb, user)


@router.post("/api/muc-gia", dependencies=[Depends(same_origin)])
def them_muc_gia(body: LevelBody, user: ApprovedUser, udb: UserDb) -> dict:
    """Đặt một mức giá để được báo khi giá chạm."""
    return _alert_call(web_alerts.add_level, udb, user, body.model_dump())


@router.post("/api/muc-gia/{level_id}/xoa", dependencies=[Depends(same_origin)])
def xoa_muc_gia(level_id: LevelId, user: ApprovedUser, udb: UserDb) -> dict:
    """Xóa (xóa mềm) một mức giá của chính mình."""
    return _alert_call(web_alerts.delete_level, udb, user, level_id)


# ---------- Báo cáo AI bản ngắn (lát 7, D116) ----------
TickerPath = Annotated[str, Path(pattern="^[A-Za-z0-9]{3,4}$")]


def _stock(ma: str, db: Session) -> str:
    """Mã hợp lệ và có trong bảng `tickers` (cùng điều kiện với các route định giá của web_main)."""
    ticker = web_flow.normalize_ticker(ma)
    if ticker is None:
        raise HTTPException(status_code=422, detail="Mã không hợp lệ.")
    if not web_valuation.known(db, ticker):
        raise HTTPException(status_code=404, detail="Không có mã này trong dữ liệu.")
    return ticker


@router.get("/api/co-phieu/{ma}/bao-cao-ai")
def bao_cao_ai_ngan(
    ma: TickerPath, user: ApprovedUser, udb: UserDb, db: ReadDb
) -> dict:
    """Bản báo cáo AI ngắn đã lưu của mã (nếu có) và số lượt sinh mới người này còn trong ngày."""
    return web_ai_report.status(udb, user, _stock(ma, db))


@router.post("/api/co-phieu/{ma}/bao-cao-ai", dependencies=[Depends(same_origin)])
def sinh_bao_cao_ai(
    ma: TickerPath, user: ApprovedUser, udb: UserDb, db: ReadDb
) -> dict:
    """Sinh bản mới (một lần gọi DeepSeek, trừ một lượt); dữ liệu không đổi thì trả bản cũ, không trừ lượt."""
    try:
        return web_ai_report.generate(db, udb, user, _stock(ma, db))
    except web_ai_report.AiReportError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc
