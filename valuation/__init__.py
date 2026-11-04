import os
import sys

import numpy as np

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_PKG_DIR)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)


def _numpy_keeps_locals() -> bool:
    """False nếu numpy ghi đè mảng cục bộ (D82): numpy < 2.3 trên Python 3.14 coi biến cục bộ
    là mảng tạm khi ≥ 256 KiB (NPY_MIN_ELIDE_BYTES) → pivot/unstack ra nhãn index sai âm thầm.
    """
    x = np.ones(256 * 1024 // 8)
    _ = x + 1.0
    return bool(x[0] == 1.0)


if not _numpy_keeps_locals():
    raise RuntimeError(
        f"numpy {np.__version__} trên Python {sys.version.split()[0]} ghi đè mảng cục bộ "
        "≥ 32.768 phần tử (D82) — pivot/unstack sẽ cho kết quả sai âm thầm. Sửa: "
        f"{sys.executable} -m pip install --no-deps numpy==2.3.5 (hoặc dùng Python 3.12/3.13)."
    )
