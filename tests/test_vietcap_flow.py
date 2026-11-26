"""Vá phiên khối ngoại FHSC trả trống bằng Vietcap IQ (lỗi 23/11/2026). Không gọi mạng: nguồn và hàm ghi là giả.

Số mẫu là dòng thật của FPT Vietcap trả ngày 26/11/2026 (rút gọn cột), đối chiếu TCBS: khớp lệnh mua 4.177.805 cp.
"""

from __future__ import annotations

import datetime as dt
import io
import json

import pandas as pd
import pytest

from valuation.ingest import vietcap_flow as v

FPT_23_11 = {
    "tradingDate": "2026-11-23T00:00:00",
    "foreignBuyVolumeMatched": 4177805.0,
    "foreignBuyVolumeDeal": 722000.0,
    "foreignBuyVolumeTotal": 4899805.0,
    "foreignBuyValueTotal": 225151047950.0,
    "foreignSellVolumeTotal": 4380795.0,
    "foreignSellValueTotal": 200121286500.0,
    "foreignNetValueTotal": 25029761450.0,
}
FPT_20_11 = {
    "tradingDate": "2026-11-20T00:00:00",
    "foreignBuyVolumeTotal": 4227064.0,
    "foreignBuyValueTotal": 190506514800.0,
    "foreignSellVolumeTotal": 7705567.0,
    "foreignSellValueTotal": 347521285750.0,
}


def test_doc_dong_vietcap_tinh_tay():
    df = v.parse([FPT_23_11])
    r = df.iloc[0]
    assert r["time"] == dt.date(2026, 11, 23)
    # Tổng = khớp lệnh + thỏa thuận: 4.177.805 + 722.000 = 4.899.805 cp
    assert r["buy_vol"] == 4177805 + 722000
    # ròng = mua − bán: 225.151.047.950 − 200.121.286.500 = 25.029.761.450 đ, đúng cột ròng của Vietcap
    assert r["net_val"] == 25029761450.0 == FPT_23_11["foreignNetValueTotal"]
    assert r["net_vol"] == 4899805 - 4380795 == 519010
    # Cùng định nghĩa cột FHSC đã ghi cho phiên 20/11: FHSC mua 4.227.064 cp, ròng −3.478.503 cp
    p = v.parse([FPT_20_11]).iloc[0]
    assert (p["buy_vol"], p["net_vol"]) == (4227064, -3478503)
    with pytest.raises(v.VietcapFlowError):
        v.parse([{"tradingDate": "2026-11-23T00:00:00"}])


def test_lay_mot_ma_qua_api(monkeypatch):
    seen = {}

    def opener(req, timeout):
        seen["url"], seen["timeout"] = req.full_url, timeout
        return io.BytesIO(
            json.dumps({"data": {"content": [FPT_23_11, FPT_20_11]}}).encode()
        )

    df = v.fetch_foreign("FPT", opener=opener)
    assert "/company/FPT/price-history?" in seen["url"] and "size=30" in seen["url"]
    assert df["time"].tolist() == [dt.date(2026, 11, 23), dt.date(2026, 11, 20)]

    bad = lambda req, timeout: io.BytesIO(b'{"data": null}')
    with pytest.raises(v.VietcapFlowError):
        v.fetch_foreign("FPT", opener=bad)


def test_chi_ghi_dung_phien_can_va_bo_so_0():
    day = dt.date(2026, 11, 23)
    src = {
        "FPT": v.parse([FPT_23_11, FPT_20_11]),
        "AAA": v.parse(
            [{**FPT_23_11, "foreignBuyValueTotal": 0.0, "foreignSellValueTotal": 0.0}]
        ),  # Vietcap cũng trống
    }

    def fetch(t):
        if t == "BBB":
            raise v.VietcapFlowError("Vietcap không trả lời (URLError)")
        return src[t]

    written = {}
    res = v.fill_sessions(
        ["FPT", "AAA", "BBB"],
        [day],
        fetch=fetch,
        write=lambda t, f, p: written.update({t: f}),
        pause=0,
    )
    assert res == {
        "days": ["2026-11-23"],
        "written": 1,
        "missing": ["AAA"],
        "errors": {"BBB": "Vietcap không trả lời (URLError)"},
    }
    assert list(written) == ["FPT"] and written["FPT"]["time"].tolist() == [
        day
    ]  # không ghi lại phiên 20/11
    assert isinstance(written["FPT"], pd.DataFrame)
