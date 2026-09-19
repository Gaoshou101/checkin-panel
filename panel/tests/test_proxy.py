"""Tests for proxy resolution and CHECKIN_PROXY_OVERRIDES."""
import json
import pytest
from panel.vendor.utils.proxy import get_proxy_server, _extract_host

def test_extract_host():
	assert _extract_host('https://anyrouter.top/login') == 'anyrouter.top'
	assert _extract_host('http://anyrouter.top:8080/foo') == 'anyrouter.top'
	assert _extract_host('anyrouter.top:443') == 'anyrouter.top'
	assert _extract_host('anyrouter.top') == 'anyrouter.top'
	assert _extract_host('sub.domain.com') == 'sub.domain.com'
	assert _extract_host('') is None
	assert _extract_host(None) is None

def test_proxy_server_default(monkeypatch):
	monkeypatch.setenv('CHECKIN_PROXY_URL', 'socks5://127.0.0.1:1080')
	monkeypatch.delenv('CHECKIN_PROXY_OVERRIDES', raising=False)
	assert get_proxy_server() == 'socks5://127.0.0.1:1080'
	assert get_proxy_server(url='https://example.com') == 'socks5://127.0.0.1:1080'
	assert get_proxy_server(use_proxy=False) is None

def test_proxy_server_overrides(monkeypatch):
	monkeypatch.setenv('CHECKIN_PROXY_URL', 'socks5://default:1080')
	overrides = {
		'anyrouter.top': 'http://clash:7890',
		'direct.com': 'DIRECT',
		'empty.com': '',
	}
	monkeypatch.setenv('CHECKIN_PROXY_OVERRIDES', json.dumps(overrides))

	# Overridden host
	assert get_proxy_server(url='https://anyrouter.top/api/status') == 'http://clash:7890'
	# Subdomain match
	assert get_proxy_server(url='https://sub.anyrouter.top') == 'http://clash:7890'
	# Non-matching host falls back to default
	assert get_proxy_server(url='https://tabitoken.com') == 'socks5://default:1080'
	# Direct override
	assert get_proxy_server(url='https://direct.com/test') is None
	assert get_proxy_server(url='https://empty.com') is None

def test_proxy_server_malformed_overrides(monkeypatch):
	monkeypatch.setenv('CHECKIN_PROXY_URL', 'socks5://default:1080')
	monkeypatch.setenv('CHECKIN_PROXY_OVERRIDES', 'invalid json')
	# Does not crash and falls back
	assert get_proxy_server(url='https://anyrouter.top') == 'socks5://default:1080'

def test_proxy_pool(monkeypatch):
	from panel.vendor.utils.proxy import get_proxy_pool
	# Test semicolon separated list
	monkeypatch.setenv('CHECKIN_PROXY_POOL', 'socks5://p1:1080;socks5://p2:1080')
	monkeypatch.delenv('CHECKIN_PROXY_URL', raising=False)
	assert get_proxy_pool() == ['socks5://p1:1080', 'socks5://p2:1080']
	# Test fallback in get_proxy_server
	assert get_proxy_server() == 'socks5://p1:1080'

	# Test JSON format
	monkeypatch.setenv('CHECKIN_PROXY_POOL', '["socks5://j1:1080", "socks5://j2:1080"]')
	assert get_proxy_pool() == ['socks5://j1:1080', 'socks5://j2:1080']
