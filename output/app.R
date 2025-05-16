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

  output$avg_visible_box <- renderValueBox({
    df <- coverage_data()
    avg_val <- if (nrow(df) > 0 && "visible_count" %in% names(df)) round(mean(df$visible_count, na.rm = TRUE), 1) else "N/A"
    valueBox(avg_val, "平均可見衛星數", icon = icon("calculator"), color = "purple")
  })

  output$max_visible_box <- renderValueBox({
    df <- coverage_data()
    max_val <- if (nrow(df) > 0 && "visible_count" %in% names(df)) max(df$visible_count, na.rm = TRUE) else "N/A"
    valueBox(max_val, "最大可見衛星數", icon = icon("arrow-up"), color = "green")
  })

  output$min_visible_box <- renderValueBox({
    df <- coverage_data()
    min_val <- if (nrow(df) > 0 && "visible_count" %in% names(df)) min(df$visible_count, na.rm = TRUE) else "N/A"
    valueBox(min_val, "最小可見衛星數", icon = icon("arrow-down"), color = "yellow")
  })
  
  output$data_table_preview <- renderDT({
    df <- coverage_data()
    if (nrow(df) > 0) {
      datatable(head(df, 100), options = list(pageLength = 10, scrollX = TRUE))
    } else {
      datatable(data.frame(Message = "沒有可顯示的數據或coverage_data.csv未找到。"), options = list(pageLength = 1))
    }
  })

  output$visibility_plot <- renderPlotly({
    df <- coverage_data()
    if (nrow(df) > 0 && "timestamp" %in% names(df) && "visible_count" %in% names(df)) {
      # 轉換時間戳為POSIXct對象以便繪圖
      df$timestamp <- as.POSIXct(df$timestamp, format="%Y-%m-%d %H:%M:%S", tz="UTC")
      plot_ly(df, x = ~timestamp, y = ~visible_count, type = 'scatter', mode = 'lines+markers') %>%
        layout(title = "可見衛星數量隨時間變化", xaxis = list(title = "時間"), yaxis = list(title = "可見衛星數量"))
    } else {
      plot_ly() %>% layout(title = "無數據可顯示")
    }
  })

  output$elevation_plot <- renderPlotly({
    df <- coverage_data()
    if (nrow(df) > 0 && "timestamp" %in% names(df) && "elevation" %in% names(df)) {
      df$timestamp <- as.POSIXct(df$timestamp, format="%Y-%m-%d %H:%M:%S", tz="UTC")
      plot_ly(df, x = ~timestamp, y = ~elevation, type = 'scatter', mode = 'lines') %>%
        layout(title = "最佳衛星仰角隨時間變化", xaxis = list(title = "時間"), yaxis = list(title = "仰角 (度)"))
    } else {
      plot_ly() %>% layout(title = "無數據可顯示 (或 'elevation' 列缺失)")
    }
  })
}

# 運行應用
shinyApp(ui = ui, server = server)
