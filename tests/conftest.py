import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pytest


@pytest.fixture
def web_approved():
    """Test số liệu của web hợp nhất (lát 1–4) gọi route như một tài khoản đã duyệt.

    Từ lát 5a mọi route số liệu đòi đăng nhập và đã duyệt; phần đó có test riêng ở test_web_auth.py.
    """
    from valuation.api import web_main
    from valuation.api.web_deps import require_approved

    web_main.app.dependency_overrides[require_approved] = lambda: None
    yield
    web_main.app.dependency_overrides.pop(require_approved, None)
