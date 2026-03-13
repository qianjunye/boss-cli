# Boss CLI

A terminal client for **Boss Zhipin (BOSS直聘)** — search jobs and chat with bosses from the command line.

## Installation

```bash
# Recommended
uv tool install boss-cli

# Alternative
pipx install boss-cli
```

## Quick Start

```bash
# Login via QR code
boss login

# Search jobs
boss search "Python"
boss search "前端" -c 上海
boss search "Golang" -c 深圳 -p 2

# Check login status
boss status

# Logout
boss logout
```

## Commands

| Command | Description |
|---------|-------------|
| `boss login` | 扫码登录 Boss 直聘 APP |
| `boss logout` | 清除已保存的登录凭证 |
| `boss status` | 查看当前登录状态 |
| `boss search <keyword>` | 搜索职位 |

### Search Options

- `-c, --city` — 城市名称 (默认: 全国)
- `-p, --page` — 页码 (默认: 1)
- `--json-output` — 输出原始 JSON

## Supported Cities

北京、上海、广州、深圳、杭州、成都、南京、武汉、西安、苏州、长沙、天津、重庆、郑州、厦门、合肥、大连、青岛、东莞、佛山、宁波、珠海、无锡

## Authentication

Boss CLI supports three authentication methods (tried in order):

1. **Saved credential** — `~/.config/boss-cli/credential.json`
2. **Browser cookies** — Auto-extracted via `browser-cookie3`
3. **QR code login** — Scan with Boss Zhipin APP

## License

Apache-2.0
