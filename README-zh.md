# droidrun-agent 中文快速说明

## 1. 下载并安装 Portal 手机端 APK

前往 [droidrun-portal 发布页](https://github.com/droidrun/droidrun-portal/releases)，下载最新 Portal APK 并安装到你的安卓设备。

---

## 2. 获取连接信息（URL 和 TOKEN）

打开 Portal App，复制首页显示的服务 URL 和 TOKEN（服务地址和认证信息），后续集成均需使用。

---

## 3. 安装 uvx

建议用 pip 安装 uvx（自动处理所有依赖）：
```bash
pip install uvx
```
> 更详细安装方式见 [uvx 官方文档](https://github.com/astral-sh/uv)。

---

## 4. 各平台集成

### OpenClaw 集成

```bash
npm i -g clawhub    # 或 pnpm add -g clawhub
clawhub install hanxi/droidrun-agent
```
安装完成后，将刚才获取的 `URL` 和 `TOKEN` 填入 OpenClaw 对应配置环境变量。

详细操作与常见问题请见 [ClawHub工具文档](https://docs.openclaw.ai/zh-CN/tools/clawhub)。

---

### Codex 集成

方式一：CLI 配置 MCP Server
```bash
codex mcp add droidrun-agent --env PORTAL_BASE_URL=<你的URL> --env PORTAL_TOKEN=<你的TOKEN> -- uvx --with mcp droidrun-agent --mcp
```

方式二：编辑 config.toml 文件
```toml
[mcp_servers.droidrun-agent]
command = "uvx"
args = ["--with", "mcp", "droidrun-agent", "--mcp"]

[mcp_servers.droidrun-agent.env]
PORTAL_BASE_URL = "<你的URL>"
PORTAL_TOKEN = "<你的TOKEN>"
```
配置详细用法见 [Codex MCP官方文档](https://developers.openai.com/codex/mcp)。

---

### Qoder 集成

在 Qoder IDE 的【MCP设置】页，“我的服务”里点击“+ 添加”，粘贴以下配置：
```json
{
  "mcpServers": {
    "droidrun-agent": {
      "command": "uvx",
      "args": [
        "--with",
        "mcp",
        "droidrun-agent",
        "--mcp"
      ],
      "env": {
        "PORTAL_BASE_URL": "<你的URL>",
        "PORTAL_TOKEN": "<你的TOKEN>"
      }
    }
  }
}
```
保存后即可启用。详细步骤参考 [Qoder官方文档](https://docs.qoder.com/zh/user-guide/chat/model-context-protocol)。

---

> 三个平台均推荐 uvx 方式集成。务必先安装手机端 APK，并从 app 首页获取服务 URL 和 TOKEN，填入对应配置，即可在 IDE 或智能体中控制安卓设备。
> uvx 自动管理依赖，无需担心 Python 环境。

更多高级用法和排查措施请查阅官方文档：
- [ClawHub工具库](https://clawhub.ai/hanxi/droidrun-agent)
- [OpenClaw官方ClawHub文档](https://docs.openclaw.ai/zh-CN/tools/clawhub)
- [OpenAI Codex MCP](https://developers.openai.com/codex/mcp)
- [Qoder官方MCP配置说明](https://docs.qoder.com/zh/user-guide/chat/model-context-protocol)
- [droidrun-portal 手机APK下载](https://github.com/droidrun/droidrun-portal/releases)
