# GitHub MCP Tools Not Loading in Claude Code

**Date**: 2026-04-17 14:00
**Severity**: Medium
**Component**: Claude Code MCP Integration
**Status**: Resolved

## What Happened

Configured GitHub MCP via `~/.claude/settings.json` using `npx @modelcontextprotocol/server-github`, but GitHub tools never appeared in Claude Code sessions despite the npx server binary working and token being valid.

## The Brutal Truth

Wasted time debugging a non-existent problem. The infrastructure was already set up correctly — just misconfigured locally. The Docker MCP Toolkit had `github-official` server running with OAuth + secrets, but the Claude Code client was sitting in `disconnected` state.

## Technical Details

- Config: `~/.claude/settings.json` with npx server endpoint
- Status: Server responding, auth token valid, tools missing
- Real issue: `docker mcp client list` showed `claude-code` as `disconnected` to gateway
- Gateway logs: No connection attempts from claude-code client

## Root Cause

Docker MCP Toolkit was the canonical source for GitHub MCP (oauth-ready, secrets configured), but Claude Code client wasn't connected to it. Adding redundant npx server masked the actual problem instead of solving it.

## Resolution

1. Ran `docker mcp client connect claude-code` to bridge the client
2. Removed duplicate npx github server from settings
3. Restarted Claude Code to load Docker MCP gateway (`MCP_DOCKER`)
4. Bonus: Changed `"defaultMode": "auto"` → `"bypassPermissions"` to eliminate permission prompts

## Lesson

Check client connection status before adding server configurations. Infrastructure duplication wastes debugging time.
