#!/usr/bin/env Rscript
# compute_handover.R - 計算衛星切換(handover)及延遲分析

#' 計算衛星handover並建立生存分析模型
#'
#' @param visible_tbl 衛星可見度數據框架
#' @return 包含handover分析結果的列表
compute_handover <- function(visible_tbl) {
  # 確認輸入是否為tibble或data.frame
  if (!is.data.frame(visible_tbl)) {
    stop("輸入必須是data.frame或tibble格式")
  }
  
  library(dplyr)
  library(tidyr)
  library(survival)
  library(lubridate)
  
  # 確保時間列為datetime格式
  if (is.character(visible_tbl$time)) {
    visible_tbl$time <- as.POSIXct(visible_tbl$time)
  }
  
  message("開始計算衛星handover...")
  
  # 依時間分組，找出每個時間點最佳衛星(仰角最高)
  best_satellites <- visible_tbl %>%
    group_by(time) %>%
    slice_max(elev) %>%
    ungroup() %>%
    arrange(time)
  
  # 計算handover事件
  handovers <- best_satellites %>%
    mutate(next_satellite = lead(satellite),
           next_time = lead(time)) %>%
    filter(satellite != next_satellite & !is.na(next_satellite)) %>%
    select(time, from = satellite, to = next_satellite, 
           from_elev = elev, to_elev = lead(elev), 
           direction, rain)
  
  # 計算每個handover間的時間間隔(分鐘)
  handovers <- handovers %>%
    mutate(next_time = lead(time),
           duration_minutes = as.numeric(difftime(next_time, time, units = "mins"))) %>%
    filter(!is.na(duration_minutes))
  
  # 為每個handover事件創建ID
  handovers <- handovers %>%
    mutate(handover_id = row_number())
  
  # 計算基本統計數據
  stats <- list(
    total_satellites = length(unique(visible_tbl$satellite)),
    total_handovers = nrow(handovers),
    avg_handover_interval_minutes = mean(handovers$duration_minutes, na.rm = TRUE),
    median_handover_interval_minutes = median(handovers$duration_minutes, na.rm = TRUE)
  )
  
  # 創建生存分析數據
  survival_data <- handovers %>%
    mutate(
      status = 1,  # 所有事件都是完整觀察到的
      elev_group = cut(from_elev, breaks = c(0, 30, 45, 60, 90), 
                        labels = c("低(0-30°)", "中(30-45°)", "高(45-60°)", "非常高(60-90°)")),
      rain_factor = factor(rain, levels = c(0, 1), labels = c("無雨", "有雨"))
    )
  
  # 建立Cox比例風險模型
  cox_model <- survival::coxph(
    Surv(duration_minutes, status) ~ from_elev + direction + rain_factor,
    data = survival_data
  )
  
  # 建立Kaplan-Meier生存曲線
  kmfit <- survival::survfit(Surv(duration_minutes, status) ~ 1, data = survival_data)
  kmfit_by_elev <- survival::survfit(Surv(duration_minutes, status) ~ elev_group, data = survival_data)
  kmfit_by_rain <- survival::survfit(Surv(duration_minutes, status) ~ rain_factor, data = survival_data)
  
  # 回傳結果列表
  return(list(
    best_satellites = best_satellites,
    handovers = handovers,
    stats = stats,
    cox_model = cox_model,
    km_fit = kmfit,
    km_fit_by_elev = kmfit_by_elev,
    km_fit_by_rain = kmfit_by_rain,
    survival_data = survival_data
  ))
}

# 如果從命令行直接執行此文件，則使用命令行參數
if (sys.nframe() == 0) {
  args <- commandArgs(trailingOnly = TRUE)
  if (length(args) > 0) {
    # 從CSV文件讀取數據
    visible_tbl <- readr::read_csv(args[1])
    result <- compute_handover(visible_tbl)
    
    # 輸出一些統計結果
    cat("===== 衛星Handover分析結果 =====\n")
    cat("總衛星數:", result$stats$total_satellites, "\n")
    cat("總handover次數:", result$stats$total_handovers, "\n")
    cat("平均handover間隔(分鐘):", round(result$stats$avg_handover_interval_minutes, 2), "\n")
    cat("Cox模型摘要:\n")
    print(summary(result$cox_model))
  }
}

# 返回函數作為targets的調用函數
compute_handover 