"""Turnstile Solver: CapSolver and YesCaptcha integrations.

Solves Cloudflare Turnstile without launching local headless browsers,
saving substantial CPU/RAM on low-power NAS devices and achieving
instant, reliable token minting.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Optional
import httpx

from panel.vendor.utils.debug import is_debug_enabled, debug_print


def get_capsolver_key() -> Optional[str]:
	return os.getenv('CAPSOLVER_API_KEY') or os.getenv('CAPSOLVER_KEY') or None


def get_yescaptcha_key() -> Optional[str]:
	return os.getenv('YESCAPTCHA_CLIENT_KEY') or os.getenv('YESCAPTCHA_KEY') or None


def get_solver_provider() -> str:
	return os.getenv('TURNSTILE_SOLVER_PROVIDER', 'auto').strip().lower()


async def solve_capsolver(
	website_url: str,
	sitekey: str,
	api_key: str,
	*,
	base_url: str = 'https://api.capsolver.com',
	timeout_s: float = 45.0,
	poll_interval_s: float = 1.5,
) -> Optional[str]:
	"""Solve Cloudflare Turnstile using CapSolver API."""
	create_payload = {
		'clientKey': api_key,
		'task': {
			'type': 'AntiTurnstileTaskProxyLess',
			'websiteURL': website_url,
			'websiteKey': sitekey,
		},
	}
	start = time.monotonic()
	try:
		async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
			resp = await client.post(f'{base_url.rstrip("/")}/createTask', json=create_payload)
			if resp.status_code != 200:
				print(f'[WARN] CapSolver createTask HTTP {resp.status_code}: {resp.text[:200]}')
				return None
			data = resp.json()
			if data.get('errorId', 0) != 0:
				print(f'[WARN] CapSolver createTask error: {data.get("errorCode")} - {data.get("errorDescription")}')
				return None

			if data.get('status') == 'ready' and data.get('solution', {}).get('token'):
				cost_s = time.monotonic() - start
				print(f'[INFO] CapSolver solved Turnstile immediately in {cost_s:.1f}s')
				return data['solution']['token']

			task_id = data.get('taskId')
			if not task_id:
				print('[WARN] CapSolver did not return taskId')
				return None

			poll_payload = {'clientKey': api_key, 'taskId': task_id}
			while time.monotonic() - start < timeout_s:
				await asyncio.sleep(poll_interval_s)
				poll_resp = await client.post(f'{base_url.rstrip("/")}/getTaskResult', json=poll_payload)
				if poll_resp.status_code != 200:
					continue
				res = poll_resp.json()
				if res.get('errorId', 0) != 0:
					print(f'[WARN] CapSolver poll error: {res.get("errorCode")} - {res.get("errorDescription")}')
					return None
				if res.get('status') == 'ready':
					token = res.get('solution', {}).get('token')
					if token:
						cost_s = time.monotonic() - start
						print(f'[INFO] CapSolver solved Turnstile in {cost_s:.1f}s')
						return token
					return None
	except Exception as e:
		print(f'[WARN] CapSolver request exception: {type(e).__name__} ({e})')
		return None

	print(f'[WARN] CapSolver Turnstile solve timed out after {timeout_s}s')
	return None


async def solve_yescaptcha(
	website_url: str,
	sitekey: str,
	client_key: str,
	*,
	base_url: Optional[str] = None,
	timeout_s: float = 45.0,
	poll_interval_s: float = 1.5,
) -> Optional[str]:
	"""Solve Cloudflare Turnstile using YesCaptcha API."""
	endpoint = base_url or os.getenv('YESCAPTCHA_BASE_URL') or 'https://api.yescaptcha.com'
	create_payload = {
		'clientKey': client_key,
		'task': {
			'type': 'TurnstileTaskProxyless',
			'websiteURL': website_url,
			'websiteKey': sitekey,
		},
	}
	start = time.monotonic()
	try:
		async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
			resp = await client.post(f'{endpoint.rstrip("/")}/createTask', json=create_payload)
			if resp.status_code != 200:
				print(f'[WARN] YesCaptcha createTask HTTP {resp.status_code}: {resp.text[:200]}')
				return None
			data = resp.json()
			if data.get('errorId', 0) != 0:
				print(f'[WARN] YesCaptcha createTask error: {data.get("errorCode")} - {data.get("errorDescription")}')
				return None

			if data.get('status') == 'ready' and data.get('solution', {}).get('token'):
				cost_s = time.monotonic() - start
				print(f'[INFO] YesCaptcha solved Turnstile immediately in {cost_s:.1f}s')
				return data['solution']['token']

			task_id = data.get('taskId')
			if not task_id:
				print('[WARN] YesCaptcha did not return taskId')
				return None

			poll_payload = {'clientKey': client_key, 'taskId': task_id}
			while time.monotonic() - start < timeout_s:
				await asyncio.sleep(poll_interval_s)
				poll_resp = await client.post(f'{endpoint.rstrip("/")}/getTaskResult', json=poll_payload)
				if poll_resp.status_code != 200:
					continue
				res = poll_resp.json()
				if res.get('errorId', 0) != 0:
					print(f'[WARN] YesCaptcha poll error: {res.get("errorCode")} - {res.get("errorDescription")}')
					return None
				if res.get('status') == 'ready':
					token = res.get('solution', {}).get('token')
					if token:
						cost_s = time.monotonic() - start
						print(f'[INFO] YesCaptcha solved Turnstile in {cost_s:.1f}s')
						return token
					return None
	except Exception as e:
		print(f'[WARN] YesCaptcha request exception: {type(e).__name__} ({e})')
		return None

	print(f'[WARN] YesCaptcha Turnstile solve timed out after {timeout_s}s')
	return None


async def solve_turnstile(website_url: str, sitekey: str) -> Optional[str]:
	"""Attempts to solve Cloudflare Turnstile using configured third-party solver.
	Returns token if successful, or None to fall back to browser-based minting.
	"""
	capsolver_key = get_capsolver_key()
	yescaptcha_key = get_yescaptcha_key()

	if not capsolver_key and not yescaptcha_key:
		return None

	provider = get_solver_provider()

	# If provider is explicitly specified
	if provider == 'capsolver' and capsolver_key:
		return await solve_capsolver(website_url, sitekey, capsolver_key)
	if provider == 'yescaptcha' and yescaptcha_key:
		return await solve_yescaptcha(website_url, sitekey, yescaptcha_key)

	# Auto mode: try CapSolver first if key exists, then YesCaptcha if failed
	if capsolver_key:
		token = await solve_capsolver(website_url, sitekey, capsolver_key)
		if token:
			return token
		if yescaptcha_key:
			print('[INFO] CapSolver failed, falling back to YesCaptcha...')
			return await solve_yescaptcha(website_url, sitekey, yescaptcha_key)

	if yescaptcha_key:
		return await solve_yescaptcha(website_url, sitekey, yescaptcha_key)

	return None
