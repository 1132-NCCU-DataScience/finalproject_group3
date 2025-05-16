#!/bin/bash

# 簡化版啟動腳本 - 避開renv問題
# 作者: Claude 3.7 Sonnet

# 設置顏色輸出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 打印帶顏色的訊息
print_message() {
  echo -e "${BLUE}[$(date +"%Y-%m-%d %H:%M:%S")] ${GREEN}$1${NC}"
}

print_error() {
  echo -e "${BLUE}[$(date +"%Y-%m-%d %H:%M:%S")] ${RED}錯誤: $1${NC}"
}

# 檢查目錄
check_directory() {
  if [ ! -d "$1" ]; then
    print_message "創建目錄 $1"
    mkdir -p "$1"
  fi
}

# 檢查conda是否已安裝
if ! command -v conda &> /dev/null; then
  print_error "找不到conda命令。請先安裝conda: https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html"
  exit 1
fi

print_message "====== 台北市區 24h 衛星 handover 週期與延遲分析 ======"
print_message "已找到conda: $(conda --version)"

# 檢查必要的目錄
check_directory "output"

# 確認環境是否存在並更新
if ! conda env list | grep -q "starlink-env"; then
  print_message "創建conda環境: starlink-env"
  conda env create -f environment.yml
else
  print_message "環境starlink-env已存在，更新環境"
  conda env update -f environment.yml
fi

# 運行Python分析
print_message "執行Python衛星分析..."
conda run -n starlink-env python satellite_analysis.py

# 啟動Shiny應用
print_message "啟動Shiny Dashboard..."

# 獲取 Conda 環境中的 R 庫路徑
CONDA_R_LIBS=$(conda run -n starlink-env R -e "cat(paste(.libPaths(), collapse=':'))" | tail -n 1)

print_message "使用 R 庫路徑: $CONDA_R_LIBS"

# 設置 R_LIBS_USER 和 R_LIBS_SITE，並嘗試禁用 renv 的自動載入行為
# 啟動 Shiny 應用，強制使用 conda 的 R 庫路徑
conda run -n starlink-env \
    R_LIBS_USER="$CONDA_R_LIBS" \
    R_LIBS_SITE="$CONDA_R_LIBS" \
    R -e "options(renv.config.autoloader.enabled = FALSE); shiny::runApp('app.R', host='0.0.0.0', port=3838, launch.browser=TRUE)" 