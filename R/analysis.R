# R/analysis.R
# Starlink 分析 R 模組
# 使用 reticulate 調用 Python 分析功能

library(reticulate)
library(jsonlite)

# 隱藏所有訊息的輔助函數
quiet <- function(x) { 
  sink(nullfile())
  on.exit(sink()) 
  invisible(force(x)) 
}

# 簡化的 Python 環境配置
python_configured <- FALSE

tryCatch({
  # 直接使用系統 Python
  python_paths <- c(
    "/home/lean/miniconda3/bin/python",
    "/usr/bin/python3",
    Sys.which("python3"),
    Sys.which("python")
  )
  
  for (py_path in python_paths) {
    if (file.exists(py_path) && !python_configured) {
      tryCatch({
        quiet(use_python(py_path, required = FALSE))
        
        # 簡單測試 pandas 是否可用
        if (py_module_available("pandas")) {
          python_configured <- TRUE
          break
        }
      }, error = function(e) {
        # 靜默處理
      })
    }
  }
  
  # 如果成功配置，嘗試載入 Python 模組
  if (python_configured) {
    tryCatch({
      # 檢查分析文件是否存在
      if (file.exists("satellite_analysis.py")) {
        quiet(source_python("satellite_analysis.py"))
      }
    }, error = function(e) {
      python_configured <- FALSE
    })
  }
}, error = function(e) {
  python_configured <- FALSE
})

# 如果配置失敗，設置為 FALSE
if (!exists("python_configured")) {
  python_configured <- FALSE
}

#' 執行 Starlink 衛星分析
#' 
#' @param lat 緯度
#' @param lon 經度  
#' @param interval_minutes 時間間隔（分鐘）
#' @param analysis_duration_minutes 分析持續時間（分鐘）
#' @param min_elevation_threshold 最小仰角閾值（度）
#' @param output_dir 輸出目錄
#' 
#' @return 包含分析結果檔案路徑的列表
run_analysis <- function(lat = 25.0330, 
                        lon = 121.5654, 
                        interval_minutes = 1.0,
                        analysis_duration_minutes = 60,
                        min_elevation_threshold = 25,
                        output_dir = "output") {
  
  if (!python_configured) {
    return(list(
      stats_path = NULL,
      report_path = NULL,
      data_path = NULL,
      plots_paths = list()
    ))
  }
  
  tryCatch({
    # 檢查 StarlinkAnalysis 是否可用
    if (!exists("StarlinkAnalysis")) {
      return(list(
        stats_path = NULL,
        report_path = NULL,
        data_path = NULL,
        plots_paths = list()
      ))
    }
    
    # 調用 Python 分析函數
    result <- quiet(StarlinkAnalysis$analyze(
      lat = lat,
      lon = lon, 
      interval_minutes = interval_minutes,
      analysis_duration_minutes = analysis_duration_minutes,
      min_elevation_threshold = min_elevation_threshold,
      output_dir = output_dir
    ))
    
    return(result)
    
  }, error = function(e) {
    return(list(
      stats_path = NULL,
      report_path = NULL,
      data_path = NULL,
      plots_paths = list()
    ))
  })
}

#' 讀取分析統計數據
#' 
#' @param stats_path 統計數據 JSON 檔案路徑
#' 
#' @return 統計數據列表
read_analysis_stats <- function(stats_path) {
  if (is.null(stats_path) || !file.exists(stats_path)) {
    return(list(
      avg_visible_satellites = 0,
      max_visible_satellites = 0,
      min_visible_satellites = 0,
      coverage_percentage = 0,
      avg_elevation = 0,
      max_elevation = 0,
      analysis_duration_minutes = 0,
      observer_lat = 25.0330,
      observer_lon = 121.5654
    ))
  }
  
  tryCatch({
    fromJSON(stats_path)
  }, error = function(e) {
    return(list())
  })
}

#' 讀取覆蓋數據
#' 
#' @param data_path 覆蓋數據 CSV 檔案路徑
#' 
#' @return 覆蓋數據 data.frame
read_coverage_data <- function(data_path) {
  if (is.null(data_path) || !file.exists(data_path)) {
    return(data.frame())
  }
  
  tryCatch({
    read.csv(data_path, stringsAsFactors = FALSE)
  }, error = function(e) {
    return(data.frame())
  })
}

#' 檢查分析結果檔案是否存在
#' 
#' @param output_dir 輸出目錄
#' 
#' @return 布林值，表示是否有現有結果
has_existing_results <- function(output_dir = "output") {
  stats_file <- file.path(output_dir, "coverage_stats.json")
  data_file <- file.path(output_dir, "coverage_data.csv")
  
  return(file.exists(stats_file) && file.exists(data_file))
}

#' 載入現有分析結果
#' 
#' @param output_dir 輸出目錄
#' 
#' @return 包含統計數據和覆蓋數據的列表
load_existing_results <- function(output_dir = "output") {
  stats_path <- file.path(output_dir, "coverage_stats.json")
  data_path <- file.path(output_dir, "coverage_data.csv")
  report_path <- file.path(output_dir, "coverage_report.html")
  
  list(
    stats = read_analysis_stats(stats_path),
    data = read_coverage_data(data_path),
    stats_path = if(file.exists(stats_path)) stats_path else NULL,
    data_path = if(file.exists(data_path)) data_path else NULL,
    report_path = if(file.exists(report_path)) report_path else NULL
  )
} 