#!/usr/bin/env Rscript
# plot_timeline.R - 繪製衛星覆蓋和Handover時間線圖

#' 繪製衛星覆蓋和Handover時間線圖
#'
#' @param visible_data 衛星可見性數據
#' @param handover_data Handover分析結果
#' @return 時間線圖列表
plot_timeline <- function(visible_data, handover_data) {
  library(ggplot2)
  library(dplyr)
  library(lubridate)
  library(scales)
  library(gridExtra)
  library(survival)
  
  # 確保時間列為datetime格式
  if (is.character(visible_data$time)) {
    visible_data$time <- as.POSIXct(visible_data$time)
  }
  
  # 計算每個時間點的可見衛星數量
  satellite_count <- visible_data %>%
    group_by(time) %>%
    summarise(visible_count = n(), .groups = 'drop')
  
  # 獲取最佳衛星(仰角最高)數據
  best_satellites <- handover_data$best_satellites
  
  # 獲取handover事件
  handovers <- handover_data$handovers
  
  # 圖1: 可見衛星數量時間線
  p1 <- ggplot(satellite_count, aes(x = time, y = visible_count)) +
    geom_step(color = "#3498db", size = 1) +
    labs(title = "24小時內可見Starlink衛星數量",
         x = "時間 (UTC)",
         y = "可見衛星數量") +
    theme_minimal() +
    theme(plot.title = element_text(hjust = 0.5, face = "bold"),
          axis.text = element_text(size = 10),
          axis.title = element_text(size = 12),
          legend.position = "bottom") +
    scale_x_datetime(labels = date_format("%H:%M", tz = "UTC"))
  
  # 圖2: 最佳衛星仰角時間線，並標記handover事件
  p2 <- ggplot() +
    geom_step(data = best_satellites, aes(x = time, y = elev), color = "#2ecc71", size = 1) +
    geom_vline(data = handovers, aes(xintercept = as.numeric(time)), 
               color = "#e74c3c", linetype = "dashed", alpha = 0.5) +
    labs(title = "最佳衛星仰角與Handover時間線",
         subtitle = "紅色虛線表示衛星切換(Handover)事件",
         x = "時間 (UTC)",
         y = "仰角 (度)") +
    theme_minimal() +
    theme(plot.title = element_text(hjust = 0.5, face = "bold"),
          plot.subtitle = element_text(hjust = 0.5),
          axis.text = element_text(size = 10),
          axis.title = element_text(size = 12),
          legend.position = "bottom") +
    scale_x_datetime(labels = date_format("%H:%M", tz = "UTC"))
  
  # 圖3: Handover間隔的Kaplan-Meier生存曲線
  surv_data <- handover_data$survival_data
  km_fit <- handover_data$km_fit
  
  # 準備生存曲線的數據框
  surv_df <- data.frame(
    time = km_fit$time,
    surv = km_fit$surv,
    upper = km_fit$upper,
    lower = km_fit$lower
  )
  
  p3 <- ggplot(surv_df, aes(x = time, y = 1-surv)) +
    geom_step(size = 1, color = "#9b59b6") +
    geom_ribbon(aes(ymin = 1-upper, ymax = 1-lower), alpha = 0.2, fill = "#9b59b6") +
    labs(title = "Handover間隔累積分布函數(CDF)",
         x = "間隔時間 (分鐘)",
         y = "累積機率") +
    theme_minimal() +
    theme(plot.title = element_text(hjust = 0.5, face = "bold"),
          axis.text = element_text(size = 10),
          axis.title = element_text(size = 12))
  
  # 圖4: 不同因素下的Kaplan-Meier曲線
  # 依仰角分組
  km_elev <- handover_data$km_fit_by_elev
  
  # 轉換為數據框
  surv_elev_df <- data.frame(
    time = rep(km_elev$time, length(km_elev$strata)),
    surv = km_elev$surv,
    strata = rep(names(km_elev$strata), km_elev$strata)
  )
  
  # 提取層名
  surv_elev_df$elev_group <- gsub("elev_group=", "", surv_elev_df$strata)
  
  p4 <- ggplot(surv_elev_df, aes(x = time, y = 1-surv, color = elev_group)) +
    geom_step(size = 1) +
    labs(title = "不同仰角下的Handover間隔CDF",
         x = "間隔時間 (分鐘)",
         y = "累積機率",
         color = "仰角範圍") +
    theme_minimal() +
    theme(plot.title = element_text(hjust = 0.5, face = "bold"),
          axis.text = element_text(size = 10),
          axis.title = element_text(size = 12),
          legend.position = "bottom") +
    scale_color_brewer(palette = "Set1")
  
  # 綜合圖表
  combined_plot <- grid.arrange(p1, p2, p3, p4, ncol = 2)
  
  # 保存所有圖表
  result <- list(
    satellite_count_plot = p1,
    best_elevation_plot = p2,
    survival_plot = p3,
    survival_by_elev_plot = p4,
    combined_plot = combined_plot
  )
  
  return(result)
}

# 如果從命令行直接執行此文件
if (sys.nframe() == 0) {
  args <- commandArgs(trailingOnly = TRUE)
  if (length(args) >= 2) {
    # 從CSV文件讀取數據
    visible_data <- readr::read_csv(args[1])
    
    # 計算handover
    source("R/compute_handover.R")
    handover_data <- compute_handover(visible_data)
    
    # 繪製圖表
    plots <- plot_timeline(visible_data, handover_data)
    
    # 保存圖表
    output_dir <- ifelse(length(args) >= 3, args[3], "output")
    if (!dir.exists(output_dir)) {
      dir.create(output_dir, recursive = TRUE)
    }
    
    ggsave(file.path(output_dir, "satellite_count.png"), plots$satellite_count_plot, width = 10, height = 6)
    ggsave(file.path(output_dir, "best_elevation.png"), plots$best_elevation_plot, width = 10, height = 6)
    ggsave(file.path(output_dir, "survival_curve.png"), plots$survival_plot, width = 10, height = 6)
    ggsave(file.path(output_dir, "survival_by_elev.png"), plots$survival_by_elev_plot, width = 10, height = 6)
    ggsave(file.path(output_dir, "combined_plots.png"), plots$combined_plot, width = 14, height = 10)
    
    cat("圖表已保存至:", output_dir, "\n")
  }
}

# 返回函數作為targets調用函數
plot_timeline 