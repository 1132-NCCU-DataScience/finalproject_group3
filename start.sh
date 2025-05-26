#!/bin/bash

# 🚀 Starlink 台北衛星分析系統 - 簡化啟動
# 這個腳本會調用主要的網頁服務啟動腳本

echo "🛰️  啟動 Starlink 台北衛星分析系統網頁服務..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# 調用主要的網頁啟動腳本
"$SCRIPT_DIR/scripts/start_web.sh" 