import pytest
from unittest.mock import patch, MagicMock
from checker import is_ip_blocked

def test_not_blocked_when_both_apis_say_accessible():
    with patch("checker._check_pingpe", return_value=False), \
         patch("checker._check_ipcheck", return_value=False):
        assert is_ip_blocked("1.2.3.4", port=22, timeout=5) is False

def test_blocked_when_both_apis_say_inaccessible():
    with patch("checker._check_pingpe", return_value=True), \
         patch("checker._check_ipcheck", return_value=True):
        assert is_ip_blocked("1.2.3.4", port=22, timeout=5) is True

def test_not_blocked_when_only_one_api_reports_inaccessible():
    with patch("checker._check_pingpe", return_value=True), \
         patch("checker._check_ipcheck", return_value=False):
        assert is_ip_blocked("1.2.3.4", port=22, timeout=5) is False

def test_fallback_to_tcp_when_all_apis_unavailable():
    with patch("checker._check_pingpe", return_value=None), \
         patch("checker._check_ipcheck", return_value=None), \
         patch("checker._check_tcp", return_value=True):
        assert is_ip_blocked("1.2.3.4", port=22, timeout=5) is True

def test_fallback_tcp_accessible():
    with patch("checker._check_pingpe", return_value=None), \
         patch("checker._check_ipcheck", return_value=None), \
         patch("checker._check_tcp", return_value=False):
        assert is_ip_blocked("1.2.3.4", port=22, timeout=5) is False
