"""Lộ trình học trong tab "Dòng tiền ngành" (D73, docs/PLAN_SECTOR_FLOW.md §5).

Văn bản tĩnh + 1 dòng "Ví dụ từ dữ liệu" sinh từ kết quả compute_money_flow (thiếu dữ liệu thì câu
dự phòng). Không gọi mạng, không AI. Bài L4 cố ý nhắc cụm "tiền vào/tiền ra" để giải thích vì sao app
không dùng — chỉ template sinh động mới bị quét forbidden_phrases.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from valuation.analysis.money_flow import (
    _bn,
    _dm,
    _ty,
    implied_domestic,
    position_size,
)
from valuation.views.market_overview import _chg, _vi

Example = Callable[[dict, str | None, dict], str]


# ---------- Hướng dẫn đọc (dấu ? ở tiêu đề mục) và tooltip ----------
def read_sector(cfg: dict) -> str:
    return "\n".join(
        [
            (
                "- Màu là mua/bán ròng của khối ngoại so với GTGD của chính ngành (R_F), cắt ở "
                f"±{_vi(cfg['heat_clip'] * 100)}% để ngành nhỏ không lấn màu; chữ trong ô vẫn là số thật."
            ),
            "- Một mã lớn có thể kéo cả ngành: xem thêm cột **Mã chi phối** và cột **Gom / xả**.",
            f"- Ngành dưới {cfg['small_sector_n']} mã xếp cuối (cờ «ít mã») và không vào câu kết luận.",
            (
                "- Tự doanh chỉ tính trên phiên có số; phủ dưới "
                f"{_vi(cfg['prop_sector_min_value_cov'] * 100)}% GTGD ngành thì ô để mờ."
            ),
            "- Ngân hàng bán ròng có thể do kín room ngoại (chưa có dữ liệu room tới giai đoạn B1).",
            "- Khối ngoại thường mua theo đà giá (Richards 2005), vì vậy mua ròng không có nghĩa giá sẽ tăng.",
            (
                "- Khung «Tổng quan thị trường» ở sidebar tính gồm thỏa thuận và không cắt theo lịch phiên, "
                "nên có thể lệch dấu với tab này ở chế độ Loại."
            ),
        ]
    )


def read_card(cfg: dict) -> str:
    s = cfg["signal"]
    return "\n".join(
        [
            (
                "- 6 nhãn: Dấu hiệu gom ▲ / Dấu hiệu xả ▼ (khối ngoại dẫn) · Nội gom △ / Nội xả ▽ (ngoại không "
                "có chiều) · Trung tính · Chưa đủ dữ liệu. Nhãn luôn tính ở chế độ **Loại** thỏa thuận; công tắc "
                "Gồm chỉ đổi các con số tổng."
            ),
            (
                f"- **Ngoại** (phiếu chính): R_F ≥ {_vi(s['foreign_band'] * 100)}% GTGD và ≥ "
                f"{_vi(s['same_sign_share'] * 100)}% phiên hợp lệ cùng dấu; cần ≥ {s['min_valid_sessions']} "
                "phiên hợp lệ."
            ),
            (
                f"- **Giá-KL** (xác nhận): CMF{s['cmf_window']} ≥ +{_vi(s['cmf_band'], 2)} hoặc ≤ "
                f"−{_vi(s['cmf_band'], 2)} (tính trên biên độ thực, có cả khoảng nhảy giá so với phiên trước); "
                f"quá {s['cmf_max_flat']} phiên đứng giá thì không bỏ phiếu."
            ),
            (
                f"- **Tự doanh** (phụ): R_P ≥ {_vi(s['prop_band'] * 100, 1)}% và phủ ≥ "
                f"{_vi(s['prop_min_session_cov'] * 100)}% phiên; không chặn được nhãn, một mình không tạo nhãn."
            ),
            (
                "- Gom/Xả cần phiếu Ngoại cùng chiều + ít nhất 1 phiếu xác nhận cùng chiều, Giá-KL không "
                "ngược chiều. Không có điểm tổng hợp, không có xác suất."
            ),
            (
                f"- **Nội gom / Nội xả**: phiếu Ngoại = 0, Giá-KL ▲/▼, KL khớp TB {s['cmf_window']} phiên ≥ "
                f"{_vi(s['rvol_min'], 1)} lần TB {s['rvol_base']} phiên liền trước, Tự doanh không ngược chiều. "
                "Đây là áp lực mua/bán đọc qua giá-KL khi khối ngoại đứng ngoài — không phải số mua ròng của "
                "nhà đầu tư trong nước (số đó luôn = −(ngoại + tự doanh)). Giảm sàn không người mua thì KL thấp "
                "nên không ra Nội xả. Chưa backtest."
            ),
            (
                "- ▲ mua ròng / CMF dương · ▼ bán ròng / CMF âm · 0 chưa đạt ngưỡng · ◌ không đủ dữ liệu "
                "để bỏ phiếu. Hậu tố («giá đi ngang», «giá đã tăng x%») chỉ mô tả giá 20 phiên."
            ),
        ]
    )


def read_list(cfg: dict) -> str:
    return "\n".join(
        [
            "- Lọc theo ngành/nhãn ở hai ô phía trên; bấm một dòng để xem thẻ của mã đó.",
            (
                f"- «Giữ nhãn từ»: ngày nhãn hiện tại bắt đầu, xét {cfg['signal']['label_history']} phiên "
                "dòng tiền gần nhất; «≤» nghĩa là đã giữ suốt các phiên đó."
            ),
            "- Upside là cột phụ từ đợt định giá VN100 (giá trị hợp lý chưa qua golden test).",
        ]
    )


def read_detail(cfg: dict) -> str:
    return "\n".join(
        [
            (
                "- Thỏa thuận suy từ KL ngoại + tự doanh > KL khớp: KL là **cận dưới**, giá trị chỉ là "
                "**ước ~** (cận dưới × giá bình quân phía áp đảo)."
            ),
            (
                "- Trong nước suy ra D = −(ngoại + tự doanh) chỉ đúng khi: (1) có số cả hai nhóm, "
                "(2) ngoại và tự doanh không trùng người, (3) cùng phạm vi giao dịch (đã loại thỏa thuận)."
            ),
            "- OBV chỉ để minh họa, chỉ xem độ dốc; không dùng để bỏ phiếu.",
            f"- Dạng ngoại↔ngoại: min/max(ngoại mua, ngoại bán) ≥ {_vi(cfg['cross_foreign_ratio'], 1)}.",
        ]
    )


HELP = {
    "mode": "Loại: bỏ cả phiên-mã có cờ thỏa thuận khỏi tử số lẫn mẫu số (mặc định). Gồm: cộng cả "
    "thỏa thuận, chỉ hiện tổng tỷ đồng (không tỷ lệ, không màu).",
    "sector": "Ngành theo bảng routing của app (market_overview.sector_map).",
    "foreign": "Tổng mua ròng khối ngoại 20 phiên (tỷ đồng) và R_F = tổng / GTGD trên phiên hợp lệ.",
    "prop": "Tự doanh CTCK 20 phiên trên các phiên có số; kèm độ phủ GTGD.",
    "labels": "Số mã Dấu hiệu gom ▲ · Dấu hiệu xả ▼ (khối ngoại dẫn); nếu có thì thêm Nội gom △ · Nội xả ▽ "
    "(ngoại không có chiều, đọc qua giá-KL), đếm riêng / tổng số mã của ngành.",
    "dominant": "Mã có |mua/bán ròng ngoại| lớn nhất và tỷ trọng trong tổng |ròng| của ngành.",
    "breadth": "Số mã trong ngành được khối ngoại mua ròng trong cửa sổ / số mã có số liệu. Mỗi mã tính một phiếu "
    "như nhau, không theo vốn hóa. Cột Ngoại tính theo tổng tiền nên một mã trụ có thể kéo cả ngành: vd ngành "
    "bán ròng do một mã lớn nhưng 4/6 mã vẫn mua ròng → dòng tiền đang phân hóa, không phải cả ngành bị xả.",
    "rs20": "Trung vị (ret20 của mã − trung vị VN100) trong ngành.",
    "flags": "đổi dấu Gồm/Loại · ít mã · dòng tiền thủng (có giá nhưng thiếu số khối ngoại).",
    "votes": "Ngoại · Giá-KL · Tự doanh: ▲ +1, ▼ −1, 0 chưa đạt ngưỡng, ◌ không đủ dữ liệu.",
    "context": "Chỉ mô tả giá 20 phiên, không đổi nhãn.",
    "held": "Ngày nhãn hiện tại bắt đầu (xét các phiên dòng tiền gần nhất).",
    "upside": "Giá trị hợp lý (đợt định giá VN100) ÷ giá − 1. Cột phụ, chưa golden.",
}

# Dòng giải thích khi rê chuột vào TIÊU ĐỀ CỘT, cho mọi bảng của tab Dòng tiền ngành (money_flow._help_cfg).
# Cột tên động "Ngoại 20p" / "Tự doanh 20p" khớp theo tiền tố (COLUMN_HELP_PREFIX).
COLUMN_HELP = {
    "Ngành": HELP["sector"],
    "n": "Số mã VN100 của ngành có dữ liệu trong cửa sổ.",
    "Gom / xả": HELP["labels"],
    "Mã chi phối": HELP["dominant"],
    "Độ rộng ngoại": HELP["breadth"],
    "RS20": HELP["rs20"],
    "Cờ": HELP["flags"],
    "Mã": "Mã cổ phiếu VN100. Bấm một dòng để xem thẻ chi tiết của mã.",
    "Nhãn": "Kết luận dòng tiền của mã: ▲ Dấu hiệu gom · ▼ Dấu hiệu xả (khối ngoại dẫn) · △ Nội gom · ▽ Nội xả "
    "(ngoại không có chiều; giá-KL + KL đột biến) · 0 Trung tính · ◌ Chưa đủ dữ liệu, tổng hợp từ ba phiếu (cột "
    "Phiếu). Mô tả dữ liệu quá khứ, không phải khuyến nghị.",
    "Phiếu": HELP["votes"],
    "Bối cảnh": HELP["context"],
    "Ngoại (tỷ)": "Khối ngoại mua − bán (tỷ đồng) trong cửa sổ/phiên. Dương = mua ròng, âm = bán ròng.",
    "R_F (%)": "Mua ròng khối ngoại ÷ giá trị giao dịch (GTGD) trên các phiên hợp lệ. Đo sức mua/bán của ngoại "
    "so với thanh khoản của chính mã.",
    "Tự doanh (tỷ)": "Tự doanh CTCK mua − bán (tỷ đồng), chỉ trên các phiên nguồn có số.",
    "CMF20": "Chaikin Money Flow 20 phiên, tính trên biên độ thực (True Range: biên độ phiên nới ra tới giá đóng "
    "cửa phiên trước, như Twiggs Money Flow): đóng cửa gần mức cao + khối lượng lớn → dương (áp lực mua); gần mức "
    "thấp → âm. Từ −1 đến +1. Phiên nhảy giá, kể cả trần/sàn trắng bên, đều được tính.",
    "ret20 (%)": "Biến động giá 20 phiên gần nhất (ROC 20).",
    "Giữ nhãn từ": HELP["held"],
    "Upside (%)": HELP["upside"],
    "Huy hiệu": "Ghi chú sự kiện đáng chú ý của mã trong cửa sổ: thỏa thuận lớn, GDKHQ (giá/GTGD đã điều chỉnh)…",
    "Ngày": "Ngày giao dịch.",
    "Thỏa thuận": "Phiên có giao dịch thỏa thuận: KL (≥ = cận dưới ước tính khi nguồn không có số chính xác) và "
    "giá trị ước tính. Chế độ Loại bỏ các phiên này khỏi phép tính.",
    "Dạng": "Bên chủ động trong thỏa thuận: ngoại mua / ngoại bán / tự doanh mua / tự doanh bán; "
    "ngoại↔ngoại = khối ngoại sang tay cho nhau.",
    "Đo": "Giá trị đo được của phiếu trong cửa sổ (tỷ lệ trên GTGD, hoặc CMF).",
    "Ngưỡng": "Mức phải vượt để phiếu thành ▲/▼; chưa vượt thì phiếu = 0.",
    "Ghi chú": "Lý do phiếu ra kết quả hiện tại (vd thiếu dữ liệu, chưa đủ phiên).",
    "Cửa sổ": "Số phiên giao dịch gần nhất được cộng dồn.",
    "Phủ TD (%)": "Độ phủ số liệu tự doanh: % GTGD của cửa sổ nằm trên các phiên nguồn có số tự doanh. "
    "Phủ thấp → phiếu tự doanh kém tin cậy.",
    "Ngoại mua (cp)": "Khối lượng khối ngoại mua trong phiên (cổ phiếu).",
    "Ngoại bán (cp)": "Khối lượng khối ngoại bán trong phiên (cổ phiếu).",
    "TD mua (cp)": "Khối lượng tự doanh CTCK mua trong phiên (cổ phiếu).",
    "TD bán (cp)": "Khối lượng tự doanh CTCK bán trong phiên (cổ phiếu).",
    "KL khớp (cp)": "Khối lượng khớp lệnh của phiên. Ngoại/tự doanh mua hoặc bán vượt KL khớp → phiên có thỏa thuận.",
}
COLUMN_HELP_PREFIX = {"Ngoại ": HELP["foreign"], "Tự doanh ": HELP["prop"]}

# Giải thích khi rê chuột vào dấu (?) ở tiêu đề từng tầng biểu đồ chi tiết mã (money_flow.flow_chart).
CHART_HELP = {
    "Giá": "Nến giá đã điều chỉnh cổ tức/quyền: xanh = đóng cửa ≥ mở cửa, đỏ = ngược lại. "
    "MA20/MA50: trung bình giá đóng cửa 20/50 phiên. ◆ phiên có thỏa thuận lớn (rê vào ◆ xem KL). "
    "▲ ngày giao dịch không hưởng quyền (GDKHQ).",
    "Khối lượng": "Khối lượng khớp lệnh mỗi phiên: xanh = phiên tăng, đỏ = phiên giảm. "
    "Chế độ Gồm vẽ thêm khối lượng thỏa thuận (tím).",
    "Khối ngoại": "Cột: khối ngoại mua − bán khớp lệnh trong phiên (tỷ đồng), xanh = mua ròng, đỏ = bán ròng. "
    "Đường (trục phải): cộng dồn từ đầu khung — đi lên = ngoại đang gom, đi xuống = đang xả. "
    "Chế độ Gồm cộng cả thỏa thuận (tím).",
    "Tự doanh": "Cột: tự doanh CTCK mua − bán trong phiên (tỷ đồng). Đường (trục phải): cộng dồn từ đầu khung. "
    "Chỉ là phiếu phụ: tự doanh có thể mua/bán để phòng hộ chứng quyền/ETF, không hẳn là quan điểm.",
    "Ai gom/xả": "Đường (trục phải): mua ròng cộng dồn từ đầu khung (tỷ) của khối ngoại, tự doanh và trong nước. "
    "Trong nước là số suy ra = −(ngoại + tự doanh), vì mỗi cổ phiếu mua vào có người bán ra. "
    "Đường đi lên = nhóm đó đang gom, đi xuống = đang xả. "
    "Nền xanh/đỏ (trục trái) = CMF20, "
    + COLUMN_HELP["CMF20"]
    + " Hai đường 0 trùng nhau.",
    "MACD": "MACD = EMA12 − EMA26 của giá đóng cửa; đường tín hiệu = EMA9 của MACD; cột = MACD − tín hiệu. "
    "MACD cắt lên đường tín hiệu: động lượng giá tăng; cắt xuống: động lượng giảm.",
}


def column_help(col: str) -> str | None:
    """Giải thích tiêu đề cột; None nếu chưa có (không bịa)."""
    if col in COLUMN_HELP:
        return COLUMN_HELP[col]
    return next((h for p, h in COLUMN_HELP_PREFIX.items() if col.startswith(p)), None)


# ---------- ví dụ sinh từ dữ liệu ----------
def _tk(res: dict, t: str | None) -> dict | None:
    return res.get("tickers", {}).get(t) if t else None


_NUM = ("close", "high", "low", "vol_adj", "volume", "gtgd", "f", "f_gom", "p", "p_gom")


def series_frame(tk: dict) -> pd.DataFrame:
    """Chuỗi chi tiết của mã thành DataFrame; cột số ép float (cột toàn None → NaN, không object)."""
    s = pd.DataFrame(tk["series"])
    s[list(_NUM)] = s[list(_NUM)].astype(float)
    return s


def _window(tk: dict, n: int) -> pd.DataFrame:
    return series_frame(tk).iloc[-n:]


def _ex_l1(res: dict, t: str | None, cfg: dict) -> str:
    tk = _tk(res, t)
    if not tk:
        return "Chọn một mã VN100 ở ô tra mã để xem GTGD 20 phiên của mã đó."
    g = _window(tk, int(cfg["window"]))["gtgd"].dropna()
    if g.empty:
        return f"{t} chưa có GTGD trong cửa sổ."
    return (
        f"GTGD {len(g)} phiên của {t} ≈ {_bn(g.sum())}, bình quân ≈ {_bn(g.mean())}/phiên "
        "(ước = giá đóng cửa × KL khớp)."
    )


def _ex_l2(res: dict, t: str | None, cfg: dict) -> str:
    tot = res.get("modes", {}).get("loai", {}).get("totals", {})
    if not tot.get("block_n"):
        return "Cửa sổ hiện tại chưa có phiên-mã nào bị gắn cờ thỏa thuận."
    s = f"Cửa sổ {cfg['window']} phiên có {tot['block_n']} phiên-mã có cờ thỏa thuận"
    if tot.get("block_f") is not None:
        s += f", ngoại {_ty(tot['block_f'])} trong các phiên đó"
    big = next(
        (b for b in (_tk(res, t) or {}).get("badges", []) if "Thỏa thuận lớn" in b),
        None,
    )
    return s + (f". {t}: {big}." if big else ".")


def _ex_l3(res: dict, t: str | None, cfg: dict) -> str:
    tk = _tk(res, t)
    if not tk:
        return "Chọn một mã để xem phiên tự doanh lớn nhất của mã đó."
    s = series_frame(tk).dropna(subset=["p"])
    if s.empty:
        return (
            f"{t} chưa có số tự doanh trong {len(tk['series']['date'])} phiên gần nhất."
        )
    r = s.loc[s["p"].abs().idxmax()]
    side = "mua" if r["p"] >= 0 else "bán"
    return (
        f"Phiên tự doanh lớn nhất của {t} trong {len(tk['series']['date'])} phiên: "
        f"{_dm(r['date'])}, tự doanh {side} ròng {_bn(r['p'])}."
    )


def _ex_l4(res: dict, t: str | None, cfg: dict) -> str:
    tk = _tk(res, t)
    if not tk:
        return "Chọn một mã để xem đẳng thức ngoại + tự doanh + trong nước = 0."
    s = _window(tk, int(cfg["window"]))
    ok = s["close"].notna() & ~s["excl"] & s["f"].notna() & s["p"].notna()
    if not ok.any():
        return f"{t} chưa có phiên nào có cả số ngoại lẫn tự doanh trong cửa sổ."
    f, p = float(s.loc[ok, "f"].sum()), float(s.loc[ok, "p"].sum())
    d = float(implied_domestic(s.loc[ok, "f"], s.loc[ok, "p"]).sum())
    return (
        f"Trên {int(ok.sum())}/{len(s)} phiên có cả số ngoại lẫn tự doanh của {t}: ngoại {_ty(f)} "
        f"+ tự doanh {_ty(p)} + trong nước suy ra {_ty(d)} = 0."
    )


def spearman_rf_ret(res: dict) -> tuple[float | None, int]:
    """Tương quan hạng (Spearman = Pearson trên hạng, hạng trùng lấy trung bình) giữa R_F và ret20."""
    rows = [
        (tk["flows"][str(res["meta"]["window"])]["loai"]["r_f"], tk["ret20"])
        for tk in res.get("tickers", {}).values()
    ]
    d = pd.DataFrame(rows, columns=["r_f", "ret"], dtype=float).dropna()
    if len(d) < 3 or d["r_f"].nunique() < 2 or d["ret"].nunique() < 2:
        return None, len(d)  # hằng số → tương quan không xác định
    return float(d["r_f"].rank().corr(d["ret"].rank())), len(d)


def _ex_l5(res: dict, t: str | None, cfg: dict) -> str:
    rho, n = spearman_rf_ret(res) if res.get("tickers") else (None, 0)
    if rho is None:
        return "Chưa đủ mã có cả R_F và ret20 để tính tương quan."
    return (
        f"Tương quan hạng (Spearman) giữa R_F {cfg['window']} phiên và ret20 trên {n} mã: "
        f"{_vi(rho, 2)}. Đây là tương quan cùng kỳ (mã được mua ròng thường là mã đã tăng giá), "
        "không phải dự báo."
    )


def _ex_l6(res: dict, t: str | None, cfg: dict) -> str:
    tk = _tk(res, t)
    if not tk:
        return "Chọn một mã để xem CMF20 của mã đó."
    return f"{t}: {tk['votes']['pv']['chip']}."


def _ex_l7(res: dict, t: str | None, cfg: dict) -> str:
    tk = _tk(res, t)
    if not tk:
        return "Chọn một mã để xem hậu tố bối cảnh giá."
    return (
        f"Hậu tố của {t}: «{tk['context']}» — chỉ mô tả giá, app không gán pha Wyckoff."
    )


def _ex_l8(res: dict, t: str | None, cfg: dict) -> str:
    rows = [
        r
        for r in res.get("modes", {}).get("loai", {}).get("sectors", [])
        if not r["small"] and r["r_f"] is not None
    ]
    if len(rows) < 2:
        return "Chưa đủ ngành để so sánh."
    hi, lo = max(rows, key=lambda r: r["r_f"]), min(rows, key=lambda r: r["r_f"])
    return (
        f"Đến {_dm(res['meta']['flow_date'])}: R_F cao nhất là {hi['sector']} ({_chg(hi['r_f'])}), "
        f"thấp nhất là {lo['sector']} ({_chg(lo['r_f'])}) — chỉ xét ngành ≥ {cfg['small_sector_n']} mã."
    )


def _ex_l9(res: dict, t: str | None, cfg: dict) -> str:
    up = res.get("upside", {})
    row = up.get("rows", {}).get(t) if t else None
    if not row or row["upside"] is None:
        return "Mã đang xem chưa có upside từ đợt định giá VN100."
    note = f", ghi chú: {row['note']}" if row["note"] else ""
    return f"Upside mô hình của {t}: {_chg(row['upside'])} ({up['source']}{note})."


def _ex_l10(res: dict, t: str | None, cfg: dict) -> str:
    n = position_size(50_000_000, 0.02, 50_000, 45_000, int(cfg["lot_size"]))
    return f"50.000.000 × 2% / (50.000 − 45.000) = {_vi(n)} cp."


LESSONS: list[tuple[str, str, Example]] = [
    (
        "L1 · Thanh khoản",
        (
            "GTGD (giá trị giao dịch) = giá × khối lượng khớp; ADTV20 = GTGD bình quân 20 phiên. "
            "HOSE: biên độ giá ±7% quanh giá tham chiếu, thanh toán T+2, lô chẵn 100 cp (bản trích quy "
            "chế HOSE của MBS). Trong app, GTGD là **ước tính** = giá đóng cửa × KL khớp (có quy đổi khi "
            "có cổ tức cổ phiếu/thưởng), vì cột giá trị trong DB đang trống."
        ),
        _ex_l1,
    ),
    (
        "L2 · Khớp lệnh và thỏa thuận",
        (
            "Khớp lệnh: lệnh vào sổ và khớp theo giá, tạo ra giá đóng cửa. Thỏa thuận: hai bên tự chốt giá "
            "và KL rồi báo qua sàn (HOSE: từ {pt} cp trở lên), không tạo giá đóng cửa. Một phiên thỏa "
            "thuận lớn có thể làm mua/bán ròng của ngoại lệch hẳn phần khớp lệnh, nên tab có công tắc "
            "**Loại/Gồm**. Ví dụ đã đối chiếu khi lập kế hoạch D73: MCH 09/10/2026 ngoại bán khoảng 64,3 "
            "triệu cp trong khi KL khớp cả phiên chỉ khoảng 0,8 triệu; sở hữu ngoại giảm từ khoảng 16% "
            "xuống khoảng 11%. Bảng khối ngoại của CafeF chỉ tính khớp lệnh nên ngày đó ghi +47,5 tỷ."
        ),
        _ex_l2,
    ),
    (
        "L3 · Các nhóm nhà đầu tư",
        (
            "Có số theo ngày cho khối ngoại và tự doanh CTCK; phần còn lại là nhà đầu tư trong nước "
            "(chủ yếu cá nhân). Số tham khảo: cá nhân khoảng 82%, khối ngoại khoảng 10–12% thanh khoản "
            "HOSE (cần kiểm lại theo báo cáo HOSE mới nhất). Room/FOL là giới hạn sở hữu nước ngoài: mã "
            "kín room thì ngoại khó mua thêm. Tự doanh có thể mua/bán để phòng hộ chứng quyền có bảo đảm "
            "(TT 107/2016/TT-BTC) hoặc hoán đổi chứng chỉ quỹ ETF (TT 229/2012/TT-BTC), không nhất thiết "
            "là quan điểm đầu tư."
        ),
        _ex_l3,
    ),
    (
        "L4 · «Mua ròng» là gì",
        (
            "Mỗi cổ phiếu được mua đều có người bán. Mua ròng của một nhóm = mua − bán của nhóm đó, và "
            "tổng mua ròng của mọi nhóm luôn bằng 0. Vì vậy app không dùng chữ «tiền vào/tiền ra» mà ghi "
            "«mua ròng/bán ròng» của từng nhóm. Trong nước suy ra D = −(ngoại + tự doanh), chỉ đúng khi có "
            "số cả hai nhóm và hai nhóm không trùng người."
        ),
        _ex_l4,
    ),
    (
        "L5 · Mua ròng ≠ giá sẽ tăng",
        (
            "Nghiên cứu quốc tế cho thấy khối ngoại thường mua theo đà, tức mua sau khi giá đã tăng "
            "(Froot, O'Connell & Seasholes 2001; Richards 2005). Ở Việt Nam, bằng chứng dòng tiền ngoại "
            "dự báo được giá còn yếu và có dấu hiệu hành vi bầy đàn. Nhãn trong tab là mô tả quá khứ, "
            "chưa backtest."
        ),
        _ex_l5,
    ),
    (
        "L6 · Dòng tiền ẩn danh qua giá-KL",
        (
            "Khi không biết ai mua/bán, có thể đọc gián tiếp từ vị trí giá đóng cửa trong biên độ ngày và "
            "KL: OBV, đường A/D, CMF. CMF20 = Σ(MFM × KL)/ΣKL với MFM = ((C−TRL) − (TRH−C))/(TRH−TRL), "
            "TRH/TRL = cao/thấp của phiên nới tới giá đóng cửa phiên trước (biên độ thực, như ATR; ý tưởng "
            "của Twiggs Money Flow): đóng cửa gần giá cao thì dương. CMF gốc của StockCharts chỉ dùng H/L "
            "trong phiên nên bỏ sót phiên nhảy giá — trần trắng bên (H = L) không xác định được; biên độ "
            "thực tính phiên đó là +1. Các chỉ báo này cùng dùng giá và KL nên tương quan với nhau "
            "(multicollinearity), app chỉ giữ 1 phiếu Giá-KL (CMF20); OBV chỉ để minh họa. Phiên đứng giá "
            "(cao = thấp = giá phiên trước) không xác định MFM nên bị loại."
        ),
        _ex_l6,
    ),
    (
        "L7 · Gom hàng theo Wyckoff",
        (
            "Wyckoff mô tả giai đoạn tích lũy: giá đi ngang sau một xu hướng giảm, KL lớn nhưng giá không "
            "giảm thêm (Effort vs Result). Các pha chỉ thấy rõ khi nhìn lại, nên app không tự gán pha; "
            "hậu tố chỉ mô tả giá («giá đi ngang», «giá đã tăng x%»)."
        ),
        _ex_l7,
    ),
    (
        "L8 · Ngành và luân chuyển",
        (
            "Bản đồ ngành tô màu theo R_F, cắt ở ±{clip}% để ngành nhỏ không lấn màu. Xem cột «Mã chi "
            "phối» (một mã lớn có thể kéo cả ngành) và cột gom/xả. Ngành dưới {small} mã xếp cuối. RS20 = "
            "trung vị (ret20 của mã − trung vị VN100) trong ngành. Biểu đồ luân chuyển kiểu RRG chỉ là "
            "khung tham khảo, không phải hệ thống giao dịch."
        ),
        _ex_l8,
    ),
    (
        "L9 · Kết hợp định giá",
        (
            "Upside = giá trị hợp lý của mô hình ÷ giá − 1. Trong tab chỉ là cột phụ vì giá trị hợp lý "
            "chưa qua golden test (luật #8). Value và momentum tương quan âm (Asness, Moskowitz & Pedersen "
            "2013): mã «rẻ» thường đang bị bán, nên «rẻ + bị bán» là vùng chờ xác nhận, không phải tín hiệu."
        ),
        _ex_l9,
    ),
    (
        "L10 · Quản trị rủi ro",
        (
            "Số cp = vốn × % rủi ro ÷ (giá vào − giá stop), làm tròn xuống lô {lot} cp (quy ước của app; "
            "HOSE có khớp lô lẻ). Giá stop đặt theo cấu trúc giá (đáy gần nhất) hoặc theo ATR "
            "(StockCharts). App không gợi ý giá vào hay giá stop; máy tính dưới đây chỉ dùng số bạn nhập."
        ),
        _ex_l10,
    ),
]


def lesson_texts(
    res: dict, ticker: str | None, cfg: dict
) -> list[tuple[str, str, str]]:
    """(tiêu đề, nội dung tĩnh, ví dụ từ dữ liệu) của 10 bài."""
    fill = {
        "pt": _vi(cfg["hose_put_through_min_shares"]),
        "clip": _vi(cfg["heat_clip"] * 100),
        "small": cfg["small_sector_n"],
        "lot": cfg["lot_size"],
    }
    return [(t, body.format(**fill), ex(res, ticker, cfg)) for t, body, ex in LESSONS]


def render_lessons(res: dict, ticker: str | None, cfg: dict) -> None:
    import streamlit as st

    with st.expander("Học từ cơ bản (10 bài)", expanded=False):
        for title, body, ex in lesson_texts(res, ticker, cfg):
            st.markdown(f"**{title}**\n\n{body}")
            st.caption(f"Ví dụ từ dữ liệu: {ex}")
        _calculator(int(cfg["lot_size"]))


def _calculator(lot: int) -> None:
    import streamlit as st

    st.markdown("**Máy tính khối lượng vị thế (L10)** — chỉ dùng số bạn nhập")
    c = st.columns(4)
    capital = c[0].number_input(
        "Vốn (đ)", min_value=0.0, value=None, step=1e6, key="flow_calc_cap"
    )
    risk = c[1].number_input(
        "% rủi ro",
        min_value=0.0,
        max_value=100.0,
        value=None,
        step=0.5,
        key="flow_calc_risk",
    )
    entry = c[2].number_input(
        "Giá vào (đ)", min_value=0.0, value=None, step=100.0, key="flow_calc_entry"
    )
    stop = c[3].number_input(
        "Giá stop (đ)", min_value=0.0, value=None, step=100.0, key="flow_calc_stop"
    )
    if capital is None or risk is None or entry is None or stop is None:
        st.caption("Nhập đủ 4 ô để tính.")
        return
    try:
        n = position_size(capital, risk / 100, entry, stop, lot)
    except ValueError as e:  # nhập sai là lỗi người dùng → báo, không tính
        st.error(str(e))
        return
    st.success(
        f"{_vi(capital)} × {_vi(risk, 1)}% ÷ ({_vi(entry)} − {_vi(stop)}) → **{_vi(n)} cp** "
        f"(làm tròn xuống lô {lot})"
    )
    if n * entry > capital:
        st.warning(
            f"Giá trị vị thế {_vi(n * entry)} đ vượt vốn {_vi(capital)} đ (cần vay margin): "
            "stop quá sát giá vào hoặc % rủi ro quá lớn."
        )
