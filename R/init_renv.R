#!/usr/bin/env Rscript
# init_renv.R - 初始化R項目環境

# 檢查套件是否可用，如果不可用則提醒用戶使用conda安裝
check_packages <- function() {
  # 所需套件列表
  pkgs <- c(
    "tidyverse", "dplyr", "ggplot2", "lubridate",
    "reticulate", "sf", "leaflet", "leaflet.extras",
    "shiny", "shinydashboard", "survival", "plotly", "knitr", "kableExtra",
    "gridExtra", "rmarkdown", "htmltools", "DT", "scales",
    "renv", "targets", "jsonlite", "htmlwidgets", "quarto",
    "curl", "httr", "xml2", "pak"
  )
  
  # 檢查每個套件
  missing_pkgs <- c()
  for (pkg in pkgs) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      missing_pkgs <- c(missing_pkgs, pkg)
    } else {
      cat(pkg, "已安裝\n")
    }
  }
  
  # 如果有缺失的套件，提示用戶使用conda安裝
  if (length(missing_pkgs) > 0) {
    missing_str <- paste(missing_pkgs, collapse = " r-")
    cat("以下套件未安裝:", paste(missing_pkgs, collapse = ", "), "\n")
    cat("請使用conda安裝這些套件:\n")
    cat("conda install -y -c conda-forge r-", missing_str, "\n", sep = "")
    
    # 避免嘗試使用install.packages()，直接停止
    stop("缺少必要套件，請通過conda安裝後再試。不建議使用install.packages()，因為可能導致與conda環境的C庫衝突")
  }
}

# 初始化renv (如果已安裝)
init_renv <- function() {
  if (requireNamespace("renv", quietly = TRUE)) {
    cat("初始化renv環境...\n")
    # 如果專案目錄沒有renv初始化，則初始化它
    if (!file.exists("renv.lock")) {
      renv::init(bare = TRUE)
    }
    
    # 使用已安裝的套件更新renv snapshot
    cat("從已安裝的套件更新renv.lock...\n")
    renv::snapshot(confirm = FALSE)
  } else {
    cat("renv套件未安裝，跳過renv初始化\n")
  }
}

# 配置targets腳本
setup_targets <- function() {
  if (!requireNamespace("targets", quietly = TRUE)) {
    cat("targets套件未安裝，無法設定targets腳本\n")
    return()
  }
  
  cat("設定targets腳本...\n")
  targets::tar_script({
    library(targets)
    library(tidyverse)
    library(reticulate)
    library(sf)
    library(leaflet)
    
    # 設定 Python 環境
    use_condaenv("starlink-env", required = TRUE)
    
    # 導入 Python 套件
    py_run_string("from skyfield.api import load, wgs84")
    
    # 設定目標
    list(
      # 資料來源
      tar_target(tle_url, "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle", format = "url"),
      tar_target(tle_raw, readLines(tle_url)),
      tar_target(gs_url, "https://satellitemap.space/data/ground_stations.json", format = "url"),
      tar_target(gs_json, jsonlite::fromJSON(gs_url, simplifyVector = TRUE)),
      
      # 台北市座標設定
      tar_target(taipei_coords, list(lat = 25.0330, lon = 121.5654, elevation = 10.0)),
      
      # Python 可見度分析
      tar_target(visibility_py, source_python("py/visibility.py")),
      tar_target(visible_data, 
                 compute_visibility(tle_raw, 
                                   taipei_coords$lat, 
                                   taipei_coords$lon, 
                                   taipei_coords$elevation, 
                                   interval_minutes = 1,
                                   duration_hours = 24)),
      
      # Handover 分析
      tar_target(handover_data, source_file("R/compute_handover.R")(visible_data)),
      
      # 視覺化
      tar_target(fig_timeline, source_file("R/plot_timeline.R")(visible_data, handover_data)),
      tar_target(fig_heatmap, source_file("R/plot_heatmap.R")(visible_data)),
      
      # 報告生成
      tar_target(report_data, list(
        visible_data = visible_data,
        handover_data = handover_data,
        fig_timeline = fig_timeline,
        fig_heatmap = fig_heatmap
      )),
      tar_target(report, rmarkdown::render("Rmd/report.qmd", 
                                         params = list(data = report_data),
                                         output_file = "../output/starlink_analysis_report.html"))
    )
  })
}

# 主函數
main <- function() {
  cat("檢查必要套件...\n")
  check_packages()
  
  # 初始化renv
  init_renv()
  
  # 設定targets
  setup_targets()
  
  cat("R環境初始化完成!\n")
  cat("接下來使用 targets::tar_make() 執行分析流程\n")
}

# 執行主函數
main() 