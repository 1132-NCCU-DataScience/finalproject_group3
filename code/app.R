# app.R
# Starlink 台北衛星分析系統 - 主應用程式檔案

# 載入必要的庫
library(shiny)
library(shinydashboard)
library(plotly)
library(DT)
library(ggplot2)
library(reticulate)
library(jsonlite)
library(dplyr)
library(scales)

# 設置 Python 環境（可根據需要調整）
tryCatch({
  use_python("/usr/bin/python3", required = FALSE)
}, error = function(e) {
  # 如果找不到 Python 3，嘗試使用系統默認 Python
  tryCatch({
    use_python("python", required = FALSE)
  }, error = function(e2) {
    warning("無法找到 Python 環境，請確保已安裝 Python 和 reticulate 套件")
  })
})

# 確保輸出目錄存在
if (!dir.exists("output")) {
  dir.create("output", recursive = TRUE)
}

# 確保 R 目錄存在
if (!dir.exists("R")) {
  dir.create("R", recursive = TRUE)
}

# 載入 UI 和 Server
source("ui.R")
source("server.R")

# 執行應用程式
shinyApp(ui = ui, server = server) 