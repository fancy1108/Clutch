# Figma MCP（示例）

Clutch Hub **没有** Figma 专用按钮。第三方 MCP 都走同一张表。

## 官方远程 `https://mcp.figma.com/mcp`（目前连不上 Clutch）

Figma 远程 MCP 只允许目录里的客户端做 OAuth 注册（Claude Code、Cursor、VS Code、Codex 等）。Clutch 不在名单里，`POST /v1/oauth/mcp/register` 会 **403 Forbidden**，所以 **不会出现 Figma 授权页**。这不是 Hub 按钮失灵。

要用官方远程 Figma：在 Clutch 里选 **Claude Code**，并在 Figma 的第三方 Agent 弹窗里打开 Claude Code。

## 本机桌面 MCP（Clutch Hub 可用）

仅当 Figma Dev Mode 里能打开 **Enable desktop MCP server**，且 `curl http://127.0.0.1:3845/mcp` 能通时：

1. Settings → MCP → Transport **HTTP**，网址 `http://127.0.0.1:3845/mcp`，Register。
2. Test connection 应列出工具，再 Enable（FM-02）。

其它第三方 MCP（stdio / 带 API Key 的 HTTP）仍用同一张表，不受 Figma 名单限制。
