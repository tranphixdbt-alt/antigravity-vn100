from valuation.ingest import vnstock_client as client_module


def test_vnstock_client_applies_configured_key_once(monkeypatch):
    calls = []
    monkeypatch.setattr(client_module.settings, "vnstock_api_key", "test-key")
    monkeypatch.setattr(
        client_module,
        "_configure_vnstock_api_key",
        lambda key: calls.append(key),
    )
    client = client_module.VnstockClient()

    client._ensure_api_key()
    client._ensure_api_key()

    assert calls == ["test-key"]


def test_vnstock_client_skips_setup_without_key(monkeypatch):
    calls = []
    monkeypatch.setattr(client_module.settings, "vnstock_api_key", "")
    monkeypatch.setattr(
        client_module,
        "_configure_vnstock_api_key",
        lambda key: calls.append(key),
    )

    client_module.VnstockClient()._ensure_api_key()

    assert calls == []


def test_vnai_threading_bug_retried_once():
    # vnai 2.5.9 beam/quota.py: `import threading` cục bộ → UnboundLocalError ở lượt đồng bộ quota; bộ đếm
    # đã reset trước khi lỗi nên gọi lại ngay là qua. Thiếu giá MCH, VPI phiên 10/11 vì lỗi này.
    import pytest

    bug = UnboundLocalError(
        "cannot access local variable 'threading' where it is not associated with a value"
    )
    calls = []

    def flaky(outcomes):
        def fn():
            calls.append(1)
            out = outcomes.pop(0)
            if isinstance(out, BaseException):
                raise out
            return out

        return fn

    assert client_module._call_with_rate_limit_retry(flaky([bug, "ok"])) == "ok"
    assert len(calls) == 2

    calls.clear()  # lỗi lặp lại → nổi lên, không thử mãi
    with pytest.raises(UnboundLocalError):
        client_module._call_with_rate_limit_retry(flaky([bug, bug, "ok"]))
    assert len(calls) == 2

    calls.clear()  # UnboundLocalError khác (lỗi code thật) → không nuốt
    other = UnboundLocalError("cannot access local variable 'x'")
    with pytest.raises(UnboundLocalError):
        client_module._call_with_rate_limit_retry(flaky([other, "ok"]))
    assert len(calls) == 1
