import pytest
from unittest.mock import AsyncMock, patch
from panel import turnstile_solver
from panel import browser_login


@pytest.mark.asyncio
async def test_solver_no_keys(monkeypatch):
    monkeypatch.delenv('CAPSOLVER_API_KEY', raising=False)
    monkeypatch.delenv('CAPSOLVER_KEY', raising=False)
    monkeypatch.delenv('YESCAPTCHA_CLIENT_KEY', raising=False)
    monkeypatch.delenv('YESCAPTCHA_KEY', raising=False)

    res = await turnstile_solver.solve_turnstile('https://example.com', '0x4AAA')
    assert res is None


@pytest.mark.asyncio
async def test_capsolver_immediate_success(monkeypatch):
    monkeypatch.setenv('CAPSOLVER_API_KEY', 'test_key')
    monkeypatch.delenv('YESCAPTCHA_CLIENT_KEY', raising=False)

    class MockResp:
        status_code = 200
        def json(self):
            return {
                'errorId': 0,
                'status': 'ready',
                'solution': {'token': 'capsolver_token_123'},
            }

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MockResp()
        token = await turnstile_solver.solve_turnstile('https://example.com', '0x4AAA')
        assert token == 'capsolver_token_123'
        assert mock_post.call_count == 1


@pytest.mark.asyncio
async def test_capsolver_polling_success(monkeypatch):
    monkeypatch.setenv('CAPSOLVER_API_KEY', 'test_key')
    monkeypatch.delenv('YESCAPTCHA_CLIENT_KEY', raising=False)

    create_resp = MockResp = type('MockResp', (), {
        'status_code': 200,
        'json': lambda self: {'errorId': 0, 'status': 'processing', 'taskId': 'task_abc'}
    })()

    poll_resp = type('MockResp', (), {
        'status_code': 200,
        'json': lambda self: {'errorId': 0, 'status': 'ready', 'solution': {'token': 'polled_token_456'}}
    })()

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [create_resp, poll_resp]
        with patch('asyncio.sleep', new_callable=AsyncMock):
            token = await turnstile_solver.solve_turnstile('https://example.com', '0x4AAA')
            assert token == 'polled_token_456'
            assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_yescaptcha_fallback(monkeypatch):
    monkeypatch.setenv('CAPSOLVER_API_KEY', 'cap_key')
    monkeypatch.setenv('YESCAPTCHA_CLIENT_KEY', 'yes_key')

    # CapSolver fails
    cap_fail = type('MockResp', (), {
        'status_code': 200,
        'json': lambda self: {'errorId': 1, 'errorCode': 'ERROR_BALANCE', 'errorDescription': 'No money'}
    })()

    # YesCaptcha succeeds
    yes_ok = type('MockResp', (), {
        'status_code': 200,
        'json': lambda self: {'errorId': 0, 'status': 'ready', 'solution': {'token': 'yescaptcha_token_789'}}
    })()

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [cap_fail, yes_ok]
        token = await turnstile_solver.solve_turnstile('https://example.com', '0x4AAA')
        assert token == 'yescaptcha_token_789'


@pytest.mark.asyncio
async def test_mint_turnstile_fast_path(monkeypatch):
    with patch('panel.turnstile_solver.solve_turnstile', new_callable=AsyncMock) as mock_solve:
        mock_solve.return_value = 'mock_solved_token'
        # launch_login_context should NOT be called
        with patch('panel.browser_login.launch_login_context', new_callable=AsyncMock) as mock_launch:
            token = await browser_login.mint_turnstile(
                base_url='https://example.com',
                provider='github',
                account_name='test',
                sitekey='0x4AAA'
            )
            assert token == 'mock_solved_token'
            mock_launch.assert_not_called()
