from types import SimpleNamespace

from ib_async import RealTimeBarList

from backend.signals.service import PERMISSION_RETRY_SECONDS, SignalService

MACRO_ERROR = "Requested market data is not subscribed.YM DEC'26/TOP/ALL"


def streaming_service(req_id=7):
    service = SignalService()
    service.stream = "streaming"
    service.rt_bars = RealTimeBarList()
    service.rt_bars.reqId = req_id
    return service


def test_another_features_error_without_a_contract_leaves_the_stream_running():
    service = streaming_service()
    service._on_error(46, 354, MACRO_ERROR, None)
    assert service.stream == "streaming" and service.error is None and service.rt_bars is not None


def test_another_contracts_error_leaves_the_stream_running():
    service = streaming_service()
    service._on_error(46, 10197, "competing session", SimpleNamespace(symbol="NQ"))
    assert service.stream == "streaming"


def test_the_streams_own_error_stops_it_even_without_a_contract():
    service = streaming_service()
    service._on_error(7, 354, "not subscribed", None)
    assert service.stream == "error" and service.rt_bars is None
    assert service._retry_at is not None and PERMISSION_RETRY_SECONDS == 300


def test_an_error_for_the_symbol_stops_the_stream():
    service = streaming_service()
    service._on_error(99, 10197, "competing session", SimpleNamespace(symbol="SOXL"))
    assert service.stream == "error"


def test_a_session_wide_error_stops_the_stream():
    service = streaming_service()
    service._on_error(-1, 10197, "competing session", None)
    assert service.stream == "error"


def test_warmup_errors_for_the_symbol_still_count():
    service = SignalService()
    service.stream = "warming_up"
    service._on_error(12, 162, "no data", SimpleNamespace(symbol="SOXL"))
    assert service.stream == "error"
