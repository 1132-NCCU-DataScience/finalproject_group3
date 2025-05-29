# ui.R
# Starlink 台北衛星分析系統 - Shiny UI

library(shiny)
library(shinydashboard)
library(plotly)
library(DT)

# 定義 UI
ui <- dashboardPage(
  # Header
  dashboardHeader(
    title = "🛰️ Starlink 台北衛星分析系統",
    titleWidth = 350
  ),
  
  # Sidebar
  dashboardSidebar(
    width = 300,
    sidebarMenu(
      menuItem("分析參數", tabName = "parameters", icon = icon("sliders-h")),
      menuItem("統計結果", tabName = "stats", icon = icon("chart-bar")),
      menuItem("視覺化", tabName = "plots", icon = icon("chart-line")),
      menuItem("數據下載", tabName = "download", icon = icon("download"))
    ),
    
    # 分析參數控制
    div(style = "padding: 20px;",
        h4("分析參數", style = "color: #2c3e50; margin-bottom: 20px;"),
        
        # 觀測位置
        h5("觀測位置", style = "color: #34495e; margin-bottom: 10px;"),
        numericInput("lat", "緯度 (°):", 
                     value = 25.0330, 
                     min = -90, max = 90, step = 0.0001,
                     width = "100%"),
        numericInput("lon", "經度 (°):", 
                     value = 121.5654, 
                     min = -180, max = 180, step = 0.0001,
                     width = "100%"),
        
        # 分析參數
        h5("分析參數", style = "color: #34495e; margin-top: 20px; margin-bottom: 10px;"),
        sliderInput("duration", "分析持續時間 (分鐘):",
                    min = 5, max = 240, value = 60, step = 5,
                    width = "100%"),
        sliderInput("interval", "時間間隔 (分鐘):",
                    min = 0.5, max = 5, value = 1.0, step = 0.5,
                    width = "100%"),
        sliderInput("min_elevation", "最小仰角閾值 (度):",
                    min = 10, max = 45, value = 25, step = 1,
                    width = "100%"),
        
        # 統一的分析按鈕
        br(),
        actionButton("startAnalysis", "🚀 開始分析", 
                     class = "btn-primary btn-lg", 
                     style = "width: 100%; margin-bottom: 20px;"),
        
        # 進度顯示區域
        conditionalPanel(
          condition = "input.startAnalysis > 0",
          div(id = "progressContainer", style = "margin-top: 20px;",
              h5("分析進度", style = "color: #34495e; margin-bottom: 10px;"),
              
              # 進度條
              div(class = "progress", style = "height: 25px; margin-bottom: 15px;",
                  div(id = "progressBar", 
                      class = "progress-bar progress-bar-striped progress-bar-animated",
                      role = "progressbar",
                      style = "width: 0%; transition: width 0.5s ease;",
                      "0%"
                  )
              ),
              
              # 狀態訊息
              div(id = "statusMessage", 
                  style = "color: #7f8c8d; font-size: 0.9em; text-align: center;",
                  "準備開始分析..."
              )
          )
        )
    )
  ),
  
  # Body
  dashboardBody(
    # 自定義 CSS
    tags$head(
      tags$style(HTML("
        .content-wrapper, .right-side {
          background-color: #f8f9fa;
        }
        .box {
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          border-radius: 8px;
        }
        .stat-card {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border-radius: 8px;
          padding: 20px;
          margin-bottom: 15px;
          text-align: center;
        }
        .stat-value {
          font-size: 2.5em;
          font-weight: bold;
          margin-bottom: 5px;
        }
        .stat-title {
          font-size: 1.1em;
          opacity: 0.9;
        }
        .info-card {
          background: #ffffff;
          border-left: 4px solid #3498db;
          padding: 15px;
          margin-bottom: 15px;
          border-radius: 4px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .progress {
          background-color: #f5f5f5;
          border-radius: 4px;
          box-shadow: inset 0 1px 2px rgba(0,0,0,.1);
          overflow: hidden;
        }
        .progress-bar {
          float: left;
          height: 100%;
          font-size: 12px;
          line-height: 20px;
          color: #fff;
          text-align: center;
          background-color: #337ab7;
          box-shadow: inset 0 -1px 0 rgba(0,0,0,.15);
          transition: width .6s ease;
        }
        .progress-bar-striped {
          background-image: linear-gradient(45deg,rgba(255,255,255,.15) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.15) 50%,rgba(255,255,255,.15) 75%,transparent 75%,transparent);
          background-size: 40px 40px;
        }
        .progress-bar-animated {
          animation: progress-bar-stripes 2s linear infinite;
        }
        @keyframes progress-bar-stripes {
          from { background-position: 40px 0; }
          to { background-position: 0 0; }
        }
      "))
    ),
    
    # JavaScript 用於進度條控制
    tags$script(HTML("
      $(document).ready(function() {
        var progressInterval;
        
        // 監聽分析按鈕點擊
        $('#startAnalysis').on('click', function() {
          // 重置進度條
          $('#progressBar').css('width', '0%').text('0%').addClass('progress-bar-animated');
          $('#statusMessage').text('正在初始化分析系統...');
          $('#progressContainer').show();
          
          // 開始進度模擬
          var progress = 0;
          var stepCount = 0;
          progressInterval = setInterval(function() {
            stepCount++;
            progress += Math.random() * 15 + 5;  // 每次增加 5-20%
            
            // 確保進度條能完成
            if (stepCount > 15 || progress > 95) {
              progress = 100;
              clearInterval(progressInterval);
              
              $('#progressBar').css('width', '100%').text('100%').removeClass('progress-bar-animated');
              $('#statusMessage').text('✅ 分析完成！正在更新圖表...');
              
              // 3秒後隱藏進度條
              setTimeout(function() {
                $('#progressContainer').fadeOut('slow');
              }, 3000);
            } else {
              $('#progressBar').css('width', progress + '%').text(Math.round(progress) + '%');
              
              // 更新狀態訊息
              if (progress < 20) {
                $('#statusMessage').text('正在載入衛星數據...');
              } else if (progress < 40) {
                $('#statusMessage').text('正在計算軌道位置...');
              } else if (progress < 60) {
                $('#statusMessage').text('正在分析覆蓋情況...');
              } else if (progress < 80) {
                $('#statusMessage').text('正在生成統計數據...');
              } else {
                $('#statusMessage').text('正在準備結果顯示...');
              }
            }
          }, 200);
        });
        
        // 如果需要，也可以監聽 Shiny 完成訊息
        Shiny.addCustomMessageHandler('analysisComplete', function(message) {
          if (progressInterval) {
            clearInterval(progressInterval);
          }
          
          $('#progressBar').css('width', '100%').text('100%').removeClass('progress-bar-animated');
          $('#statusMessage').text('✅ 分析完成！正在更新圖表...');
          
          // 2秒後隱藏進度條
          setTimeout(function() {
            $('#progressContainer').fadeOut('slow');
          }, 2000);
        });
      });
    ")),
    
    tabItems(
      # 參數頁面
      tabItem(tabName = "parameters",
        fluidRow(
          box(
            title = "系統說明", status = "primary", solidHeader = TRUE,
            width = 12, collapsible = TRUE,
            div(class = "info-card",
                h4("🛰️ 關於 Starlink 台北衛星分析系統", style = "color: #2c3e50;"),
                p("本系統專為分析 SpaceX Starlink 衛星在台北地區的覆蓋情況而設計。"),
                p("系統特色："),
                tags$ul(
                  tags$li("📡 精確的衛星軌道計算"),
                  tags$li("⚡ 高效能並行運算"),
                  tags$li("📊 互動式數據視覺化"),
                  tags$li("💾 完整的結果匯出功能")
                )
            ),
            div(class = "info-card",
                h4("🔧 參數說明", style = "color: #2c3e50;"),
                tags$ul(
                  tags$li(strong("緯度/經度："), "觀測者的地理位置座標"),
                  tags$li(strong("分析持續時間："), "分析的總時長（5-240分鐘）"),
                  tags$li(strong("時間間隔："), "計算的時間步長（0.5-5分鐘）"),
                  tags$li(strong("最小仰角閾值："), "衛星被視為可見的最低角度（10-45度）")
                )
            )
          )
        )
      ),
      
      # 統計結果頁面
      tabItem(tabName = "stats",
        fluidRow(
          # 統計卡片
          column(3,
            div(class = "stat-card",
                div(class = "stat-value", textOutput("avgSatellites")),
                div(class = "stat-title", "平均可見衛星數")
            )
          ),
          column(3,
            div(class = "stat-card",
                div(class = "stat-value", textOutput("maxSatellites")),
                div(class = "stat-title", "最大可見衛星數")
            )
          ),
          column(3,
            div(class = "stat-card",
                div(class = "stat-value", textOutput("coveragePercentage")),
                div(class = "stat-title", "覆蓋率 (%)")
            )
          ),
          column(3,
            div(class = "stat-card",
                div(class = "stat-value", textOutput("avgElevation")),
                div(class = "stat-title", "平均仰角 (°)")
            )
          )
        ),
        
        fluidRow(
          # 詳細統計表格
          box(
            title = "詳細統計數據", status = "info", solidHeader = TRUE,
            width = 8, collapsible = TRUE,
            DT::dataTableOutput("statsTable")
          ),
          
          # 分析資訊
          box(
            title = "分析資訊", status = "warning", solidHeader = TRUE,
            width = 4, collapsible = TRUE,
            verbatimTextOutput("analysisInfo")
          )
        )
      ),
      
      # 視覺化頁面
      tabItem(tabName = "plots",
        fluidRow(
          # 互動式時間線圖
          box(
            title = "可見衛星數時間線 (互動式)", status = "primary", solidHeader = TRUE,
            width = 8, collapsible = TRUE,
            plotlyOutput("timelinePlot", height = "400px")
          ),
          
          # 統計摘要圖
          box(
            title = "統計摘要", status = "info", solidHeader = TRUE,
            width = 4, collapsible = TRUE,
            plotOutput("summaryPlot", height = "400px")
          )
        ),
        
        fluidRow(
          # 仰角變化圖
          box(
            title = "最佳衛星仰角變化", status = "success", solidHeader = TRUE,
            width = 6, collapsible = TRUE,
            plotOutput("elevationPlot", height = "350px")
          ),
          
          # 覆蓋統計
          box(
            title = "覆蓋統計圖", status = "warning", solidHeader = TRUE,
            width = 6, collapsible = TRUE,
            plotOutput("coveragePlot", height = "350px")
          )
        )
      ),
      
      # 下載頁面
      tabItem(tabName = "download",
        fluidRow(
          box(
            title = "數據下載", status = "primary", solidHeader = TRUE,
            width = 8, collapsible = TRUE,
            div(class = "info-card",
                h4("📥 下載選項", style = "color: #2c3e50;"),
                p("您可以下載以下格式的分析結果："),
                br(),
                # 下載按鈕
                div(style = "text-align: center;",
                    downloadButton("downloadStats", "📊 下載統計數據 (JSON)", 
                                   class = "btn-primary", 
                                   style = "margin: 5px; width: 200px;"),
                    br(),
                    downloadButton("downloadData", "📈 下載覆蓋數據 (CSV)", 
                                   class = "btn-info", 
                                   style = "margin: 5px; width: 200px;"),
                    br(),
                    downloadButton("downloadReport", "📄 下載完整報告 (HTML)", 
                                   class = "btn-success", 
                                   style = "margin: 5px; width: 200px;"),
                    br(),
                    downloadButton("downloadPlots", "🖼️ 下載圖表 (PNG)", 
                                   class = "btn-warning", 
                                   style = "margin: 5px; width: 200px;")
                )
            )
          ),
          
          # 檔案資訊
          box(
            title = "檔案資訊", status = "info", solidHeader = TRUE,
            width = 4, collapsible = TRUE,
            verbatimTextOutput("fileInfo")
          )
        ),
        
        fluidRow(
          box(
            title = "使用說明", status = "warning", solidHeader = TRUE,
            width = 12, collapsible = TRUE,
            div(class = "info-card",
                h4("📋 文件格式說明", style = "color: #2c3e50;"),
                tags$ul(
                  tags$li(strong("JSON 統計數據："), "包含所有關鍵統計指標的結構化數據"),
                  tags$li(strong("CSV 覆蓋數據："), "包含時間線數據，可用於進一步分析"),
                  tags$li(strong("HTML 報告："), "完整的視覺化報告，包含圖表和說明"),
                  tags$li(strong("PNG 圖表："), "高解析度圖表，適合論文或報告使用")
                ),
                br(),
                p(strong("注意："), "系統會自動載入最佳的分析結果，確保數據的準確性。")
            )
          )
        )
      )
    )
  )
) 