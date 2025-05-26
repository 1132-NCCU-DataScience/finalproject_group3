#!/bin/bash

# 🚀 Starlink 台北衛星分析系統 - Flask 網頁服務啟動腳本

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +"%H:%M:%S")] $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo ""
echo "🛰️  ========================================"
echo "🚀  啟動 Starlink 台北衛星分析網頁服務"
echo "🛰️  ========================================"
echo ""

# 切換到專案根目錄 (上一層目錄)
cd "$(dirname "$0")/.."

# 檢查 app/static 目錄是否存在，如果不存在則創建
if [ ! -d "app/static" ]; then
    log "創建 app/static 目錄..."
    mkdir -p app/static
    log_success "app/static 目錄已創建"
fi

# 檢查 app/templates 目錄和 app/templates/index.html 是否存在
if [ ! -d "app/templates" ] || [ ! -f "app/templates/index.html" ]; then
    log_warning "app/templates 目錄或 app/templates/index.html 不存在。"
    log_warning "網頁可能無法正常顯示。請確保已正確設置前端文件。"
fi

# 檢查 run.py 是否存在
if [ ! -f "run.py" ]; then
    log_error "錯誤: 找不到 Flask 啟動腳本 run.py。"
    exit 1
fi

# 停止舊的服務器（如果存在）
log "嘗試停止任何已在運行的開發服務器..."
pkill -f "python run.py" 2>/dev/null || true
pkill -f "gunicorn.*app:app" 2>/dev/null || true # 停止 Gunicorn 服務
sleep 1
log_success "舊服務器檢查完畢。"

echo ""
log "🌐 啟動 Flask 開發網頁服務器..."
log_success "服務器將在 http://0.0.0.0:8080 啟動 (或您在 run.py 中配置的地址和端口)"
log "請在瀏覽器中打開網址。按 Ctrl+C 停止服務器。"
echo ""

# 執行 Flask 應用 (開發模式)
# 您可以傳遞 --debug 參數給 run.py 以啟用 Flask 的除錯模式
# 例如: python run.py --host 0.0.0.0 --port 8080 --debug
python run.py --host 0.0.0.0 --port 8080

# 腳本執行到此處表示 Flask 服務器已停止
log "Flask 網頁服務器已停止。" 