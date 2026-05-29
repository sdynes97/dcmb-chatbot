import time

import services.telnyx_service as telnyx_service


def test_stale_timestamp_rejected():
    # A validly-formatted but very old timestamp must be rejected (replay).
    old_ts = str(int(time.time()) - 10_000)
    assert telnyx_service.validate_webhook_signature(b"{}", old_ts, "sig") is False


def test_future_timestamp_rejected():
    future_ts = str(int(time.time()) + 10_000)
    assert telnyx_service.validate_webhook_signature(b"{}", future_ts, "sig") is False


def test_missing_timestamp_rejected():
    assert telnyx_service.validate_webhook_signature(b"{}", "", "sig") is False
    assert telnyx_service.validate_webhook_signature(b"{}", "not-a-number", "sig") is False


def test_fresh_timestamp_but_bad_signature_rejected():
    # Fresh timestamp passes the freshness gate but the bogus signature fails.
    fresh_ts = str(int(time.time()))
    assert telnyx_service.validate_webhook_signature(b"{}", fresh_ts, "not-base64-sig") is False
