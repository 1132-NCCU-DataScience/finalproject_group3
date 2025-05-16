#!/bin/bash

# 改進版啟動腳本 - 使用 R Markdown 替代 Shiny
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
if ! command -v conda &> /dev/null; then
  print_error "找不到conda命令。請先安裝conda: https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html"
  exit 1
fi

print_message "====== 台北市區 24h 衛星 handover 週期與延遲分析 ======"
print_message "已找到conda: $(conda --version)"

# 檢查必要的目錄
check_directory "output"
check_directory "Rmd"

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

# 檢查Python是否成功執行
if [ $? -ne 0 ]; then
  print_error "Python分析失敗，請檢查錯誤訊息"
  exit 1
fi

print_message "Python分析完成，結果保存在output目錄"

# 生成R Markdown報告
print_message "生成互動式HTML報告..."

# 獲取 Conda 環境中的 R 庫路徑
CONDA_R_LIBS=$(conda run -n starlink-env R -e "cat(paste(.libPaths(), collapse=':'))" | tail -n 1)
print_message "使用 R 庫路徑: $CONDA_R_LIBS"

# 檢查所需的R套件是否已安裝
print_message "檢查R套件..."
conda run -n starlink-env \
  R_LIBS_USER="$CONDA_R_LIBS" \
  R_LIBS_SITE="$CONDA_R_LIBS" \
  R -e "options(renv.config.autoloader.enabled = FALSE); pkgs <- c('tidyverse', 'plotly', 'DT', 'jsonlite', 'lubridate', 'htmlwidgets', 'knitr', 'kableExtra', 'viridis', 'rmarkdown'); missing <- pkgs[!pkgs %in% installed.packages()[,'Package']]; if(length(missing) > 0) { cat('缺少的套件: ', paste(missing, collapse=', '), '\n') } else { cat('所有所需套件已安裝\n') }"

# 渲染R Markdown報告
print_message "渲染R Markdown報告..."
conda run -n starlink-env \
  R_LIBS_USER="$CONDA_R_LIBS" \
  R_LIBS_SITE="$CONDA_R_LIBS" \
  R -e "options(renv.config.autoloader.enabled = FALSE); rmarkdown::render('Rmd/enhanced_report.Rmd', output_file = '../output/starlink_coverage_report.html')"

if [ $? -ne 0 ]; then
  print_warning "R Markdown報告生成失敗，但Python分析結果依然可用"
  print_message "您可以查看Python生成的基本HTML報告: output/starlink_coverage_report.html"
else
  print_message "分析完成！報告已生成: output/starlink_coverage_report.html"
  
  # 嘗試自動打開報告
  if command -v xdg-open &> /dev/null; then
    print_message "自動打開報告..."
    xdg-open output/starlink_coverage_report.html
  elif command -v open &> /dev/null; then
    print_message "自動打開報告..."
    open output/starlink_coverage_report.html
  else
    print_message "請手動打開報告: output/starlink_coverage_report.html"
  fi
fi

print_message "分析流程完成！" 