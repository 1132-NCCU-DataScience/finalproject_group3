library(shiny)
library(shinydashboard)
library(leaflet)
library(dplyr)
library(plotly)
library(lubridate)
library(ggplot2)
library(reticulate)
library(DT)

# 設定Python環境
use_condaenv("starlink-env", required = TRUE)

# 載入Python分析模組
source_python("satellite_analysis.py")

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
    
    # 創建分析對象
    tryCatch({
      analysis_data$status <- "正在創建分析對象..."
      
      # 這裡必須使用python調用
      isolate({
        # 創建自定義輸出目錄
        output_dir <- file.path("output", format(Sys.time(), "%Y%m%d_%H%M%S"))
        
        # 執行Python分析代碼
        py_run_string(paste0("
import os
import json
from satellite_analysis import StarlinkAnalysis

# 設置參數
output_dir = '", output_dir, "'
lat = ", input$lat, "
lon = ", input$lon, "
interval = ", input$interval, "

# 創建分析對象
analyzer = StarlinkAnalysis(output_dir=output_dir)
analyzer.observer = analyzer.observer.at(lat, lon)

# 執行分析
stats, coverage_df, handovers_df = analyzer.analyze_24h_coverage(interval_minutes=interval)

# 生成視覺化
analyzer.generate_visualizations()

# 生成報告
report_path = analyzer.export_html_report()

# 將結果保存到檔案中供R讀取
coverage_df.to_csv('", file.path(output_dir, "coverage_df.csv"), "', index=False)
handovers_df.to_csv('", file.path(output_dir, "handovers_df.csv"), "', index=False)
with open('", file.path(output_dir, "analysis_results.json"), "', 'w') as f:
    json.dump({
        'stats': stats,
        'report_path': report_path,
        'output_dir': output_dir
    }, f)
"))
        
        # 讀取分析結果
        analysis_data$status <- "正在載入分析結果..."
        results_file <- file.path(output_dir, "analysis_results.json")
        if (file.exists(results_file)) {
          results <- jsonlite::fromJSON(results_file)
          analysis_data$stats <- results$stats
          analysis_data$report_path <- results$report_path
          
          # 讀取CSV數據
          analysis_data$coverage_df <- read.csv(file.path(output_dir, "coverage_df.csv"))
          analysis_data$coverage_df$time <- as.POSIXct(analysis_data$coverage_df$time, format="%Y-%m-%d %H:%M:%S")
          
          handovers_file <- file.path(output_dir, "handovers_df.csv")
          if (file.exists(handovers_file)) {
            analysis_data$handovers_df <- read.csv(handovers_file)
            analysis_data$handovers_df$time <- as.POSIXct(analysis_data$handovers_df$time, format="%Y-%m-%d %H:%M:%S")
          }
          
          analysis_data$status <- "分析完成!"
        } else {
          analysis_data$status <- "分析失敗: 無法讀取結果文件"
        }
      })
    }, error = function(e) {
      analysis_data$status <- paste("分析錯誤:", e$message)
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
        "未知", "平均可見衛星數", icon = icon("satellite"), color = "blue"
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
        "未知", "最大可見衛星數", icon = icon("satellite-dish"), color = "green"
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
        "未知", "Handover次數", icon = icon("exchange-alt"), color = "yellow"
      )
    } else {
      valueBox(
        analysis_data$stats$handover_count, "Handover次數",
        icon = icon("exchange-alt"), color = "yellow"
      )
    }
  })
  
  output$coverage_percentage_box <- renderValueBox({
    if (is.null(analysis_data$stats)) {
      valueBox(
        "未知", "覆蓋百分比", icon = icon("percentage"), color = "red"
      )
    } else {
      valueBox(
        paste0(round(analysis_data$stats$coverage_percentage, 1), "%"), "覆蓋百分比",
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
      tags$iframe(src = analysis_data$report_path, width = "100%", height = "800px")
    } else {
      return(h3("報告檔案不存在"))
    }
  })
}

# 執行應用
shinyApp(ui, server) 