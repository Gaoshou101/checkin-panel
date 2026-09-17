# Check-in Panel (Docker Edition)

> This repository is a customized and optimized fork of [BingLi37/checkin-panel](https://github.com/BingLi37/checkin-panel), focused on **Docker containerization and headless NAS / server deployment**.
> 
> **Key Enhancements & Contributions:**
> 1. **Built-in Headless Chromium**: Pre-downloads the verified Chromium engine into `/opt/cloakbrowser` at build time. Starts up in seconds without runtime browser downloads, safe against host bind-mount masking;
> 2. **Full-chain SOCKS5 & HTTP Proxy**: Added `socksio` and integrated full support for `socks5://`, `socks5h://`, and `http://` proxies across both HTTP clients and headless browser sessions;
> 3. **Chromium Singleton Lock Auto-recovery**: Solves `ProcessSingleton: File exists` crashes after abnormal container termination by automatically removing dangling `SingletonLock` / `SingletonSocket` files;
> 4. **WAF & Cloudflare Challenge Optimization**: Proven stability when routing through local Clash / Mihomo proxies to pass Alibaba Cloud ESA WAF and Cloudflare Managed Challenges;
> 5. **Clean Streamlined Codebase**: Stripped out Windows desktop GUI and bulky tray dependencies; defaults to `PANEL_PROMO=0` clean mode with zero external promo polling.

[![Docker Hub](https://img.shields.io/badge/Docker_Hub-wit7zz%2Fcheckin--panel-blue?style=flat-square&logo=docker&logoColor=white)](https://hub.docker.com/r/wit7zz/checkin-panel)
[![GHCR](https://img.shields.io/badge/GHCR-gaoshou101%2Fcheckin--panel-2563eb?style=flat-square&logo=github&logoColor=white)](https://github.com/Gaoshou101/checkin-panel/pkgs/container/checkin-panel)
[![CI/CD Build](https://github.com/Gaoshou101/checkin-panel/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/Gaoshou101/checkin-panel/actions/workflows/docker-publish.yml)
[![License MIT](https://img.shields.io/badge/License-MIT-16a34a?style=flat-square)](LICENSE)
[![Python 3.14](https://img.shields.io/badge/Python-3.14+-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![agentrouter.org referral](https://img.shields.io/badge/agentrouter.org-Referral-f59e0b?style=flat-square)](https://agentrouter.org/register?aff=fQnR)
[![anyrouter.top referral](https://img.shields.io/badge/anyrouter.top-Referral-0284c7?style=flat-square)](https://anyrouter.top/register?aff=4w7X)

[简体中文](README.md) · **English**

> The badges above include referral links for `agentrouter.org` and `anyrouter.top` — registering through them supports the maintenance of this project. If you prefer not to use referral links, feel free to register directly on the respective sites.

A self-hosted panel that collects the daily bonus from New API style relay sites. Add your accounts, watch balances, let it claim daily — on one machine, without third-party services.

HTTP-first check-ins: launches a browser only when a site genuinely blocks protocols (OAuth session expiration, Turnstile, WAF). Most runs are fast, lightweight HTTP requests.

![Panel UI: account list showing sites, login method, success status, balance and last run time](docs/images/panel.png)

## Security Notice (Read First)

**The panel has no built-in authentication layer.** Anyone who can reach its port can retrieve **stored passwords and sessions in the clear** from `GET /api/accounts` (ADR-0003: single-user private panel design).

- **LAN / Home NAS**: Keep it within your private subnet; access via LAN IP or WireGuard / Tailscale;
- **Public VPS**: **Never expose port 8000 directly to the internet**. Put Nginx / Caddy with Basic Auth or OAuth in front with TLS, as detailed in [`docs/deploying.md`](docs/deploying.md).
- `data/panel.db` is the sole database file. Backing up this single file preserves all your accounts.

---

## Quick Start (Docker Recommended)

### Option 1: Docker Compose (Recommended)

Create `docker-compose.yml` on your NAS or Linux server:

```yaml
services:
  checkin-panel:
    # Docker Hub image (GHCR alternative: ghcr.io/gaoshou101/checkin-panel:latest)
    image: wit7zz/checkin-panel:latest
    container_name: checkin-panel
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      # Timezone (ensures claim windows align with local site schedules)
      TZ: Asia/Shanghai
      # Outbound proxy (for Cloudflare & WAF bypass; supports http://, socks5://, socks5h://)
      CHECKIN_PROXY_URL: http://host.docker.internal:7890
      # Scheduler: 1 to enable daily automatic check-ins, 0 for manual only
      PANEL_SCHEDULER: "1"
      # Clean mode: 0 disables external promo cards and outbound polling
      PANEL_PROMO: "0"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      # 1. Accounts database persistence (panel.db)
      - ./data:/app/data
      # 2. Browser session profile persistence
      - ./profiles:/app/.browser_profiles
```

Start the container:
```bash
docker compose up -d && docker compose logs -f
```
Open `http://<YOUR_SERVER_IP>:8000` in your browser!

### Option 2: Docker CLI

```bash
docker run -d \
  --name checkin-panel \
  --restart unless-stopped \
  -p 8000:8000 \
  -e TZ=Asia/Shanghai \
  -e PANEL_SCHEDULER=1 \
  -e PANEL_PROMO=0 \
  -e CHECKIN_PROXY_URL="http://192.168.10.30:7890" \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/profiles:/app/.browser_profiles \
  wit7zz/checkin-panel:latest
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TZ` | `Asia/Shanghai` | Timezone for accurate daily window calculation |
| `CHECKIN_PROXY_URL` | `http://127.0.0.1:7897` | Outbound proxy (`http://`, `socks5://`, `socks5h://`) |
| `CHECKIN_PROXY_OVERRIDES` | (empty) | Per-domain proxy overrides (JSON), e.g. `'{"anyrouter.top": "http://192.168.10.30:7890", "direct.com": "DIRECT"}'` |
| `PANEL_SCHEDULER` | `1` | Daily scheduler: `1` runs automatic loop every 30m, `0` disables |
| `PANEL_PROMO` | `0` | Promo cards: `0` for clean mode, `1` to poll remote promos |
| `PANEL_HOST` | `0.0.0.0` | Listen address inside container |
| `PANEL_PORT` | `8000` | Listen port inside container |

### Option 3: Local Python Run (Development)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py

# To run unit tests:
pip install -r requirements-dev.txt
pytest panel/tests
```

---

## Automated Docker Hub Publishing via GitHub Actions

This repository includes a GitHub Actions workflow (`.github/workflows/docker-publish.yml`):
- **Default Publishing**: Automatically builds and pushes to GitHub Container Registry (`ghcr.io`) upon pushes to `main` or `v*` tags;
- **Docker Hub Sync**: Add these secrets in your repository `Settings` -> `Secrets and variables` -> `Actions`:
  - `DOCKERHUB_USERNAME`: Your Docker Hub username (e.g. `gaoshou101`)
  - `DOCKERHUB_TOKEN`: Your Docker Hub Access Token
  Once configured, images will automatically push to `wit7zz/checkin-panel:latest`!

---

## Doing a browser login on a server

This is the one thing that gets stuck after deploying to a server, so it gets its own section.

The panel's daily automatic check-in uses a **headless** browser, which is no problem on a
server. But the **浏览器登录** (Browser login) button in the UI opens a **visible window** by
default — and that window opens on the machine running the panel, i.e. the server, where you
cannot see it. Inside a container it is more absolute: the image has no X display at all.

The good news: **a human is needed once, at first authorisation**, and only for one kind of
account.

### First work out whether you actually need it

| The account | Human needed? |
|---|---|
| a site where you can set a password | **No.** When the session expires the headless browser logs in again with the password |
| OAuth-only, but check-in is a POST to a route (`endpoint`) | **No browser.** Paste the site's access token if it offers one, otherwise its session — see Option A |
| OAuth-only, and the bonus comes from logging in again or loading a page (`login_bonus` / `visit`) | Yes, but only when the IdP session dies — typically once every few weeks to months |
| the site's API sits behind a WAF (anyrouter.top) | Yes, and **every day** — only a real browser passes that JS challenge, and no pasted credential helps |

An access token is a property of **the account**, not of the login method: even on a site that
only lets you in through GitHub or LinuxDO, you can generate a token on your profile page once
you are in. So most accounts in the second row can skip the browser as well — it is worth
looking for that option on the site's own profile page first.

**Hence the first piece of advice: set a password wherever you can.** That is not a workaround,
it removes the problem — a password account never touches a browser for its daily check-in. When
you add an account, the panel points this out if the site allows a password.

For sites where a password is impossible, the options below run easiest-first: Option A covers
most of them, B is for what A cannot reach. anyrouter.top (a WAF plus the `visit` mechanism, so
a browser every single time) starts at B.

### Option A: paste the site's own credential (the most direct)

No window on the server, no X, and the panel opens no browser. What moves is **a credential the
site issued to you**, and the upstream provider (GitHub / LinuxDO / Google) is not involved at
all — how you originally logged in does not matter on this path.

Sites issue two kinds. Use the first if you can.

**Preferred: an access token.** Most New API sites have "访问令牌 / Access Token" on the profile
page (measured here on `api.hcnsec.cn`: `/profile` → 访问令牌 → 生成). It is a plain string you
copy from the site's own UI, it needs **no browser extension**, and it does not expire in a month
the way a cookie does. Pick **Access Token** as the **登录方式** (Login method) and paste it —
the panel sends it as the `Authorization` header, which the site's `/api/user/self` and its
check-in route both accept.

**Fallback: the session cookie.** Only when the site offers no access token.

1. Open **the check-in site itself** in your own browser and log in.
2. Take the **value** of the `session` cookie. It is usually **HttpOnly** (measured on
   `api.hcnsec.cn`: `HttpOnly; SameSite=Strict; Max-Age=2592000`), so page JS cannot read it;
   the reliable route is the browser's own **DevTools → Application → Cookies → the site →
   `session` → copy Value**. A cookie extension can read HttpOnly too, but check that it has
   permission on that site and that you are standing **on the site's own page** — standing on
   the panel (`127.0.0.1:8000`) shows "This page does not have any cookies", because the panel
   issues none of its own.
3. In the panel → **登录方式** (Login method) → **会话 Cookie** (Session cookie) → paste into
   the session field → save.

The session field takes either a single value or the whole JSON blob a cookie extension exports.
Paste the whole thing; the panel picks the one it needs: `session` on an ordinary site,
`new_api_refresh` on a JWT site such as seekai.cc. Which one it picks is decided by **the probe
result**, not by what you pasted. Both kinds of paste are verified the moment you save, so you
find out immediately.

One more case worth knowing in advance: the cookie is good, but the site also wants the account's
own user id (the `new-api-user` header), and without it every endpoint answers 401. The panel
recognises this one and says so — "the credential is fine, but this site also wants the account's
user id" — instead of reporting a dead credential. Put that value in **API User（可选）**
(API User, optional) in the dialog: on the site's page press F12 → Network, pick any API request
the site made itself, and the `New-Api-User` request header is the value (`user.id` in
localStorage is the same number).

![DevTools Network panel: a sign_in request the site made itself, with a New-Api-User row among its request headers](docs/images/api-user.png)

Two limits, which the UI also states:

- **The panel cannot renew a session cookie.** When it expires you paste again (measured: 30 days
  on `api.hcnsec.cn`). An access token does not have this problem, an account with a password
  re-logs in by itself, and an OAuth-only account should use Option B, which lasts weeks to
  months per paste.
- **It only covers `endpoint` sites.** `login_bonus` grants the bonus by logging in again (the
  protocol itself needs the password) and `visit` needs a page genuinely loaded while logged in
  (anyrouter.top). Neither is something a cookie or a token can stand in for.

Worth saying: if the site still offers password login and does not gate it behind Turnstile
(`api.hcnsec.cn` is exactly this), you do not need to paste anything — fill in the username and
password, and the panel runs the whole thing over plain HTTP with a credential that never
expires. Try that first.

### Option B: an OAuth-only identity — inject the IdP session

The site only offers GitHub / LinuxDO login and a password is simply not possible (ADR-0009),
and the site session from Option A has expired. Now you move **the upstream layer**, after which
the panel trades it for a fresh site session every day on its own. The point is to keep the two
layers apart:

| Which layer | Lives where | Lasts | Who fetches it |
|---|---|---|---|
| site session | `accounts.session` in the database | short, swapped daily | the panel (a headless OAuth round trip) |
| **IdP session** (linux.do / github.com) | the browser profile directory | weeks to months | **a human, once** |

1. Log in to LinuxDO or GitHub in your own browser.
2. Export with a cookie extension, **standing on the linux.do / github.com page**.

   ![The Cookie-Editor extension: the export button at the bottom right, format JSON](docs/images/cookie-editor.png)

3. Click **注入会话** (Inject session) on that account's row, paste the whole blob, save.

   ![The inject-session dialog: paste the exported JSON into the text box, with a "verify immediately after injecting" switch below it](docs/images/inject-session.png)

"注入后立刻验证一次" (verify immediately after injecting) is on by default: the panel runs one
headless authorisation there and then and tells you whether it worked, rather than letting you
find out tomorrow when the scheduled check-in fails. The three outcomes are "verified", "login
failed + reason" and "not verified" — only the first is evidence.

Three things to be clear about:

- **What you pasted is your entire forum or GitHub account**, not a credential for the check-in
  site. It is written into that account's browser profile and the panel does not copy it into the
  database — but the panel has no login of its own (ADR-0003), so anyone who can reach the panel
  can use that identity. Every line about `PANEL_HOST` and the published port matters *more*
  after this step, not less.

- When the session expires, export it again. The frequency is the same as Options C and D: weeks
  to months.
- The **first** headless round trip after an injection is the one link on this path that has not
  been measured: whether an injected session and one the browser logged in itself look equivalent
  to Cloudflare is not something this repository has evidence for. So leave that verification
  switch on, and if it does not work, Options C and D are still below.
- **Deleting the account offers to delete the profile too, and the default is to delete it.** The
  IdP session from the table above lives in that directory, so keeping it leaves a working forum
  or GitHub login on the disk while the account it belonged to is gone from the panel. If you do
  keep it, it turns up later under **清理 profile** (Clean up profiles) beside the page title —
  renamed accounts leave one there as well, because a profile directory is named after the
  account.

  ![The profile cleanup dialog: profiles no account claims, with the space each takes](docs/images/profile-cleanup.png)

### Option C: a temporary VNC in the container, and click the window yourself

The image **already has `Xvfb`** (`playwright install-deps` brings it along). What is missing is
only a bridge you can see it through.

Add an on-demand service to `docker-compose.yml`. Note that `profiles:` keeps it from starting by
default:

```yaml
services:
  panel:
    environment:
      DISPLAY: ":99"          # put the panel's browser on the virtual display

  vnc:
    profiles: ["vnc"]         # off by default, started only when you need to authorise
    image: anyrouter-checkin-panel
    container_name: checkin-vnc
    network_mode: "service:panel"
    volumes:
      - panel-profiles:/app/.browser_profiles
    user: root
    entrypoint: >
      sh -c "apt-get update && apt-get install -y --no-install-recommends x11vnc websockify novnc &&
             Xvfb :99 -screen 0 1280x800x24 &
             sleep 2 &&
             x11vnc -display :99 -forever -localhost -nopw &
             websockify --web=/usr/share/novnc 127.0.0.1:6080 127.0.0.1:5900"
```

To use it:

```bash
docker compose --profile vnc up -d vnc          # only when you need to authorise
ssh -L 6080:127.0.0.1:6080 you@your-server      # tunnel from your own machine
# open http://127.0.0.1:6080/vnc.html, then click 浏览器登录 in the panel
docker compose --profile vnc down               # shut it down once you are done
```

**Two requirements that do not bend:**

1. **The VNC port goes through an SSH tunnel or a private network, never onto the public
   internet.** That is what `x11vnc -localhost` and `websockify 127.0.0.1` above are for — a
   remote desktop with a logged-in IdP in it is worth more than the panel itself.
2. **Shut it down when you are done.** It is not meant to stay up.

One admission: I have not measured a headed Chromium actually starting under Xvfb (it wants the
500MB engine downloaded first). It is what Xvfb is for and it ought to work, but that is
inference rather than measurement, and your first run may need adjusting.

### Option D: SSH X11 forwarding

```bash
ssh -X you@your-server
# in the container: docker exec -e DISPLAY=$DISPLAY -it checkin-panel ...
```

The window opens on your own screen and nothing stays exposed on the server. The cost is an X
server on your machine (something like VcXsrv on Windows), and in the container case passing
`DISPLAY` and the X socket in as well — more fiddly than Option C.

### One road that does not work: copying the profile directory

**Do not plan on "authorise locally, then copy the whole profile directory to the server".** A
Windows profile's `Local State` holds `os_crypt.encrypted_key`, which is DPAPI-encrypted and
bound to the current Windows account, so on Linux the cookies cannot be decrypted.

**And that is exactly why Options A and B do work.** Keep the two apart:

| What you move | Works? | Why |
|---|---|---|
| the whole profile directory | no | the cookies inside are encrypted with a DPAPI key, and the key cannot travel |
| cookie **values** (the exported JSON) | yes | plain name/value pairs, re-encrypted by the receiving browser with its own key |

The `session` column in the database was always movable (it is just a string) — that is Option A.
A `visit` account's site session lives in the profile, but the headless round trip fetches it
fresh every day, so what you move for that kind of account is the IdP session one layer up.

## Environment variables

All optional.

| Variable | Default | What it does |
|---|---|---|
| `PANEL_HOST` | `run.py`: `0.0.0.0` / desktop: `127.0.0.1` | bind address. **This is the trust boundary** |
| `PANEL_PORT` | `8000` | port |
| `PANEL_SCHEDULER` | on | `0` turns off the daily automatic check-in |
| `PANEL_PROMO` | on | `0` turns off the promo card; nothing is fetched |
| `CHECKIN_PROXY_URL` | `http://127.0.0.1:7897` | browser login only. Inside a container, a proxy on the host is `http://host.docker.internal:7897` |
| `TZ` | system | must be right inside a container, see above |

## Development

```bat
.venv\Scripts\python.exe -m pytest              :: 285 tests
cd frontend && npm run dev                       :: frontend hot reload, :5173 proxies to :8000
```

After forking, install this hook first. It stops credential-shaped strings and database files at
`git commit`:

```bat
.venv\Scripts\python.exe scripts\check_secrets.py --install
.venv\Scripts\python.exe scripts\check_secrets.py --all   :: or scan the whole tree by hand
```

It matches only shapes with a fixed prefix that have no innocent meaning (`ghp_`, `sk-`, `AKIA`,
private key headers), so a hit is a hit. It does not do entropy or `password=` heuristics, because
in this repository those produced nothing but false positives — and a check that cries wolf gets
bypassed with `--no-verify`, which is worse than no check. It never prints the value it matched.

Changing the frontend needs no panel restart; changing `panel/` does.

`panel/` must stay OS-neutral, because it is imported inside the Linux container — every
Windows-only line lives in `desktop/` at the repository root. That is why the 285 tests in
`panel/tests/` have to be runnable in the container; the desktop shell's own tests are not here,
they are kept with the development tree.

The comment density in the code is high on purpose: next to every non-obvious decision is why it
looks that way, not just what it does. A marker like `ADR-0007` in a comment points at a decision
record in the development tree, and those files are not in this repository — read it as "there is
a non-obvious trade-off here, and the reason is the comment beside it". The comments stand on
their own.

## What it does not do

- **No panel, no check-in.** There is no external scheduler and no server-side component
  (ADR-0008), which is also why the choice of run mode matters.
- **No dry run.** Pressing 签到 (Check in) in the UI performs the real thing (ADR-0005).
- **No encryption at rest.** In all three modes the trust boundary is the host itself.
- **No telemetry.** The panel makes exactly one outbound request of its own: the promo card
  manifest, which carries nothing about you, and `PANEL_PROMO=0` turns it off entirely
  ([`docs/promo-cards.md`](docs/promo-cards.md)). The browser engine download is made by
  cloakbrowser itself — see [`THIRD-PARTY.md`](THIRD-PARTY.md).

## Licence

MIT, see [`LICENSE`](LICENSE).

Third-party licences and the obligations that come with them are in
[`THIRD-PARTY.md`](THIRD-PARTY.md). One is worth noting: `pystray`, which draws the tray icon, is
**LGPLv3** and is compiled into the desktop executable. That does not require your code to be
closed or open — this project is open anyway — but distributing the zip means keeping that notice
with it.

There is no GitHub Actions check-in workflow in this repository. The panel schedules itself
(ADR-0008), so a fork needs none of those secrets.

This project is not affiliated with any of the sites it checks into. Their terms of service are
yours to follow.

