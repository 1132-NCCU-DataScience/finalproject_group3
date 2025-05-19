library(shiny)
library(shinydashboard)
library(leaflet)
library(dplyr)
library(plotly)
library(lubridate)
library(ggplot2)
library(reticulate)
library(DT)
library(future)
library(promises)

# 設定Python環境
use_condaenv("starlink-env", required = TRUE)

# 載入Python分析模組
source_python("satellite_analysis.py")

# 初始化分析器（會自動下載 TLE 數據）
py_run_string('
from satellite_analysis import StarlinkAnalysis
global_analyzer = StarlinkAnalysis()  # 創建全局分析器對象
')

# 設定並行運算
plan(multicore, workers = availableCores() - 1)  # 使用所有可用核心減1

# 為靜態文件添加資源路徑
addResourcePath("results", "output")

# 載入分析結果（如果有的話）
coverage_data <- NULL
stats_json <- NULL
if (file.exists("output/coverage_data.csv")) {
    coverage_data <- read.csv("output/coverage_data.csv")
}
if (file.exists("output/coverage_stats.json")) {
    stats_json <- jsonlite::fromJSON("output/coverage_stats.json")
}

# UI
ui <- dashboardPage(
  dashboardHeader(title = "台北市Starlink分析"),
  dashboardSidebar(
    sidebarMenu(
      menuItem("儀表板", tabName = "dashboard", icon = icon("dashboard")),
      menuItem("衛星覆蓋", tabName = "coverage", icon = icon("satellite")),
      menuItem("Handover分析", tabName = "handover", icon = icon("exchange-alt")),
      menuItem("覆蓋熱圖", tabName = "heatmap", icon = icon("fire")),
      menuItem("報告", tabName = "report", icon = icon("file-alt")),
      hr(),
      div(style = "padding: 20px;",
          p("分析參數:"),
          numericInput("lat", "緯度:", value = 25.0330),
          numericInput("lon", "經度:", value = 121.5654),
          numericInput("interval", "分析間隔 (分鐘):", value = 1, min = 0.1, max = 60),
          actionButton("analyze", "開始分析", icon = icon("play"), 
                       style = "color: #fff; background-color: #337ab7; border-color: #2e6da4")
      )
    )
  ),
  dashboardBody(
    tabItems(
      # 儀表板頁面
      tabItem(tabName = "dashboard",
              fluidRow(
                valueBoxOutput("avg_satellites_box", width = 3),
                valueBoxOutput("max_satellites_box", width = 3),
                valueBoxOutput("handover_count_box", width = 3),
                valueBoxOutput("coverage_percentage_box", width = 3)
              ),
              fluidRow(
                box(title = "24小時可見衛星數量", status = "primary", solidHeader = TRUE,
                    plotlyOutput("visible_satellites_plot"), width = 12)
              ),
              fluidRow(
                box(title = "分析狀態", status = "info", solidHeader = TRUE,
                    verbatimTextOutput("analysis_status"), width = 12)
              )
      ),
      
      # 衛星覆蓋頁面
      tabItem(tabName = "coverage",
              fluidRow(
                box(title = "最佳衛星仰角時間線", status = "primary", solidHeader = TRUE,
                    plotlyOutput("best_elevation_plot"), width = 12)
              ),
              fluidRow(
                box(title = "衛星覆蓋數據", status = "info", solidHeader = TRUE,
                    DTOutput("coverage_table"), width = 12)
              )
      ),
      
      # Handover分析頁面
      tabItem(tabName = "handover",
              fluidRow(
                box(title = "Handover時間線", status = "primary", solidHeader = TRUE,
                    plotlyOutput("handover_timeline_plot"), width = 12)
              ),
              fluidRow(
                box(title = "Handover詳細資料", status = "info", solidHeader = TRUE,
                    DTOutput("handover_table"), width = 12)
              )
      ),
      
      # 覆蓋熱圖頁面
      tabItem(tabName = "heatmap",
              fluidRow(
                box(title = "衛星覆蓋熱力圖", status = "primary", solidHeader = TRUE,
                    plotlyOutput("coverage_heatmap", height = "600px"), width = 12)
              )
      ),
      
      # 報告頁面
      tabItem(tabName = "report",
              fluidRow(
                box(title = "HTML報告", status = "primary", solidHeader = TRUE,
                    uiOutput("html_report"), width = 12)
              )
      )
    )
  )
)

# Server
server <- function(input, output, session) {
  
  # 反應性數據
  analysis_data <- reactiveValues(
    stats = NULL,
    coverage_df = NULL,
    handovers_df = NULL,
    report_path = NULL,
    status = "等待開始分析..."
  )
  
  # 分析按鈕事件
  observeEvent(input$analyze, {
    # 更新狀態
    analysis_data$status <- "正在初始化分析..."
    
    # 創建輸出目錄
    output_dir <- file.path("output", format(Sys.time(), "%Y%m%d_%H%M%S"))
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
    
    # 不使用 future_promise，改用同步處理
    tryCatch({
      analysis_data$status <- "正在執行Starlink衛星分析..."
      
      # 執行Python分析代碼
      py_run_string(sprintf('
import os
import json
from satellite_analysis import StarlinkAnalysis

# 設置參數
output_dir = "%s"
lat = %f
lon = %f
interval = %f

# 創建分析對象
analyzer = StarlinkAnalysis(output_dir=output_dir)

# 設置觀察者位置
analyzer.set_observer_location(lat, lon)

# 執行分析
stats = analyzer.analyze_24h_coverage(interval_minutes=interval)

# 保存結果
analyzer.save_results()

# 生成視覺化和報告
analyzer.generate_visualizations()
analyzer.export_html_report()
', output_dir, input$lat, input$lon, input$interval))
      
      # 讀取分析結果
      analysis_data$status <- "正在載入分析結果..."
      
      # 讀取coverage數據
      coverage_file <- file.path(output_dir, "coverage_data.csv")
      if (file.exists(coverage_file)) {
        analysis_data$coverage_df <- read.csv(coverage_file)
        analysis_data$coverage_df$time <- as.POSIXct(analysis_data$coverage_df$time)
      } else {
        stop("找不到覆蓋率數據文件")
      }
      
      # 讀取統計數據
      stats_file <- file.path(output_dir, "coverage_stats.json")
      if (file.exists(stats_file)) {
        analysis_data$stats <- jsonlite::fromJSON(stats_file)
      } else {
        stop("找不到統計數據文件")
      }
      
      # 讀取handover數據
      handover_file <- file.path(output_dir, "handover_data.csv")
      if (file.exists(handover_file)) {
        analysis_data$handovers_df <- read.csv(handover_file)
        analysis_data$handovers_df$time <- as.POSIXct(analysis_data$handovers_df$time)
      }
      
      # 讀取報告路徑
      report_file <- file.path(output_dir, "report.html")
      if (file.exists(report_file)) {
        analysis_data$report_path <- report_file
      }
      
      analysis_data$status <- "分析完成!"
      
    }, error = function(e) {
      analysis_data$status <- paste("分析錯誤:", e$message)
      print(e)
    })
  })
  
  # 狀態輸出
  output$analysis_status <- renderText({
    analysis_data$status
  })
  
  # 數據盒
  output$avg_satellites_box <- renderValueBox({
    if (is.null(analysis_data$stats)) {
      valueBox(
        "0", "平均可見衛星數", icon = icon("satellite"), color = "blue"
      )
    } else {
      valueBox(
        round(analysis_data$stats$avg_visible_satellites, 1), "平均可見衛星數",
        icon = icon("satellite"), color = "blue"
      )
    }
  })
  
  output$max_satellites_box <- renderValueBox({
    if (is.null(analysis_data$stats)) {
      valueBox(
        "0", "最大可見衛星數", icon = icon("satellite-dish"), color = "green"
      )
    } else {
      valueBox(
        analysis_data$stats$max_visible_satellites, "最大可見衛星數",
        icon = icon("satellite-dish"), color = "green"
      )
    }
  })
  
  output$handover_count_box <- renderValueBox({
    if (is.null(analysis_data$stats)) {
      valueBox(
        "0", "Handover次數", icon = icon("exchange-alt"), color = "yellow"
      )
    } else {
      handover_count <- analysis_data$stats$handover_count
      # 如果沒有 handover_count，預設為 0
      if (is.null(handover_count)) handover_count <- 0
      valueBox(
        handover_count, "Handover次數",
        icon = icon("exchange-alt"), color = "yellow"
      )
    }
  })
  
  output$coverage_percentage_box <- renderValueBox({
    if (is.null(analysis_data$stats)) {
      valueBox(
        "0%", "覆蓋百分比", icon = icon("percentage"), color = "red"
      )
    } else {
      coverage_percentage <- analysis_data$stats$coverage_percentage
      # 如果沒有 coverage_percentage，預設為 0
      if (is.null(coverage_percentage)) coverage_percentage <- 0
      valueBox(
        paste0(round(coverage_percentage, 1), "%"), "覆蓋百分比",
        icon = icon("percentage"), color = "red"
      )
    }
  })
  
  # 可見衛星圖表
  output$visible_satellites_plot <- renderPlotly({
    req(analysis_data$coverage_df)
    
    p <- plot_ly(analysis_data$coverage_df, x = ~time, y = ~visible_satellites, 
                 type = 'scatter', mode = 'lines', name = '可見衛星數量') %>%
      layout(title = '24小時內可見Starlink衛星數量',
             xaxis = list(title = '時間 (UTC)'),
             yaxis = list(title = '可見衛星數量'))
    
    return(p)
  })
  
  # 最佳衛星仰角圖表
  output$best_elevation_plot <- renderPlotly({
    req(analysis_data$coverage_df)
    
    p <- plot_ly(analysis_data$coverage_df, x = ~time, y = ~best_alt, 
                 type = 'scatter', mode = 'lines', name = '最佳衛星仰角') %>%
      layout(title = '24小時內最佳衛星仰角',
             xaxis = list(title = '時間 (UTC)'),
             yaxis = list(title = '仰角 (度)'))
    
    return(p)
  })
  
  # Handover時間線圖表
  output$handover_timeline_plot <- renderPlotly({
    req(analysis_data$coverage_df)
    
    # 創建基本圖表
    p <- plot_ly(analysis_data$coverage_df, x = ~time, y = ~best_alt, 
                 type = 'scatter', mode = 'lines', name = '最佳衛星仰角') %>%
      layout(title = 'Handover時間線',
             xaxis = list(title = '時間 (UTC)'),
             yaxis = list(title = '仰角 (度)'))
    
    # 如果有handover數據，添加垂直線
    if (!is.null(analysis_data$handovers_df) && nrow(analysis_data$handovers_df) > 0) {
      for (i in 1:nrow(analysis_data$handovers_df)) {
        p <- add_segments(p,
                          x = analysis_data$handovers_df$time[i], 
                          xend = analysis_data$handovers_df$time[i],
                          y = 0, 
                          yend = 90,
                          line = list(color = 'red', width = 1, dash = 'dash'),
                          showlegend = (i == 1), 
                          name = 'Handover')
      }
    }
    
    return(p)
  })
  
  # 覆蓋數據表格
  output$coverage_table <- renderDT({
    req(analysis_data$coverage_df)
    
    df <- analysis_data$coverage_df %>%
      select(time, visible_satellites, best_satellite, best_alt, best_az, best_distance) %>%
      rename(時間 = time, 
             可見衛星數 = visible_satellites, 
             最佳衛星 = best_satellite, 
             仰角 = best_alt, 
             方位角 = best_az, 
             距離_km = best_distance)
    
    datatable(df, options = list(pageLength = 10))
  })
  
  # Handover數據表格
  output$handover_table <- renderDT({
    req(analysis_data$handovers_df)
    
    if (nrow(analysis_data$handovers_df) > 0) {
      df <- analysis_data$handovers_df %>%
        select(time, from, to, from_alt, to_alt) %>%
        rename(時間 = time, 
               從衛星 = from, 
               到衛星 = to, 
               從仰角 = from_alt, 
               到仰角 = to_alt)
      
      datatable(df, options = list(pageLength = 10))
    } else {
      return(NULL)
    }
  })
  
  # 覆蓋熱力圖
  output$coverage_heatmap <- renderPlotly({
    req(analysis_data$stats)
    
    # 如果分析完成，從文件加載熱力圖
    if (!is.null(analysis_data$stats) && !is.null(analysis_data$report_path)) {
      # 取得輸出目錄
      output_dir <- dirname(analysis_data$report_path)
      
      # 讀取熱力圖HTML
      heatmap_path <- file.path(output_dir, "coverage_heatmap.html")
      if (file.exists(heatmap_path)) {
        # 使用plotly讀取方式
        return(plotly::plotly_build(plotly::ggplotly(ggplot() + 
          annotate("text", x = 0.5, y = 0.5, 
                   label = "熱力圖已儲存，請點擊報告頁籤查看") + 
          theme_void())))
      }
    }
    
    # 否則顯示空圖
    return(plotly::plotly_build(plotly::ggplotly(ggplot() + 
      annotate("text", x = 0.5, y = 0.5, 
               label = "請先執行分析以生成熱力圖") + 
      theme_void())))
  })
  
  # HTML報告
  output$html_report <- renderUI({
    req(analysis_data$report_path)
    
    if (file.exists(analysis_data$report_path)) {
      # 獲取目錄路徑和文件名
      report_dir <- dirname(analysis_data$report_path)
      report_dir_name <- basename(report_dir)
      
      # 創建分頁面板來顯示報告不同部分
      tabsetPanel(
        tabPanel("統計資料", 
          fluidRow(
            column(12, 
              h2("台北市 Starlink 衛星覆蓋分析報告"),
              p(paste("分析時間:", format(Sys.time(), "%Y-%m-%d %H:%M:%S"))),
              hr()
            )
          ),
          fluidRow(
            valueBox(
              round(analysis_data$stats$avg_visible_satellites, 1), 
              "平均可見衛星數", 
              icon = icon("satellite"), 
              color = "blue", 
              width = 4
            ),
            valueBox(
              analysis_data$stats$max_visible_satellites, 
              "最大可見衛星數", 
              icon = icon("satellite-dish"), 
              color = "green", 
              width = 4
            ),
            valueBox(
              paste0(round(analysis_data$stats$coverage_percentage, 1), "%"), 
              "覆蓋百分比", 
              icon = icon("percentage"), 
              color = "red", 
              width = 4
            )
          )
        ),
        tabPanel("時間線圖", 
          fluidRow(
            column(12, 
              h3("可見衛星數量時間線"),
              img(src=paste0("results/", report_dir_name, "/visible_satellites_timeline.png"), 
                  width="100%", alt="可見衛星數量時間線"),
              h3("最佳衛星仰角時間線"),
              img(src=paste0("results/", report_dir_name, "/elevation_timeline.png"), 
                  width="100%", alt="最佳衛星仰角時間線")
            )
          )
        ),
        tabPanel("熱力圖", 
          fluidRow(
            column(12, 
              h3("互動式覆蓋熱力圖"),
              tags$iframe(src=paste0("results/", report_dir_name, "/coverage_heatmap.html"), 
                         width="100%", height="600px", frameborder="0")
            )
          )
        ),
        tabPanel("完整報告", 
          fluidRow(
            column(12, 
              tags$iframe(src=paste0("results/", report_dir_name, "/report.html"), 
                         width="100%", height="800px", frameborder="0")
            )
          )
        )
      )
    } else {
      return(h3("報告檔案不存在"))
    }
  })
}

# 執行應用
shinyApp(ui, server) 