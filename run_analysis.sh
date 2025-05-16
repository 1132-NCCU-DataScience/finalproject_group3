#!/bin/bash

# 台北市區 24h 衛星 handover 週期與延遲分析自動化腳本
# 作者: Claude 3.7 Sonnet
# 日期: $(date +"%Y-%m-%d")

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

print_warning() {
  echo -e "${BLUE}[$(date +"%Y-%m-%d %H:%M:%S")] ${YELLOW}警告: $1${NC}"
}

# 檢查目錄
check_directory() {
  if [ ! -d "$1" ]; then
    print_message "創建目錄 $1"
    mkdir -p "$1"
  fi
}

# 檢查conda是否已安裝
check_conda() {
  if ! command -v conda &> /dev/null; then
    print_error "找不到conda命令。請先安裝conda: https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html"
    exit 1
  fi
  print_message "已找到conda: $(conda --version)"
}

# 檢查conda環境是否存在
check_env() {
  if ! conda env list | grep -q "starlink-env"; then
    print_message "創建conda環境: starlink-env"
    conda env create -f environment.yml
  else
    print_message "環境starlink-env已存在，更新環境"
    conda env update -f environment.yml
  fi
}

# 檢查R環境和targets
check_r_env() {
  print_message "檢查R環境..."
  
  # 檢查renv是否初始化
  if [ ! -f "renv.lock" ]; then
    print_message "初始化R環境與套件..."
    conda run -n starlink-env R -e "source('R/init_renv.R')"
  else
    print_message "R環境已初始化，檢查是否需要更新..."
    conda run -n starlink-env R -e "renv::restore()"
  fi
}

# 執行Python分析
run_python_analysis() {
  print_message "執行Python衛星分析..."
  conda run -n starlink-env python satellite_analysis.py
}

# 執行targets分析流程
run_targets_pipeline() {
  print_message "執行R targets分析流程..."
  conda run -n starlink-env R -e "targets::tar_make()"
}

# 啟動Shiny應用
start_shiny() {
  print_message "啟動Shiny Dashboard..."
  conda run -n starlink-env R -e "shiny::runApp('app.R', host='0.0.0.0', port=3838, launch.browser=TRUE)"
}

# 主要執行流程
main() {
  print_message "====== 台北市區 24h 衛星 handover 週期與延遲分析 ======"
  
  # 檢查必要的目錄
  check_directory "output"
  
  # 檢查環境
  check_conda
  check_env
  
  # 檢查R環境
  check_r_env
  
  # 執行Python分析
  if [ "$1" == "--targets-only" ]; then
    run_targets_pipeline
    print_message "targets分析完成，結果保存在output目錄"
    exit 0
  elif [ "$1" == "--analysis-only" ]; then
    run_python_analysis
    print_message "Python分析完成，結果保存在output目錄"
    exit 0
  elif [ "$1" == "--dashboard-only" ]; then
    start_shiny
    exit 0
  else
    # 執行完整流程
    run_python_analysis
    run_targets_pipeline
    # 開啟儀表板
    print_message "啟動互動式儀表板..."
    start_shiny
  fi
}

# 檢查參數並執行
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
  echo "用法: $0 [選項]"
  echo "選項:"
  echo "  --targets-only     僅執行R targets分析流程"
  echo "  --analysis-only    僅執行分析，不啟動儀表板"
  echo "  --dashboard-only   僅啟動儀表板，不執行分析"
  echo "  --help, -h         顯示此幫助訊息"
  exit 0
else
  main "$1"
fi 