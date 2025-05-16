#!/bin/bash

# 台北市區 24h 衛星 handover 週期與延遲分析自動化腳本
# 作者: Claude 3.7 Sonnet
# 日期: $(date +"%Y-%m-%d")

# 設置顏色輸出
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
RED='\\033[0;31m'
NC='\\033[0m' # No Color

# 默認參數
CPU_COUNT=0  # 0表示使用所有可用CPU
OUTPUT_DIR_NAME="output" # 定義輸出目錄名稱

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
  print_message "檢測到conda已安裝"
}

# 安裝必要的Python套件
install_python_packages() {
  print_message "檢查並安裝必要的Python套件..."
  
  PYTHON_PACKAGES="pandas numpy matplotlib skyfield tqdm plotly"
  
  # 使用pip quietly install packages and check result
  if pip install $PYTHON_PACKAGES; then
    print_message "所有Python套件已成功安裝/已是最新版本。"
  else
    print_error "部分Python套件安裝失敗。"
    # Optionally, add more detailed error checking per package if needed
    return 1
  fi
  return 0
}

# 安裝/檢查必要的R套件
check_and_install_r_packages() {
  print_message "檢查並安裝必要的R套件..."
  
  # 安裝R套件的腳本
  R_SCRIPT_CONTENT=$(cat << 'EOF'
required_packages <- c("shiny", "shinydashboard", "plotly", "DT", "ggplot2", "dplyr", "tidyr", "lubridate", "htmlwidgets")
new_packages <- required_packages[!(required_packages %in% installed.packages()[,"Package"])]
if(length(new_packages) > 0) {
  cat("正在安裝R套件:", paste(new_packages, collapse=", "), "\\n")
  install.packages(new_packages, repos="https://cloud.r-project.org")
} else {
  cat("所有必要的R套件已安裝\\n")
}
EOF
)

  # 執行R腳本安裝套件
  if conda run -n base Rscript -e "$R_SCRIPT_CONTENT"; then
    print_message "R套件檢查/安裝完成。"
  else
    print_error "R套件安裝過程中發生錯誤。"
    return 1
  fi
  return 0
}

# 顯示幫助訊息
show_help() {
  echo ""
  echo "使用方式：$0 [選項]"
  echo "選項:"
  echo "  --help                    顯示此幫助訊息"
  echo "  --cpu=NUMBER              指定要使用的CPU核心數量 (默認: 使用所有可用核心)"
  echo "  --update-tle              更新TLE數據 (默認: 否)"
  echo "  --analyze-only            只執行分析，不啟動儀表板 (默認: 否)"
  echo "  --dashboard-only          只啟動儀表板，不執行分析 (默認: 否)"
  echo "  --verbose                 顯示詳細輸出 (默認: 否)"
  echo ""
  exit 0
}

# 解析命令行參數
ANALYZE=true
UPDATE_TLE=false
DASHBOARD=true
VERBOSE=false

for arg in "$@"; do
  case $arg in
    --help)
      show_help
      ;;
    --cpu=*)
      CPU_COUNT="${arg#*=}"
      if ! [[ "$CPU_COUNT" =~ ^[0-9]+$ ]]; then
        print_error "CPU數量必須是一個正整數"
        exit 1
      fi
      ;;
    --update-tle)
      UPDATE_TLE=true
      ;;
    --analyze-only)
      DASHBOARD=false
      ;;
    --dashboard-only)
      ANALYZE=false
      ;;
    --verbose)
      VERBOSE=true
      ;;
    *)
      print_error "未知的參數: $arg"
      show_help
      ;;
  esac
done

# 主程序
main() {
  print_message "開始執行Starlink台北24h衛星分析"
  
  check_conda
  check_directory "${OUTPUT_DIR_NAME}"
  check_directory "data" # 假設您有一個名為 data 的目錄用於其他數據
  
  install_python_packages || exit 1 # 如果Python套件安裝失敗則退出
  check_and_install_r_packages || exit 1 # 如果R套件安裝失敗則退出
  
  if [ "$UPDATE_TLE" = true ]; then
    print_message "更新TLE數據..."
    # 假設您有一個 update_tle.py 腳本
    # python update_tle.py
    print_warning "TLE更新功能暫未實現 (update_tle.py 未找到)"
  fi
  
  if [ "$ANALYZE" = true ]; then
    print_message "執行衛星分析 (日誌將保存在 ${OUTPUT_DIR_NAME}/analysis.log)..."
    # 使用 tee 同時輸出到控制台和日誌文件
    if [ "$CPU_COUNT" -eq 0 ]; then
      python satellite_analysis.py | tee "${OUTPUT_DIR_NAME}/analysis.log"
    else
      python satellite_analysis.py --cpu "$CPU_COUNT" | tee "${OUTPUT_DIR_NAME}/analysis.log"
    fi
    # 檢查Python腳本的退出狀態
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        print_error "Python衛星分析腳本執行失敗。請查看 ${OUTPUT_DIR_NAME}/analysis.log 獲取詳細信息。"
        exit 1
    fi
    print_message "Python分析完成，結果保存在 ${OUTPUT_DIR_NAME} 目錄"
  fi
  
  if [ "$DASHBOARD" = true ]; then
    run_dashboard
  fi
  
  print_message "處理完成"
}

# 執行R儀表板
run_dashboard() {
  print_message "準備啟動R Shiny儀表板..."
  
  SHINY_APP_FILE="${OUTPUT_DIR_NAME}/app.R"

  # 創建一個基本的 Shiny app.R 文件 (如果它不存在)
  # 您應該用您自己的 Shiny 應用程式邏輯替換這個基本版本
  if [ ! -f "$SHINY_APP_FILE" ]; then
    print_warning "Shiny應用文件 ${SHINY_APP_FILE} 未找到。將創建一個基本的演示應用。"
    cat > "$SHINY_APP_FILE" << EOF
library(shiny)
library(shinydashboard)
library(plotly)
library(DT)
library(dplyr) # 確保dplyr已加載

# UI 定義
ui <- dashboardPage(
  dashboardHeader(title = "Starlink 分析儀表板"),
  dashboardSidebar(
    sidebarMenu(
      menuItem("數據摘要", tabName = "summary", icon = icon("table")),
      menuItem("可見衛星數", tabName = "visibility", icon = icon("satellite-dish")),
      menuItem("衛星仰角", tabName = "elevation", icon = icon("chart-line"))
    )
  ),
  dashboardBody(
    tabItems(
      tabItem(tabName = "summary",
              fluidRow(
                valueBoxOutput("avg_visible_box"),
                valueBoxOutput("max_visible_box"),
                valueBoxOutput("min_visible_box")
              ),
              fluidRow(
                box(title = "數據預覽 (前100行)", status = "primary", solidHeader = TRUE, width = 12,
                    DTOutput("data_table_preview"))
              )
      ),
      tabItem(tabName = "visibility",
              fluidRow(
                box(title = "可見衛星數量隨時間變化", status = "primary", solidHeader = TRUE, width = 12,
                    plotlyOutput("visibility_plot"))
              )
      ),
      tabItem(tabName = "elevation",
              fluidRow(
                box(title = "最佳衛星仰角隨時間變化", status = "info", solidHeader = TRUE, width = 12,
                    plotlyOutput("elevation_plot"))
              )
      )
    )
  )
)

# Server 邏輯
server <- function(input, output, session) {
  # 嘗試讀取數據
  coverage_data <- reactive({
    data_path <- "coverage_data.csv" # 假設 app.R 和 csv 在同一目錄 (output)
    if (file.exists(data_path)) {
      read.csv(data_path)
    } else {
      # 返回一個空的 data frame，如果文件不存在
      data.frame(timestamp=character(), visible_count=integer(), elevation=numeric(), stringsAsFactors=FALSE)
    }
  })

  output\$avg_visible_box <- renderValueBox({
    df <- coverage_data()
    avg_val <- if (nrow(df) > 0 && "visible_count" %in% names(df)) round(mean(df\$visible_count, na.rm = TRUE), 1) else "N/A"
    valueBox(avg_val, "平均可見衛星數", icon = icon("calculator"), color = "purple")
  })

  output\$max_visible_box <- renderValueBox({
    df <- coverage_data()
    max_val <- if (nrow(df) > 0 && "visible_count" %in% names(df)) max(df\$visible_count, na.rm = TRUE) else "N/A"
    valueBox(max_val, "最大可見衛星數", icon = icon("arrow-up"), color = "green")
  })

  output\$min_visible_box <- renderValueBox({
    df <- coverage_data()
    min_val <- if (nrow(df) > 0 && "visible_count" %in% names(df)) min(df\$visible_count, na.rm = TRUE) else "N/A"
    valueBox(min_val, "最小可見衛星數", icon = icon("arrow-down"), color = "yellow")
  })
  
  output\$data_table_preview <- renderDT({
    df <- coverage_data()
    if (nrow(df) > 0) {
      datatable(head(df, 100), options = list(pageLength = 10, scrollX = TRUE))
    } else {
      datatable(data.frame(Message = "沒有可顯示的數據或coverage_data.csv未找到。"), options = list(pageLength = 1))
    }
  })

  output\$visibility_plot <- renderPlotly({
    df <- coverage_data()
    if (nrow(df) > 0 && "timestamp" %in% names(df) && "visible_count" %in% names(df)) {
      # 轉換時間戳為POSIXct對象以便繪圖
      df\$timestamp <- as.POSIXct(df\$timestamp, format="%Y-%m-%d %H:%M:%S", tz="UTC")
      plot_ly(df, x = ~timestamp, y = ~visible_count, type = 'scatter', mode = 'lines+markers') %>%
        layout(title = "可見衛星數量隨時間變化", xaxis = list(title = "時間"), yaxis = list(title = "可見衛星數量"))
    } else {
      plot_ly() %>% layout(title = "無數據可顯示")
    }
  })

  output\$elevation_plot <- renderPlotly({
    df <- coverage_data()
    if (nrow(df) > 0 && "timestamp" %in% names(df) && "elevation" %in% names(df)) {
      df\$timestamp <- as.POSIXct(df\$timestamp, format="%Y-%m-%d %H:%M:%S", tz="UTC")
      plot_ly(df, x = ~timestamp, y = ~elevation, type = 'scatter', mode = 'lines') %>%
        layout(title = "最佳衛星仰角隨時間變化", xaxis = list(title = "時間"), yaxis = list(title = "仰角 (度)"))
    } else {
      plot_ly() %>% layout(title = "無數據可顯示 (或 'elevation' 列缺失)")
    }
  })
}

# 運行應用
shinyApp(ui = ui, server = server)
EOF
  fi

  print_message "啟動R Shiny儀表板於 http://0.0.0.0:3838 (按 CTRL+C 停止)..."
  # 進入 output 目錄執行 Shiny App，這樣 app.R 可以直接讀取同目錄下的 coverage_data.csv
  (cd "${OUTPUT_DIR_NAME}" && conda run -n base Rscript -e "shiny::runApp('app.R', host='0.0.0.0', port=3838)")
}

# 執行主程序
main 