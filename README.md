# 自动签到面板 (Docker 专版)

> 本仓库是 [BingLi37/checkin-panel](https://github.com/BingLi37/checkin-panel) 的定制优化 Fork 分支，专注于 **Docker 容器化与 NAS / 服务器无人值守部署**。
> 
> **主要优化与贡献：**
> 1. **内置自动化 Chromium 内核**：镜像直接预置经检验的无头浏览器内核（`/opt/cloakbrowser`），开箱秒起，无需首次启动在线下载 500MB，更不会因宿主机目录挂载遮挡文件；
> 2. **全链路 SOCKS5 / HTTP 代理穿透**：引入 `socksio` 并在 HTTP 客户端与无头浏览器间全面打通 `socks5://`、`socks5h://` 与 `http://` 代理协议，无缝适配各类旁路由 Clash / 远程代理网关；
> 3. **Chromium 孤儿锁自愈机制**：修复容器异常退出/强制重启后遗留 `SingletonLock`、`SingletonSocket` 导致 Playwright 报错 `ProcessSingleton: File exists` 崩溃的问题，启动前自动清理残留文件锁；
> 4. **WAF 与 Cloudflare 挑战调优**：支持通过局域网 Clash / Mihomo HTTP 代理稳定通过 Alibaba Cloud ESA WAF 与 Cloudflare Managed Challenge；
> 5. **剥离桌面遗留与纯净模式**：彻底移除 Windows GUI / 托盘代码与相关庞大依赖，默认开启 `PANEL_PROMO=0` 纯净模式，不向外部公共仓库轮询卡片，轻巧专注。

[![Docker Hub](https://img.shields.io/badge/Docker_Hub-wit7zz%2Fcheckin--panel-blue?style=flat-square&logo=docker&logoColor=white)](https://hub.docker.com/r/wit7zz/checkin-panel)
[![GHCR](https://img.shields.io/badge/GHCR-gaoshou101%2Fcheckin--panel-2563eb?style=flat-square&logo=github&logoColor=white)](https://github.com/Gaoshou101/checkin-panel/pkgs/container/checkin-panel)
[![CI/CD Build](https://github.com/Gaoshou101/checkin-panel/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/Gaoshou101/checkin-panel/actions/workflows/docker-publish.yml)
[![许可 MIT](https://img.shields.io/badge/许可-MIT-16a34a?style=flat-square)](LICENSE)
[![Python 3.14](https://img.shields.io/badge/Python-3.14+-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![agentrouter.org 邀请注册](https://img.shields.io/badge/agentrouter.org-邀请注册-f59e0b?style=flat-square)](https://agentrouter.org/register?aff=fQnR)
[![anyrouter.top 邀请注册](https://img.shields.io/badge/anyrouter.top-邀请注册-0284c7?style=flat-square)](https://anyrouter.top/register?aff=4w7X)

**简体中文** · [English](README.en.md)

> 上方的徽章包含 `agentrouter.org` 与 `anyrouter.top` 的**邀请注册链接**，点它注册是支持维护本项目的方式。如果不想走邀请，直接访问对应站点首页注册也可正常使用面板。

给 New API 类型的中转站做每日签到的自建面板。加账号、看余额、每天自动领，一台机器上跑，不依赖任何外部服务。

优先走 HTTP 协议签到，只有站点确实拦得住协议（OAuth 会话过期、Turnstile、WAF）才启动浏览器 —— 所以绝大多数账号的日常签到只是几个极速 HTTP 请求，轻快省资源。

![面板主界面：账号列表，每行一个账号，显示站点、登录方式、今天签到成功没有、余额和最近一次运行时间](docs/images/panel.png)

## 安全须知（部署前必看）

**面板本身不带访问鉴权层。** 任何能直接访问到它端口的客户端，都能从 `GET /api/accounts` 获取到**已存账号的密码与 session**（ADR-0003：定位为单用户自用私有面板）。

- **局域网/家庭 NAS**：建议部署在内网网段，通过局域网 IP 或 Tailscale / WireGuard 私网访问；
- **公网 VPS**：**切勿直接把 8000 端口暴露给公网**。请务必前置 Nginx / Caddy 配合 Basic Auth 或 OAuth 进行反向代理与 TLS 加密保护，详见 [`docs/deploying.md`](docs/deploying.md)。
- `data/panel.db` 是账号和记录的唯一存储文件，备份此文件即可完整迁移数据。

---

## 快速开始（推荐 Docker 部署）

### 方式一：Docker Compose（推荐）

在你的 NAS（如飞牛 fnOS / 群晖 / 威联通 / Unraid）或 Linux 服务器上创建 `docker-compose.yml`：

```yaml
services:
  checkin-panel:
    # 优先使用 Docker Hub 镜像，备选支持 GHCR: ghcr.io/gaoshou101/checkin-panel:latest
    image: wit7zz/checkin-panel:latest
    container_name: checkin-panel
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      # 时区（确保签到刷新时间窗口准确）
      TZ: Asia/Shanghai
      # 出站代理（按需配置，用于穿透 Cloudflare 或阿里云 ESA WAF）
      # 支持 http://, socks5://, socks5h://
      # 示例指向局域网旁路由 Clash / 宿主机代理端口：
      CHECKIN_PROXY_URL: http://host.docker.internal:7890
      # 每日定时自动签到循环 (1 开启，0 仅在页面手动点击)
      PANEL_SCHEDULER: "1"
      # 纯净模式 (0 关闭第三方推荐卡片外联)
      PANEL_PROMO: "0"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      # 1. 账号数据卷（持久化存储 panel.db 数据库）
      - ./data:/app/data
      # 2. 会话状态卷（持久化存储 OAuth 与浏览器登录生成的 Profile）
      - ./profiles:/app/.browser_profiles
```

执行启动：
```bash
docker compose up -d && docker compose logs -f
```
浏览器访问 `http://<你的NAS或服务器IP>:8000` 即可使用！

### 方式二：Docker CLI 单行运行

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

### 环境变量完整参考

| 变量名 | 默认值 | 作用说明 |
|---|---|---|
| `TZ` | `Asia/Shanghai` | 容器时区，确保签到时间窗口按本地时间精准结算 |
| `CHECKIN_PROXY_URL` | `http://127.0.0.1:7897` | 全局出站代理（支持 `http://`, `socks5://`, `socks5h://`） |
| `CHECKIN_PROXY_OVERRIDES` | (空) | 按域名分流代理（JSON 格式），如 `'{"anyrouter.top": "http://192.168.10.30:7890", "direct.com": "DIRECT"}'` |
| `CHECKIN_PROXY_POOL` | (空) | 备用代理池（JSON 数组或分号分隔），未命中分流且默认代理为空时自动轮询 |
| `PANEL_SCHEDULER` | `1` | 定时签到开关：`1` 为每 30 分钟轮询窗口自动签到，`0` 为仅手动 |
| `PANEL_PROMO` | `0` | 推荐卡片：`0` 为纯净无外联模式，`1` 为拉取推荐卡片 |
| `PANEL_HOST` | `0.0.0.0` | 容器内监听地址 |
| `PANEL_PORT` | `8000` | 容器内监听端口 |

### 方式三：本地 Python 直接运行（开发模式）

```bash
# 1. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. 安装核心依赖
pip install -r requirements.txt

# 3. 运行面板
python run.py

# 4. 如需运行单元测试
pip install -r requirements-dev.txt
pytest panel/tests
```

---

## 自动构建推送至 Docker Hub 说明

本仓库已配置 GitHub Actions 自动构建工作流（`.github/workflows/docker-publish.yml`）：
- **默认推送**：每次推送代码至 `main` 分支或打 `v*` 标签时，自动推送到 GitHub Packages (`ghcr.io`)；
- **同步推送 Docker Hub**：在 GitHub 仓库 `Settings` -> `Secrets and variables` -> `Actions` 中添加以下两个 Secret：
  - `DOCKERHUB_USERNAME`: 你的 Docker Hub 用户名（如 `gaoshou101`）
  - `DOCKERHUB_TOKEN`: 你的 Docker Hub Access Token
  配置后，每次代码提交将自动推送到 `wit7zz/checkin-panel:latest`！

---

## 服务器上怎么做浏览器登录

这是部署到服务器后唯一会卡住的地方，单独讲。

面板日常自动签到走的是**无头**浏览器，服务器上本来就没问题。但界面上那个「浏览器登录」按钮默认
开一个**可见窗口** —— 窗口开在跑面板的那台机器上，也就是服务器，你看不见；容器里更彻底，镜像里
没有 X 显示服务。

好消息是：**人只在「首次授权」时被需要一次**，而且只对一类账号。

### 先判断你是否真的需要它

| 账号情况 | 需要人工吗 |
|---|---|
| 能设密码的站点 | **不需要。** 会话过期时无头浏览器自己用密码重登录 |
| OAuth-only，但签到是 POST 一个路由（`endpoint`） | **不需要浏览器。** 站点有访问令牌就粘令牌，没有就粘它的 session，见方案 A |
| OAuth-only，且靠重新登录或加载页面发额度（`login_bonus` / `visit`） | 需要，但只在 IdP 会话失效时，通常数周到数月一次 |
| 站点 API 被 WAF 挡住（anyrouter.top） | 需要，且**每天**都要 —— 只有真浏览器能过那道 JS 挑战，任何粘进来的凭据都没用 |

访问令牌是**账号自己的**属性，不是"登录方式"的属性：哪怕这个站只让你用 GitHub / LinuxDO 登，
登进去之后照样能在用户页生成一个令牌。所以第二行那种账号，多数也能靠令牌免掉浏览器 —— 值得先去
站点用户页看一眼有没有这个入口。

**所以第一条建议是：能绑密码的就绑密码。** 这不是绕过问题，是让问题不存在 —— 密码账号的日常
签到完全不碰浏览器。添加账号时如果站点允许设密码，面板会提示「能设密码就转成纯 HTTP」。

绑不了密码的站点走下面：方案 A 最省事，够不着的再看 B。anyrouter.top（WAF + `visit` 机制，
每次都要浏览器）只能走 B 往后。

### 方案 A：把站点自己的凭据粘过去（最直接）

服务器上不用开窗口、不用装 X，面板也不用开浏览器。搬的是**站点发给你的凭据**，上游那家（GitHub /
LinuxDO / 谷歌）一点都不用碰 —— 站点当初用什么方式登的，不影响这条路。

站点给的凭据有两种，能用第一种就别用第二种。

**首选：访问令牌。** 多数 New API 站点的用户页里有「访问令牌 / Access Token」（本仓库实测
`api.hcnsec.cn`：`/profile` → 访问令牌 → 生成）。它是明文一串，站点界面上直接复制，**不需要任何
浏览器扩展**，也不像 cookie 那样一个月就过期。面板里**登录方式**选「Access Token」粘进去即可 ——
面板把它作为 `Authorization` 头发出去，站点的 `/api/user/self` 和签到路由都认。

**退路：会话 Cookie。** 站点不提供访问令牌时才用这条。

1. 在自己电脑的浏览器里打开**这个签到站点**并登录。
2. 取出 `session` 这条 cookie 的**值**。它通常是 **HttpOnly** 的（实测 `api.hcnsec.cn`：
   `HttpOnly; SameSite=Strict; Max-Age=2592000`），所以页面 JS 读不到；用浏览器自带的
   **DevTools → Application → Cookies → 该站点 → `session` → 复制 Value** 最稳。
   cookie 扩展也能读 HttpOnly，但得先确认它在这个站点上有权限、且停在**站点自己的页面**上 ——
   停在面板上（`127.0.0.1:8000`）会显示 "This page does not have any cookies"，因为面板自己不发
   cookie。
3. 面板里 → **登录方式**选「会话 Cookie」→ 粘进会话栏 → 保存。

会话栏既收单独一个值，也收 cookie 扩展导出的整段 JSON；整段粘就行，面板自己挑出要用的那条：普通
站点是 `session`，JWT 站点（如 seekai.cc）是 `new_api_refresh`。挑哪条由**探测结果**决定，不是由
粘进来的内容决定。两种粘法保存时都立刻验证一次，成没成当场就知道。

还有一种情况值得先知道：cookie 是好的，但站点还要账号自己的用户 id（`new-api-user` 头），
不给它就每个接口都 401。面板认得出这一种，会直接说「凭据本身没问题，但这个站点还要账号的用户
id」，而不是笼统地报凭据无效。把这个值填进弹窗里的 **API User（可选）**：站点页面 F12 → 网络，
挑一个站点自己发出的 API 请求，请求头里的 `New-Api-User` 就是它（localStorage 里的 `user.id`
是同一个数）。

![DevTools 网络面板：站点自己发的 sign_in 请求，请求头里有 New-Api-User 一行](docs/images/api-user.png)

两个限制，界面上也会直接提示：

- **面板续不了会话 cookie。** 过期就得再粘一次（`api.hcnsec.cn` 实测 30 天）。访问令牌没这个问题，
  有密码的账号面板能自己重新登录，OAuth-only 的走方案 B 一次管数周到数月。
- **只够 `endpoint` 站点用。** `login_bonus` 靠重新登录发额度（协议层面就要密码），`visit` 要
  真的在登录状态下加载页面（anyrouter.top），这两种都不是一个 cookie 或令牌能替代的。

顺一句：这个站点如果还开着密码登录、又不要 Turnstile（`api.hcnsec.cn` 就是这样），那连粘都不用粘 ——
直接填账号密码，面板每天纯 HTTP 跑完，凭据永不过期。先试这个。

### 方案 B：OAuth-only 身份，把 IdP 会话注入进去

站点只有 GitHub / LinuxDO 登录、密码根本设不了（ADR-0009），而方案 A 那条站点会话过期了 ——
这时候搬**上游那一层**，搬完面板自己每天去换站点会话，不用再管。要点是分清两层：

| 哪一层 | 存在哪 | 活多久 | 谁去拿 |
|---|---|---|---|
| 站点会话 | 数据库 `accounts.session` | 短，每天自动换 | 面板自己（无头 OAuth 跳转） |
| **IdP 会话**（linux.do / github.com） | 浏览器 profile 目录 | 数周到数月 | **人，一次** |

1. 在自己电脑的浏览器里登录 LinuxDO 或 GitHub。
2. 用 cookie 扩展，**停在 linux.do / github.com 的页面上**导出。

   ![Cookie-Editor 扩展：右下角导出按钮，格式选 JSON](docs/images/cookie-editor.png)

3. 面板列表里点这个账号的**「注入会话」**，整段粘进去，保存。

   ![注入 GitHub 会话弹窗：把导出的整段 JSON 粘进文本框，下面是「注入后立刻验证一次」开关](docs/images/inject-session.png)

默认勾着「注入后立刻验证一次」：面板当场跑一次无头授权登录，成没成马上告诉你，而不是等到明天
定时签到失败才发现。三种结果分别是「验证通过」「登录没通过 + 原因」「未验证」——只有第一种算证据。

三点要清楚：

- **粘过去的是你整个论坛 / GitHub 账号**，不只是签到站点的凭据。它写进那个账号的浏览器 profile，
  面板不会存进数据库；但面板本身没有登录保护（ADR-0003），谁能访问面板就能用这个身份。
  所以 `PANEL_HOST` / 端口发布范围在这一步之后更要紧，不是更不要紧。
- 会话过期了就再导一次，频率和方案 C / D 一样，都是数周到数月。
- 注入后的**第一次**无头跳转是这条路上唯一没被实测过的环节：注入来的会话和浏览器自己登出来的
  会话，在 Cloudflare 眼里是否等价，仓库里没有证据。所以别关掉那个验证开关；万一不通，方案 C
  和 D 仍然在下面。
- **删账号时会问你要不要一起删掉这个 profile，默认删。** 上面那张表里 IdP 会话就住在这个目录里，
  所以留下它等于把一份还能用的论坛 / GitHub 登录留在硬盘上，而账号已经不在面板里了。选择留下的话，
  它之后会出现在标题旁边的**「清理 profile」**里 —— 改过名字的账号也会在那儿留一份，因为 profile
  是按名字建目录的。

  ![清理浏览器 profile 弹窗：列出没有账号认领的 profile 和它们占的空间](docs/images/profile-cleanup.png)

### 方案 C：容器里临时开一个 VNC，看着窗口点

镜像里**已经有 `Xvfb`**（`playwright install-deps` 顺带装的），缺的只是一个能看见它的桥。

在 `docker-compose.yml` 里加一个按需启动的服务。注意 `profiles:` 让它默认不启动：

```yaml
services:
  panel:
    environment:
      DISPLAY: ":99"          # 让面板的浏览器开在虚拟显示上

  vnc:
    profiles: ["vnc"]         # 默认不起，只在需要授权时起
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

用的时候：

```bash
docker compose --profile vnc up -d vnc          # 需要授权时才起
ssh -L 6080:127.0.0.1:6080 you@your-server      # 从本机开隧道
# 浏览器打开 http://127.0.0.1:6080/vnc.html，然后在面板里点「浏览器登录」
docker compose --profile vnc down               # 授权完就关掉
```

**两条不能松的要求：**

1. **VNC 端口只走 SSH 隧道或私有网络，绝不发布到公网。** 上面 `x11vnc -localhost` 和
   `websockify 127.0.0.1` 都是为此 —— 一个已登录 IdP 的远程桌面比面板本身更值钱。
2. **用完就关。** 它不该常驻。

坦白一句：我没有实测过有头 Chromium 在 Xvfb 下真能起来（要先下 500MB 内核）。这是 Xvfb 的本职
工作、按理可行，但这是推断不是测量结果，你第一次跑可能需要调整。

### 方案 D：SSH X11 转发

```bash
ssh -X you@your-server
# 容器里：docker exec -e DISPLAY=$DISPLAY -it checkin-panel ...
```

窗口直接开在你自己屏幕上，服务器上不留任何常驻暴露。代价是本机要有 X 服务器（Windows 上要装
VcXsrv 一类），容器场景还要把 `DISPLAY` 和 X socket 传进去，比方案 C 绕。

### 一条走不通的路：拷 profile 目录

**别想着「在本地授权好再把整个 profile 目录拷到服务器」。** Windows 的 profile 里
`Local State` 有 `os_crypt.encrypted_key`，那是 DPAPI 加密、绑当前 Windows 账户的，搬到 Linux
解不开 cookie。

**但这恰恰是方案 A / B 能成的原因**，两件事别混在一起：

| 搬什么 | 结果 | 为什么 |
|---|---|---|
| 整个 profile 目录 | 不行 | 里面的 cookie 是用 DPAPI 密钥加密的，那把钥匙搬不走 |
| cookie 的**值**（导出的 JSON） | 行 | 明文的名值对，接收方浏览器用它自己的密钥重新加密 |

数据库里的 `session` 字段本来就能搬（纯字符串），那就是方案 A；`visit` 类账号的站点会话在 profile
里，但它每天由无头跳转自己重拿，所以那种账号要搬的是上面那层 IdP 会话。

## 环境变量

全部可选。

| 变量 | 默认 | 说明 |
|---|---|---|
| `PANEL_HOST` | `run.py`: `0.0.0.0` / 桌面版: `127.0.0.1` | 绑定地址。**这是信任边界** |
| `PANEL_PORT` | `8000` | 端口 |
| `PANEL_SCHEDULER` | 开 | `0` 关掉每日自动签到 |
| `PANEL_PROMO` | 开 | `0` 关掉推荐卡片，不再发起任何请求 |
| `CHECKIN_PROXY_URL` | `http://127.0.0.1:7897` | 仅浏览器登录用。容器里主机代理是 `http://host.docker.internal:7897` |
| `TZ` | 系统 | 容器里必须设对，见上文 |

## 开发

```bat
.venv\Scripts\python.exe -m pytest              :: 201 个测试
cd frontend && npm run dev                       :: 前端热重载，:5173 代理到 :8000
```

Fork 之后建议先装上这个钩子，它会在 `git commit` 时拦下形似凭据的字符串和数据库文件：

```bat
.venv\Scripts\python.exe scripts\check_secrets.py --install
.venv\Scripts\python.exe scripts\check_secrets.py --all   :: 或手动全树扫一遍
```

它只匹配有固定前缀、不可能有正当含义的形状（`ghp_`、`sk-`、`AKIA`、私钥头等），所以报警就是真
的；不做熵值和 `password=` 这类模糊判断，因为在本仓库只产出误报，而一个乱叫的检查会被
`--no-verify` 绕过，比没有检查更糟。它从不打印匹配到的值。

改前端不用重启面板；改 `panel/` 要重启。

`panel/` 必须保持 OS 中立（它要在 Linux 容器里被导入），所有 Windows 专有代码都在仓库根的
`desktop/` 里。测试目录的划分不是装饰：`panel/tests/`（188 个）要能在容器里跑，`tests/`
（13 个）测桌面外壳，那些模块故意不在镜像里。

架构和约定写在 [`AGENTS.md`](AGENTS.md)，踩过的坑连实测数据写在
[`docs/agents/traps.md`](docs/agents/traps.md)，术语表在 [`CONTEXT.md`](CONTEXT.md)，
每个非显然的决定都有一条 [`docs/adr/`](docs/adr/)。

## 它不做什么

- **面板不跑就不签到。** 没有外部调度器，没有服务端组件（ADR-0008），这也是运行方式为什么重要。
- **没有 dry-run。** 界面上点「签到」就是真签到（ADR-0005）。
- **数据不加密。** 三种方式的信任边界都是宿主机本身。
- **没有遥测。** 面板自己只发一个外部请求：推荐卡片清单，不携带任何关于你的信息，
  `PANEL_PROMO=0` 完全关闭（[`docs/promo-cards.md`](docs/promo-cards.md)）。浏览器内核的下载
  由 cloakbrowser 自己发起，见 [`THIRD-PARTY.md`](THIRD-PARTY.md)。

## 许可

本项目 MIT，见 [`LICENSE`](LICENSE)。

第三方组件的许可和义务在 [`THIRD-PARTY.md`](THIRD-PARTY.md)，其中有一条要留意：托盘图标用的
`pystray` 是 **LGPLv3**，且被打进了桌面版 exe。这不要求你的代码闭源（本来就是开源的），但分发
zip 时需要保留那份声明。

`.github/workflows/checkin.yml` 是**废弃代码**，它跑的是上游那个老脚本、不是这个面板，仅作参考
保留（ADR-0008）。fork 之后不要指望它能用。

本项目与它签到的任何站点均无隶属关系。站点的服务条款请自行遵守。
