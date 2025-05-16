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