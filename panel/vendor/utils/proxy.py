"""代理配置：读取环境变量并供浏览器 / HTTP 客户端使用。"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _extract_host(url_or_host: Optional[str]) -> Optional[str]:
	if not url_or_host:
		return None
	val = str(url_or_host).strip().lower()
	if '://' in val:
		try:
			parsed = urlparse(val)
			return parsed.hostname
		except Exception:
			return None
	val = val.split('/')[0]
	return val.split(':')[0]


def get_proxy_pool() -> list[str]:
	"""读取代理池列表。

	支持：
	- CHECKIN_PROXY_POOL: JSON 数组或分号/逗号/换行分隔的代理列表
	- CHECKIN_PROXY_URL: 作为默认/保底代理加入池中
	"""
	raw = os.getenv('CHECKIN_PROXY_POOL', '').strip()
	pool: list[str] = []
	if raw:
		if raw.startswith('[') and raw.endswith(']'):
			try:
				parsed = json.loads(raw)
				if isinstance(parsed, list):
					pool = [str(x).strip() for x in parsed if str(x).strip()]
			except Exception as e:
				logger.warning(f"Failed to parse CHECKIN_PROXY_POOL as JSON: {e}")
		if not pool:
			for item in raw.replace(chr(10), ";").replace(",", ";").split(";"):
				p = item.strip()
				if p and p not in pool:
					pool.append(p)
	default_url = os.getenv('CHECKIN_PROXY_URL', '').strip()
	if default_url and default_url not in pool:
		pool.append(default_url)
	return pool


def get_proxy_server(*, use_proxy: bool = True, url: Optional[str] = None) -> Optional[str]:
	"""按平台配置读取代理。

	支持：
	- CHECKIN_PROXY_OVERRIDES: JSON 格式的域名映射，例如：
	  {"anyrouter.top": "http://192.168.10.30:7890", "direct.com": "DIRECT"}
	- CHECKIN_PROXY_URL: 全局默认出站代理
	- CHECKIN_PROXY_POOL: 代理池（若未设置 CHECKIN_PROXY_URL，回退到池中首个代理）
	"""
	if not use_proxy:
		return None

	target_host = _extract_host(url)
	overrides_raw = os.getenv('CHECKIN_PROXY_OVERRIDES', '').strip()
	if overrides_raw and target_host:
		try:
			overrides = json.loads(overrides_raw)
			if isinstance(overrides, dict):
				for pattern, proxy_dest in overrides.items():
					pat_host = _extract_host(pattern)
					if pat_host and (target_host == pat_host or target_host.endswith('.' + pat_host)):
						dest = str(proxy_dest).strip()
						if dest.upper() in ('DIRECT', 'NONE', ''):
							return None
						return dest
		except Exception as e:
			logger.warning(f"Failed to parse CHECKIN_PROXY_OVERRIDES: {e}")

	server = os.getenv('CHECKIN_PROXY_URL', '').strip()
	if server:
		return server

	pool = get_proxy_pool()
	return pool[0] if pool else None


def get_playwright_proxy(*, use_proxy: bool = True, url: Optional[str] = None) -> dict[str, str] | None:
	server = get_proxy_server(use_proxy=use_proxy, url=url)
	if not server:
		return None
	return {'server': server}
