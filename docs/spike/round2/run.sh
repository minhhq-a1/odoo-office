#!/bin/bash
cd /tmp/claude-0/spike/pc
export PATH=/tmp/claude-0/spike/node-v24.11.1-linux-x64/bin:$PATH PAPERCLIP_HOME=/tmp/claude-0/spike/home DATABASE_URL=postgres://paperclip:paperclip@localhost:5432/paperclip PAPERCLIP_TELEMETRY_DISABLED=1
exec pnpm paperclipai run >> /tmp/claude-0/spike/server.log 2>&1
