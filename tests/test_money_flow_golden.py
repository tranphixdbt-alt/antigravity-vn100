"""Golden T17/TB6 (D73): khối ngoại trong DB so với nguồn ngoài CafeF.

Nguồn: https://cafef.vn/du-lieu/Ajax/PageNew/DataHistory/GDKhoiNgoai.ashx?Symbol=FPT
(truy cập 24/10/2026). CafeF GDKhoiNgoai chỉ tính KHỚP LỆNH, nên:
- prices_daily (gồm cả thỏa thuận) chỉ so ở phiên KHÔNG có thỏa thuận (ASEAN put_through = 0);
- flow_daily.fr_*_match (B1) so được cả phiên có thỏa thuận (MCH 09/10).
Sai số đo trên giá trị mua, bán và |Δròng| / (mua + bán): ròng gần 0 thì % trên ròng không ổn định
(FPT 05/10 ròng −3,4 tỷ: lệch 0,16 tỷ = 4,6% ròng nhưng chỉ 0,35% tổng giao dịch).
"""

import pytest
from sqlalchemy import inspect, text

from valuation.config import load_defaults
from valuation.db.session import SessionLocalRead

TOL = float(load_defaults()["money_flow"]["golden_flow_tol"])

# (mã, ngày): (giá trị mua, giá trị bán) khối ngoại khớp lệnh theo CafeF, VND.
CAFEF_NO_DEAL = {
    ("FPT", "2026-10-05"): (20_887_230_000, 24_261_170_000),
    ("FPT", "2026-10-19"): (31_174_440_000, 73_298_880_000),
    ("FPT", "2026-10-20"): (30_252_030_000, 48_086_340_000),
    ("FPT", "2026-10-22"): (90_604_550_000, 354_795_600_000),
}
# Phiên CÓ thỏa thuận: chỉ phần khớp lệnh của flow_daily mới so được với CafeF.
CAFEF_MATCH_NET = {
    ("FPT", "2026-10-09"): -120_636_110_000,
    ("FPT", "2026-10-12"): -91_175_310_000,
    ("FPT", "2026-10-15"): 15_204_720_000,
    ("MCH", "2026-10-09"): 47_530_000_000,  # CafeF +47,53 tỷ (làm tròn 10 triệu)
}


@pytest.fixture
def db():
    session = SessionLocalRead()
    yield session
    session.close()


def _err(db_buy: float, db_sell: float, buy: float, sell: float) -> float:
    return max(
        abs(db_buy - buy) / buy,
        abs(db_sell - sell) / sell,
        abs((db_buy - db_sell) - (buy - sell)) / (buy + sell),
    )


@pytest.mark.parametrize(("key", "ref"), list(CAFEF_NO_DEAL.items()))
def test_prices_daily_foreign_matches_cafef(db, key, ref):
    row = db.execute(
        text(
            "SELECT foreign_buy_val, foreign_sell_val FROM prices_daily "
            "WHERE ticker = :t AND trade_date = :d"
        ),
        {"t": key[0], "d": key[1]},
    ).fetchone()
    if row is None or row[0] is None:
        pytest.skip(f"DB chưa có khối ngoại {key}")
    assert _err(row[0], row[1], *ref) < TOL, f"{key}: lệch vượt {TOL:.0%}"


@pytest.mark.parametrize(("key", "ref_net"), list(CAFEF_MATCH_NET.items()))
def test_flow_daily_match_net_matches_cafef(db, key, ref_net):
    if "flow_daily" not in inspect(db.get_bind()).get_table_names():
        pytest.skip("Chưa có bảng flow_daily (B1)")
    row = db.execute(
        text(
            "SELECT fr_net_match_val, fr_buy_match_val, fr_sell_match_val FROM flow_daily "
            "WHERE ticker = :t AND trade_date = :d"
        ),
        {"t": key[0], "d": key[1]},
    ).fetchone()
    if row is None or row[0] is None:
        pytest.skip(f"flow_daily chưa có {key}")
    gross = row[1] + row[2]
    assert abs(row[0] - ref_net) / gross < TOL, f"{key}: ròng khớp lệnh {row[0]:,.0f} ≠ CafeF {ref_net:,.0f}"
