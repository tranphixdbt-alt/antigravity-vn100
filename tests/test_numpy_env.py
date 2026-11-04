"""Hồi quy D82: numpy < 2.3 trên Python 3.14 (bản 2.2.6 tự build) ghi đè mảng cục bộ
≥ 32.768 phần tử → pivot/pivot_table/unstack trả nhãn index sai và lặp. Bảng nhỏ vẫn đúng
nên test thường không bắt được; ở đây dùng khung 544 ngày × 100 mã (54.400 ô)."""

from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest

DAYS = pd.date_range("2024-01-01", periods=544, freq="D")
TICKERS = [f"T{i:03d}" for i in range(100)]

RESHAPES: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "pivot": lambda df: df.pivot(index="date", columns="ticker", values="close"),
    "pivot_table": lambda df: df.pivot_table(
        index="date", columns="ticker", values="close", aggfunc="last"
    ),
    "unstack": lambda df: df.set_index(["date", "ticker"])["close"].unstack(),
}


@pytest.mark.parametrize("name", RESHAPES)
def test_reshape_khung_544x100_dung_nhan_ngay(name: str) -> None:
    df = pd.MultiIndex.from_product([DAYS, TICKERS], names=["date", "ticker"]).to_frame(
        index=False
    )
    df["close"] = np.arange(len(df), dtype=float)
    wide = RESHAPES[name](df)
    assert wide.index.is_unique and wide.index.equals(DAYS)
    assert wide.columns.tolist() == TICKERS
    # close = vị trí dòng gốc → ô (ngày i, mã k) phải bằng i*100 + k
    assert wide.at[DAYS[300], "T042"] == 300 * 100 + 42


def test_chot_chan_numpy_khong_ghi_de_bien_cuc_bo() -> None:
    from valuation import _numpy_keeps_locals  # import nổ RuntimeError nếu numpy lỗi

    assert _numpy_keeps_locals()
