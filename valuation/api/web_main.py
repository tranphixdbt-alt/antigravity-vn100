"""API và giao diện tĩnh của web hợp nhất btinvest.vn (docs/PLAN_WEB_HOP_NHAT.md mục 12, 13).

Tách khỏi `valuation.api.main` vì app đó có route ghi DB định giá và khởi động job. Ở đây mọi route số
liệu chỉ GET, chỉ đọc, và chỉ tài khoản đã được duyệt mới gọi được (lát 5a). Route ghi duy nhất là phần
tài khoản ở `web_user_routes.py`, chỉ ghi vào tệp dữ liệu người dùng, không đụng DB định giá.
Chạy tại máy: `uvicorn valuation.api.web_main:app --host 127.0.0.1 --port 8600` (thư mục gốc repo).
"""

from __future__ import annotations

from pathlib import Path as FsPath
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Query
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.responses import Response

from valuation.api import web_user_routes
from valuation.api.web_deps import require_approved
from valuation.config import load_defaults
from valuation.db.session import get_read_db
from valuation.services import web_cw, web_flow, web_live, web_market, web_valuation

WEB_DIR = FsPath(__file__).resolve().parents[2] / "web"

app = FastAPI(title="BT Invest web", docs_url=None, redoc_url=None, openapi_url=None)
# mọi route số liệu: phải đăng nhập và đã được Quản trị duyệt
data = APIRouter(dependencies=[Depends(require_approved)])

Db = Annotated[Session, Depends(get_read_db)]
Mode = Annotated[str, Query(pattern="^(loai|gom)$")]
TickerPath = Annotated[str, Path(pattern="^[A-Za-z0-9]{3,4}$")]


def _known(ma: str) -> str:
    ticker = web_flow.normalize_ticker(ma)
    if ticker is None:
        raise HTTPException(status_code=422, detail="Mã không hợp lệ.")
    return ticker


@app.get("/api/suc-khoe")
def suc_khoe() -> dict:
    return {"ok": True}


@data.get("/api/ma")
def danh_sach_ma(db: Db) -> list[dict]:
    """Danh sách mã cho ô tìm kiếm."""
    return web_flow.ticker_list(db)


@data.get("/api/dong-tien")
def dong_tien(db: Db, che_do: Mode = "loai") -> dict:
    """Tóm tắt, bảng ngành và danh sách mã của tab Dòng tiền ngành."""
    return web_flow.overview(db, che_do)


@data.get("/api/co-phieu/{ma}/dong-tien")
def dong_tien_ma(ma: TickerPath, db: Db, che_do: Mode = "loai") -> dict:
    """Thẻ dòng tiền và các bảng chi tiết của một mã."""
    data = web_flow.ticker(db, _known(ma), che_do)
    if data is None:
        raise HTTPException(
            status_code=404, detail="Mã không có trong bảng dòng tiền VN100."
        )
    return data


@data.get("/api/co-phieu/{ma}/bieu-do")
def bieu_do(
    ma: TickerPath,
    db: Db,
    che_do: Mode = "loai",
    khung: str | None = None,
    tang: str | None = None,
    ho_so: bool = False,
    toi: bool = False,
    chi_du_lieu: bool = False,
) -> dict:
    """Biểu đồ giá và dòng tiền nhiều tầng của tab cũ, trả về HTML để nhúng.

    `chi_du_lieu=true` (D128): chỉ dữ liệu các tầng, để trình duyệt thay vào biểu đồ đang mở trong phiên.
    """
    ccfg = load_defaults()["money_flow_chart"]
    rng = khung or ccfg["default_range"]
    if rng not in ccfg["ranges"]:
        raise HTTPException(status_code=422, detail="Khung thời gian không hợp lệ.")
    try:
        layers = web_flow.parse_layers(tang)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    data = web_flow.chart(db, _known(ma), che_do, rng, layers, ho_so, toi, chi_du_lieu)
    if data is None:
        raise HTTPException(
            status_code=404, detail="Mã không có trong bảng dòng tiền VN100."
        )
    return data


@data.get("/api/thi-truong")
def thi_truong(db: Db) -> dict:
    """Tổng quan thị trường: đèn tổng, bốn trụ cột, VN-Index, ngành và mã nổi bật."""
    return web_market.market(db)


@data.get("/api/truc-tiep")
def truc_tiep(db: Db, dong_tien: bool = False) -> dict:
    """Giá trong phiên: VN-Index, VN30, mã VN100 tăng giảm mạnh nhất, khối ngoại (Vietcap, nhớ chung cho mọi người).

    D128: kèm `phien_db` (dấu phiên bản số trong DB) để trình duyệt nạp lại các tab khi job vừa ghi; `dong_tien=true`
    (tab Dòng tiền, trang một mã đang mở) kèm khối ngoại ròng của phiên đang chạy theo từng mã và ngành.
    """
    out = web_live.snapshot() | {"phien_db": web_flow.data_version(db)}
    if dong_tien:
        out["dong_tien"] = web_flow.session_flows(db)
    return web_flow.clean(out)


@data.get("/api/vi-mo")
def vi_mo(db: Db) -> dict:
    """Chỉ số vĩ mô, nhận định nhanh và bản tin vĩ mô đã lưu."""
    return web_market.macro(db)


@data.get("/api/xep-hang")
def xep_hang(db: Db) -> dict:
    """Xếp hạng VN100 theo upside của đợt định giá gần nhất và ứng viên tích sản."""
    return web_market.ranking(db)


@data.get("/api/lich-quyen")
def lich_quyen(db: Db) -> dict:
    """Lịch cổ tức và quyền mua VN100 sắp tới."""
    return web_market.upcoming(db)


def _in_universe(ma: str, db: Session) -> str:
    """Mã hợp lệ và có trong bảng `tickers`; dùng cho các route định giá (lát 2)."""
    ticker = _known(ma)
    if not web_valuation.known(db, ticker):
        raise HTTPException(status_code=404, detail="Không có mã này trong dữ liệu.")
    return ticker


@data.get("/api/co-phieu/{ma}/dinh-gia")
def dinh_gia(ma: TickerPath, db: Db) -> dict:
    """Kết quả định giá, cờ cảnh báo, giả định, WACC, kịch bản, độ nhạy, dự phóng."""
    return web_valuation.valuation(db, _in_universe(ma, db))


@data.get("/api/co-phieu/{ma}/tai-chinh")
def tai_chinh(ma: TickerPath, db: Db) -> dict:
    """Báo cáo tài chính lịch sử (tỷ đồng)."""
    return web_valuation.financials(db, _in_universe(ma, db))


@data.get("/api/co-phieu/{ma}/ctck")
def cong_ty_chung_khoan(ma: TickerPath, db: Db) -> dict:
    """So sánh với giá mục tiêu công ty chứng khoán và bản tổng hợp luận điểm đã lưu."""
    return web_valuation.consensus(db, _in_universe(ma, db))


@data.get("/api/co-phieu/{ma}/co-tuc")
def co_tuc(ma: TickerPath, db: Db) -> dict:
    """Sự kiện cổ tức, tăng vốn, quyền mua đã công bố."""
    return web_valuation.dividends(db, _in_universe(ma, db))


@data.get("/api/co-phieu/{ma}/ai")
def bao_cao_ai(ma: TickerPath, db: Db) -> dict:
    """Báo cáo AI gần nhất đã lưu; không sinh mới."""
    return web_valuation.ai_report(_in_universe(ma, db))


CwCode = Annotated[str, Path(pattern="^[A-Z0-9]{4,12}$")]
FundCode = Annotated[str, Path(pattern="^[A-Z0-9]{3,12}$")]
FutureCode = Annotated[str, Path(pattern="^VN(30|100)F[12][MQ]$")]


def _cw(path: str) -> dict:
    """JSON từ dịch vụ chứng quyền (lát 4); lỗi của dịch vụ thành mã HTTP và câu báo tương ứng."""
    try:
        return web_cw.fetch(path)
    except web_cw.CwServiceError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@data.get("/api/chung-quyen")
def chung_quyen() -> dict:
    """Danh sách chứng quyền của lần quét mới nhất, số lượng theo nhóm, ngưỡng 4 tiêu chí."""
    return _cw("/api/chung-quyen")


@data.get("/api/chung-quyen/{ma}")
def chung_quyen_mot_ma(ma: CwCode) -> dict:
    """Số lúc quét của một chứng quyền, 4 tiêu chí, các chứng quyền cùng mã cơ sở."""
    return _cw(f"/api/chung-quyen/{ma}")


@data.get("/api/chung-quyen/{ma}/trang-cu")
def chung_quyen_trang_cu(ma: CwCode) -> dict:
    """Trang phân tích cũ của một chứng quyền (giá trực tiếp, nến, IV), HTML để nhúng."""
    return _cw(f"/api/trang-cu/cw/{ma}")


@data.get("/api/etf")
def quy_etf() -> dict:
    """Ba bảng ETF: chiết khấu so với NAV, chỉ số, tất cả quỹ."""
    return _cw("/api/etf")


@data.get("/api/etf/{ma}/trang-cu")
def quy_etf_trang_cu(ma: FundCode) -> dict:
    """Trang phân tích cũ của một quỹ ETF, HTML để nhúng."""
    return _cw(f"/api/trang-cu/etf/{ma}")


@data.get("/api/phai-sinh")
def phai_sinh() -> dict:
    """Hợp đồng tương lai VN30, VN100: giá, basis, basis năm hóa, ký quỹ."""
    return _cw("/api/phai-sinh")


@data.get("/api/phai-sinh/{ma}/trang-cu")
def phai_sinh_trang_cu(ma: FutureCode) -> dict:
    """Trang phân tích cũ của một hợp đồng tương lai, HTML để nhúng."""
    return _cw(f"/api/trang-cu/phai-sinh/{ma}")


app.include_router(data)
app.include_router(web_user_routes.router)


class WebAssets(StaticFiles):
    """Khung web tĩnh, luôn kèm `Cache-Control: no-cache`.

    Không có tiêu đề này thì trình duyệt tự giữ app.js cũ một thời gian sau mỗi lần deploy, giao diện cũ gọi API
    mới (thấy thật 26/11/2026, D118). Tệp có ETag nên mỗi lần hỏi lại chỉ là một yêu cầu nhỏ trả 304.
    """

    def file_response(self, *args: Any, **kwargs: Any) -> Response:
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


# tệp tĩnh của khung web (không có số liệu) thì ai cũng tải được, như các đường dẫn công khai ở Caddy
if WEB_DIR.is_dir():
    app.mount("/", WebAssets(directory=WEB_DIR, html=True), name="web")
