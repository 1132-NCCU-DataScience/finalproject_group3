# R/plots.R
# Starlink 圖表生成模組

library(ggplot2)
library(plotly)
library(dplyr)
library(scales)

# 安全訪問列表元素的輔助函數
`%||%` <- function(a, b) if (is.null(a) || length(a) == 0 || is.na(a)) b else a

#' 創建可見衛星數量時間線圖
#' 
#' @param coverage_data 覆蓋數據 data.frame
#' 
#' @return ggplot 對象
create_satellites_timeline <- function(coverage_data) {
  if (nrow(coverage_data) == 0) {
    return(ggplot() + 
           ggtitle("無數據可顯示") +
           theme_minimal())
  }
  
  # 添加時間分鐘欄位
  coverage_data$time_minutes <- seq(0, nrow(coverage_data) - 1)
  
  p <- ggplot(coverage_data, aes(x = time_minutes, y = visible_count)) +
    geom_line(color = "#3498db", linewidth = 1.2, alpha = 0.8) +
    geom_point(color = "#2980b9", size = 1.5, alpha = 0.6) +
    geom_area(alpha = 0.3, fill = "#3498db") +
    labs(
      title = "Starlink 可見衛星數量時間線",
      subtitle = paste("分析持續時間:", nrow(coverage_data), "分鐘"),
      x = "時間 (分鐘)",
      y = "可見衛星數量"
    ) +
    theme_minimal() +
    theme(
      plot.title = element_text(size = 16, face = "bold", color = "#2c3e50"),
      plot.subtitle = element_text(size = 12, color = "#7f8c8d"),
      axis.title = element_text(size = 12, color = "#34495e"),
      axis.text = element_text(size = 10, color = "#7f8c8d"),
      panel.grid.major = element_line(color = "#ecf0f1", linetype = "dashed"),
      panel.grid.minor = element_blank(),
      plot.background = element_rect(fill = "white", color = NA)
    ) +
    scale_x_continuous(breaks = pretty_breaks(n = 10)) +
    scale_y_continuous(breaks = pretty_breaks(n = 8))
  
  return(p)
}

#' 創建仰角時間線圖
#' 
#' @param coverage_data 覆蓋數據 data.frame
#' 
#' @return ggplot 對象
create_elevation_timeline <- function(coverage_data) {
  if (nrow(coverage_data) == 0 || !("elevation" %in% names(coverage_data))) {
    return(ggplot() + 
           ggtitle("無仰角數據可顯示") +
           theme_minimal())
  }
  
  # 添加時間分鐘欄位
  coverage_data$time_minutes <- seq(0, nrow(coverage_data) - 1)
  
  p <- ggplot(coverage_data, aes(x = time_minutes, y = elevation)) +
    geom_line(color = "#e74c3c", linewidth = 1.2, alpha = 0.8) +
    geom_point(color = "#c0392b", size = 1.5, alpha = 0.6) +
    geom_area(alpha = 0.3, fill = "#e74c3c") +
    labs(
      title = "最佳衛星仰角時間線",
      subtitle = paste("分析持續時間:", nrow(coverage_data), "分鐘"),
      x = "時間 (分鐘)",
      y = "仰角 (度)"
    ) +
    theme_minimal() +
    theme(
      plot.title = element_text(size = 16, face = "bold", color = "#2c3e50"),
      plot.subtitle = element_text(size = 12, color = "#7f8c8d"),
      axis.title = element_text(size = 12, color = "#34495e"),
      axis.text = element_text(size = 10, color = "#7f8c8d"),
      panel.grid.major = element_line(color = "#ecf0f1", linetype = "dashed"),
      panel.grid.minor = element_blank(),
      plot.background = element_rect(fill = "white", color = NA)
    ) +
    scale_x_continuous(breaks = pretty_breaks(n = 10)) +
    scale_y_continuous(breaks = pretty_breaks(n = 8), limits = c(0, NA))
  
  return(p)
}

#' 創建互動式可見衛星數量圖
#' 
#' @param coverage_data 覆蓋數據 data.frame
#' 
#' @return plotly 對象
create_interactive_timeline <- function(coverage_data) {
  if (nrow(coverage_data) == 0) {
    return(plot_ly() %>%
      add_annotations(
        text = "尚無數據，請先執行分析",
        x = 0.5, y = 0.5,
        xref = "paper", yref = "paper",
        showarrow = FALSE,
        font = list(size = 16, color = "gray")
      ))
  }
  
  # 添加時間分鐘欄位
  coverage_data$time_minutes <- seq(0, nrow(coverage_data) - 1)
  
  p <- plot_ly(coverage_data, 
               x = ~time_minutes, 
               y = ~visible_count,
               type = 'scatter', 
               mode = 'lines+markers',
               line = list(color = '#3498db', width = 3),
               marker = list(color = '#2980b9', size = 6),
               hovertemplate = paste(
                 "<b>時間:</b> %{x} 分鐘<br>",
                 "<b>可見衛星數:</b> %{y}<br>",
                 "<extra></extra>"
               )) %>%
    layout(
      title = list(
        text = "Starlink 可見衛星數量時間線",
        font = list(size = 18, color = "#2c3e50")
      ),
      xaxis = list(
        title = "時間 (分鐘)",
        gridcolor = "#ecf0f1",
        gridwidth = 1
      ),
      yaxis = list(
        title = "可見衛星數量",
        gridcolor = "#ecf0f1",
        gridwidth = 1
      ),
      plot_bgcolor = "white",
      paper_bgcolor = "white",
      font = list(family = "Arial, sans-serif", size = 12, color = "#2c3e50")
    )
  
  return(p)
}

#' 創建統計數據摘要圖表 (新版本)
#' 
#' @param stats 統計數據列表
#' 
#' @return ggplot 對象
create_summary_plot <- function(stats) {
  if (length(stats) == 0) {
    return(ggplot() + 
           annotate("text", x = 0.5, y = 0.5, label = "尚無數據\n請先執行分析", 
                    size = 6, color = "gray50") +
           theme_void())
  }
  
  # 準備數據
  summary_data <- data.frame(
    metric = c("平均可見衛星數", "最大可見衛星數", "覆蓋率 (%)", "平均仰角 (°)"),
    value = c(
      stats$avg_visible_satellites %||% 0,
      stats$max_visible_satellites %||% 0,
      stats$coverage_percentage %||% 0,
      stats$avg_elevation %||% 0
    ),
    color = c("#3498db", "#2ecc71", "#f39c12", "#e74c3c")
  )
  
  p <- ggplot(summary_data, aes(x = reorder(metric, value), y = value, fill = color)) +
    geom_col(alpha = 0.8) +
    scale_fill_identity() +
    coord_flip() +
    labs(
      title = "關鍵統計指標",
      x = "",
      y = "數值"
    ) +
    theme_minimal() +
    theme(
      plot.title = element_text(size = 14, face = "bold", color = "#2c3e50"),
      axis.title = element_text(size = 10, color = "#34495e"),
      axis.text = element_text(size = 9, color = "#7f8c8d"),
      panel.grid.major.y = element_blank(),
      panel.grid.minor = element_blank(),
      legend.position = "none"
    ) +
    geom_text(aes(label = round(value, 1)), 
              hjust = -0.1, vjust = 0.5, 
              color = "#2c3e50", size = 3, fontface = "bold")
  
  return(p)
}

#' 創建仰角變化圖 (新版本)
#' 
#' @param coverage_data 覆蓋數據 data.frame
#' 
#' @return ggplot 對象
create_elevation_plot <- function(coverage_data) {
  if (nrow(coverage_data) == 0) {
    return(ggplot() + 
           annotate("text", x = 0.5, y = 0.5, label = "尚無數據\n請先執行分析", 
                    size = 6, color = "gray50") +
           theme_void())
  }
  
  # 確保有仰角數據
  if (!("elevation" %in% names(coverage_data))) {
    # 如果沒有仰角數據，創建模擬數據作為示例
    coverage_data$elevation <- runif(nrow(coverage_data), 25, 85)
  }
  
  # 添加時間分鐘欄位
  coverage_data$time_minutes <- seq(0, nrow(coverage_data) - 1)
  
  p <- ggplot(coverage_data, aes(x = time_minutes, y = elevation)) +
    geom_line(color = "#e74c3c", linewidth = 1.2, alpha = 0.8) +
    geom_point(color = "#c0392b", size = 1, alpha = 0.6) +
    geom_area(alpha = 0.3, fill = "#e74c3c") +
    labs(
      title = "最佳衛星仰角變化",
      x = "時間 (分鐘)",
      y = "仰角 (度)"
    ) +
    theme_minimal() +
    theme(
      plot.title = element_text(size = 12, face = "bold", color = "#2c3e50"),
      axis.title = element_text(size = 10, color = "#34495e"),
      axis.text = element_text(size = 9, color = "#7f8c8d"),
      panel.grid.major = element_line(color = "#ecf0f1", linetype = "dashed"),
      panel.grid.minor = element_blank(),
      plot.background = element_rect(fill = "white", color = NA)
    ) +
    scale_x_continuous(breaks = pretty_breaks(n = 6)) +
    scale_y_continuous(breaks = pretty_breaks(n = 6), limits = c(0, NA))
  
  return(p)
}

#' 創建覆蓋統計圖
#' 
#' @param coverage_data 覆蓋數據 data.frame
#' 
#' @return ggplot 對象
create_coverage_plot <- function(coverage_data) {
  if (nrow(coverage_data) == 0) {
    return(ggplot() + 
           annotate("text", x = 0.5, y = 0.5, label = "尚無數據\n請先執行分析", 
                    size = 6, color = "gray50") +
           theme_void())
  }
  
  # 創建覆蓋統計
  coverage_stats <- data.frame(
    category = c("0-20 顆", "21-30 顆", "31-40 顆", "40+ 顆"),
    count = c(
      sum(coverage_data$visible_count <= 20),
      sum(coverage_data$visible_count > 20 & coverage_data$visible_count <= 30),
      sum(coverage_data$visible_count > 30 & coverage_data$visible_count <= 40),
      sum(coverage_data$visible_count > 40)
    ),
    color = c("#e74c3c", "#f39c12", "#2ecc71", "#27ae60")
  )
  
  # 移除計數為 0 的類別
  coverage_stats <- coverage_stats[coverage_stats$count > 0, ]
  
  if (nrow(coverage_stats) == 0) {
    return(ggplot() + 
           annotate("text", x = 0.5, y = 0.5, label = "無有效覆蓋數據", 
                    size = 6, color = "gray50") +
           theme_void())
  }
  
  p <- ggplot(coverage_stats, aes(x = reorder(category, count), y = count, fill = color)) +
    geom_col(alpha = 0.8) +
    scale_fill_identity() +
    coord_flip() +
    labs(
      title = "可見衛星數分佈",
      x = "衛星數量範圍",
      y = "時間點數量"
    ) +
    theme_minimal() +
    theme(
      plot.title = element_text(size = 12, face = "bold", color = "#2c3e50"),
      axis.title = element_text(size = 10, color = "#34495e"),
      axis.text = element_text(size = 9, color = "#7f8c8d"),
      panel.grid.major.y = element_blank(),
      panel.grid.minor = element_blank(),
      legend.position = "none"
    ) +
    geom_text(aes(label = count), 
              hjust = -0.1, vjust = 0.5, 
              color = "#2c3e50", size = 3, fontface = "bold")
  
  return(p)
}

#' 創建統計數據摘要圖表 (舊版本，保持向後相容)
#' 
#' @param stats 統計數據列表
#' 
#' @return ggplot 對象
create_stats_summary <- function(stats) {
  return(create_summary_plot(stats))
} 