#!/usr/bin/env python3
"""代理健康与分流探测工具。

测试代理池中所有节点对目标站点的连通性、响应延迟及 HTTP 状态码，
输出测速矩阵并自动推荐最佳分流配置 (CHECKIN_PROXY_OVERRIDES)。

用法：
    python scripts/probe_proxies.py
    python scripts/probe_proxies.py --json
"""

import argparse
import json
import os
import subprocess
import sys
import time
from urllib.parse import urlparse

# 默认待测站点列表
DEFAULT_TARGET_SITES = [
    ('anyrouter.top', 'https://anyrouter.top/login'),
    ('kktoken.cc', 'https://kktoken.cc/login'),
    ('tabitoken.com', 'https://tabitoken.com/login'),
    ('agentrouter.org', 'https://agentrouter.org/login'),
    ('api.justwoker.icu', 'https://api.justwoker.icu/login'),
]

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
)


def get_all_proxies() -> list[str]:
    raw_pool = os.getenv('CHECKIN_PROXY_POOL', '').strip()
    proxies = []
    if raw_pool:
        if raw_pool.startswith('[') and raw_pool.endswith(']'):
            try:
                parsed = json.loads(raw_pool)
                if isinstance(parsed, list):
                    proxies.extend([str(p).strip() for p in parsed if str(p).strip()])
            except Exception:
                pass
        if not proxies:
            for item in raw_pool.replace('
', ';').replace(',', ';').split(';'):
                p = item.strip()
                if p and p not in proxies:
                    proxies.append(p)
    default_p = os.getenv('CHECKIN_PROXY_URL', '').strip()
    if default_p and default_p not in proxies:
        proxies.append(default_p)
    return proxies


def probe_one(proxy: str, target_url: str, timeout: int = 6) -> dict:
    t0 = time.time()
    cmd = [
        'curl', '-s', '-I', '--max-time', str(timeout),
        '-A', USER_AGENT,
        '-x', proxy,
        target_url
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 1)
        dur = int((time.time() - t0) * 1000)
        lines = proc.stdout.strip().split('
')
        status_line = lines[0] if lines else ''
        status_code = None
        for part in status_line.split():
            if part.isdigit() and len(part) == 3:
                status_code = int(part)
                break
        return {
            'ok': status_code in (200, 301, 302, 307, 308),
            'status': status_code or 'ERR',
            'latency_ms': dur,
            'error': None if status_code else 'No status line'
        }
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        return {
            'ok': False,
            'status': 'TIMEOUT' if 'timed out' in str(e).lower() else 'FAIL',
            'latency_ms': dur,
            'error': str(e)
        }


def main():
    parser = argparse.ArgumentParser(description='Checkin-panel 代理池探测矩阵')
    parser.add_argument('--json', action='store_true', help='以 JSON 格式输出')
    args = parser.parse_args()

    proxies = get_all_proxies()
    if not proxies:
        print('[WARN] 未找到代理配置！请设置 CHECKIN_PROXY_POOL 或 CHECKIN_PROXY_URL 环境变量。')
        sys.exit(1)

    print(f'=== 发现 {len(proxies)} 个候选代理节点，开始对 {len(DEFAULT_TARGET_SITES)} 个站点进行矩阵探测 ===
')
    
    matrix = {}
    recommendations = {}

    for domain, target_url in DEFAULT_TARGET_SITES:
        matrix[domain] = {}
        best_proxy = None
        best_latency = 999999

        for p in proxies:
            res = probe_one(p, target_url)
            matrix[domain][p] = res
            if res['ok'] and res['latency_ms'] < best_latency:
                best_latency = res['latency_ms']
                best_proxy = p

        if best_proxy:
            recommendations[domain] = best_proxy

    if args.json:
        print(json.dumps({'matrix': matrix, 'recommendations': recommendations}, indent=2, ensure_ascii=False))
        return

    # 表格化展示
    header = f"{'站点域名':<20} | " + ' | '.join([f'节点 {i+1}':<12} for i in range(len(proxies))])
    print(header)
    print('-' * len(header))
    for domain, _ in DEFAULT_TARGET_SITES:
        row = [f'{domain:<20}']
        for p in proxies:
            r = matrix[domain].get(p, {})
            status = r.get('status', 'FAIL')
            lat = r.get('latency_ms', 0)
            mark = f"{status} ({lat}ms)"
            row.append(f"{mark:<12}")
        print(' | '.join(row))

    print('
=== 自动生成的推荐分流配置 (CHECKIN_PROXY_OVERRIDES) ===')
    print(json.dumps(recommendations, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
