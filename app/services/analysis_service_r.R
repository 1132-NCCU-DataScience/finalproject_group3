#!/usr/bin/env Rscript
#' Starlink Analysis Service - R Implementation
#' 
#' @description 
#' R implementation of statistical analysis and visualization functions
#' for Starlink satellite coverage analysis in Taipei region.
#' 
#' @details
#' This module provides R-based data analysis capabilities to replace
#' Python pandas/numpy computations with tidyverse ecosystem.
#' 
#' @author Lean Li
#' @version 1.0
#' @export

# Required libraries
suppressPackageStartupMessages({
  library(tidyverse)
  library(lubridate)
  library(jsonlite)
  library(plotly)
  library(ggplot2)
  library(scales)
  library(DT)
  library(htmlwidgets)
  library(RColorBrewer)
  library(rmarkdown)
  library(knitr)
})

# Constants for Taipei location
TAIPEI_LAT <- 25.0330
TAIPEI_LON <- 121.5654
ELEVATION_M <- 10.0

#' Calculate Statistics from Coverage Data
#' 
#' @description 
#' Calculate comprehensive statistics from satellite coverage data
#' 
#' @param coverage_df data.frame containing coverage data with columns:
#'   - visible_count: number of visible satellites
#'   - elevation: maximum elevation angle
#'   - timestamp: time of observation
#' @return list containing calculated statistics
#' @export
calculate_stats_r <- function(coverage_df) {
  tryCatch({
    # Validate input data
    if (is.null(coverage_df) || nrow(coverage_df) == 0) {
      warning("Empty or NULL coverage data provided")
      return(default_stats())
    }
    
    # Check for required columns and handle missing data
    count_column <- NULL
    
    if ("visible_count" %in% names(coverage_df)) {
      count_column <- "visible_count"
    } else if ("visible_satellites" %in% names(coverage_df)) {
      message("Warning: Using visible_satellites column, parsing satellite count...")
      coverage_df <- coverage_df %>%
        mutate(visible_count = map_dbl(visible_satellites, count_satellites_from_string))
      count_column <- "visible_count"
    } else {
      stop("No visible satellite count data found")
    }
    
    # Calculate basic statistics using tidyverse
    basic_stats <- coverage_df %>%
      summarise(
        avg_visible_satellites = mean(.data[[count_column]], na.rm = TRUE),
        max_visible_satellites = max(.data[[count_column]], na.rm = TRUE),
        min_visible_satellites = min(.data[[count_column]], na.rm = TRUE),
        coverage_percentage = mean(.data[[count_column]] > 0, na.rm = TRUE) * 100,
        .groups = "drop"
      )
    
    # Calculate elevation statistics if available
    elevation_stats <- list(
      avg_elevation = 0,
      max_elevation = 0
    )
    
    if ("elevation" %in% names(coverage_df) && 
        any(!is.na(coverage_df$elevation))) {
      elevation_stats <- coverage_df %>%
        filter(!is.na(elevation)) %>%
        summarise(
          avg_elevation = mean(elevation, na.rm = TRUE),
          max_elevation = max(elevation, na.rm = TRUE),
          .groups = "drop"
        ) %>%
        as.list()
    }
    
    # Combine all statistics
    stats <- c(as.list(basic_stats), elevation_stats)
    
    # Add analysis metadata
    stats$analysis_duration_minutes <- nrow(coverage_df)
    stats$last_updated_time <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
    
    return(stats)
    
  }, error = function(e) {
    warning(paste("Error calculating statistics:", e$message))
    return(default_stats())
  })
}

#' Count Satellites from String Representation
#' 
#' @description 
#' Parse satellite count from string representation of satellite data
#' 
#' @param sat_string character string containing satellite data
#' @return numeric count of satellites
#' @keywords internal
count_satellites_from_string <- function(sat_string) {
  if (is.na(sat_string) || sat_string == "" || is.null(sat_string)) {
    return(0)
  }
  
  tryCatch({
    # Count occurrences of 'name': in the string
    if (str_detect(sat_string, "^\\[.*\\]$")) {
      return(str_count(sat_string, "'name':"))
    }
    return(0)
  }, error = function(e) {
    return(0)
  })
}

#' Default Statistics Template
#' 
#' @description 
#' Returns default statistics structure when calculation fails
#' 
#' @return list with default values
#' @keywords internal
default_stats <- function() {
  list(
    avg_visible_satellites = 0,
    max_visible_satellites = 0,
    min_visible_satellites = 0,
    coverage_percentage = 0,
    avg_elevation = 0,
    max_elevation = 0,
    analysis_duration_minutes = 0,
    last_updated_time = format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  )
}

#' Generate Visualization Plots
#' 
#' @description 
#' Generate timeline plots for satellite visibility and elevation
#' 
#' @param coverage_df data.frame containing coverage data
#' @param output_dir character path to output directory
#' @return logical indicating success
#' @export
generate_visualizations_r <- function(coverage_df, output_dir = "output") {
  tryCatch({
    # Ensure output directory exists
    if (!dir.exists(output_dir)) {
      dir.create(output_dir, recursive = TRUE)
    }
    
    # Validate input data
    if (is.null(coverage_df) || nrow(coverage_df) == 0) {
      generate_empty_plots(output_dir)
      return(FALSE)
    }
    
    # Prepare data for plotting
    plot_data <- coverage_df %>%
      mutate(
        time_index = row_number(),
        time_minutes = (row_number() - 1)
      )
    
    # Generate visible satellites timeline
    generate_satellites_timeline(plot_data, output_dir)
    
    # Generate elevation timeline
    generate_elevation_timeline(plot_data, output_dir)
    
    # Generate coverage heatmap
    generate_coverage_heatmap(plot_data, output_dir)
    
    message("✅ All visualizations generated successfully")
    return(TRUE)
    
  }, error = function(e) {
    warning(paste("Error generating visualizations:", e$message))
    generate_empty_plots(output_dir)
    return(FALSE)
  })
}

#' Generate Visible Satellites Timeline Plot
#' 
#' @description 
#' Create timeline plot showing number of visible satellites over time
#' 
#' @param plot_data data.frame prepared plot data
#' @param output_dir character output directory path
#' @keywords internal
generate_satellites_timeline <- function(plot_data, output_dir) {
  # Determine count column
  count_col <- if ("visible_count" %in% names(plot_data)) {
    "visible_count"
  } else if ("visible_satellites" %in% names(plot_data)) {
    plot_data <- plot_data %>%
      mutate(visible_count = map_dbl(visible_satellites, count_satellites_from_string))
    "visible_count"
  } else {
    return(generate_empty_satellite_plot(output_dir))
  }
  
  # Create the plot using ggplot2
  p <- plot_data %>%
    ggplot(aes(x = time_minutes, y = .data[[count_col]])) +
    geom_line(color = "#3498db", size = 1.2, alpha = 0.8) +
    geom_point(color = "#2980b9", size = 1.5, alpha = 0.6) +
    labs(
      title = "Visible Starlink Satellites in Taipei",
      subtitle = paste("Analysis Duration:", nrow(plot_data), "minutes"),
      x = "Time (minutes)",
      y = "Number of Visible Satellites"
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
  
  # Save the plot
  output_path <- file.path(output_dir, "visible_satellites_timeline.png")
  ggsave(output_path, plot = p, width = 12, height = 6, dpi = 300, bg = "white")
  
  message(paste("✅ Satellites timeline saved to:", output_path))
}

#' Generate Elevation Timeline Plot
#' 
#' @description 
#' Create timeline plot showing maximum elevation angle over time
#' 
#' @param plot_data data.frame prepared plot data
#' @param output_dir character output directory path
#' @keywords internal
generate_elevation_timeline <- function(plot_data, output_dir) {
  if (!"elevation" %in% names(plot_data) || all(is.na(plot_data$elevation))) {
    return(generate_empty_elevation_plot(output_dir))
  }
  
  # Create the plot
  p <- plot_data %>%
    filter(!is.na(elevation)) %>%
    ggplot(aes(x = time_minutes, y = elevation)) +
    geom_line(color = "#e74c3c", size = 1.2, alpha = 0.8) +
    geom_point(color = "#c0392b", size = 1.5, alpha = 0.6) +
    labs(
      title = "Maximum Satellite Elevation Over Time",
      subtitle = paste("Analysis Duration:", nrow(plot_data), "minutes"),
      x = "Time (minutes)",
      y = "Maximum Elevation (degrees)"
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
    scale_y_continuous(breaks = pretty_breaks(n = 8), limits = c(0, 90))
  
  # Save the plot
  output_path <- file.path(output_dir, "elevation_timeline.png")
  ggsave(output_path, plot = p, width = 12, height = 6, dpi = 300, bg = "white")
  
  message(paste("✅ Elevation timeline saved to:", output_path))
}

#' Generate Coverage Heatmap
#' 
#' @description 
#' Create interactive heatmap showing satellite coverage over time
#' 
#' @param plot_data data.frame prepared plot data
#' @param output_dir character output directory path
#' @keywords internal
generate_coverage_heatmap <- function(plot_data, output_dir) {
  tryCatch({
    # Determine count column
    count_col <- if ("visible_count" %in% names(plot_data)) {
      "visible_count"
    } else if ("visible_satellites" %in% names(plot_data)) {
      plot_data <- plot_data %>%
        mutate(visible_count = map_dbl(visible_satellites, count_satellites_from_string))
      "visible_count"
    } else {
      stop("No count data available")
    }
    
    # Calculate analysis duration
    duration_minutes <- nrow(plot_data)
    hours <- duration_minutes %/% 60
    minutes <- duration_minutes %% 60
    
    if (hours == 0) {
      # For analysis less than 1 hour, create minute-based heatmap
      heatmap_data <- plot_data %>%
        mutate(
          hour_group = "00:00",
          minute = sprintf("%02d", time_minutes)
        ) %>%
        select(hour_group, minute, count = all_of(count_col))
      
      # Create plotly heatmap
      p <- plot_ly(
        data = heatmap_data,
        x = ~minute,
        y = ~hour_group,
        z = ~count,
        type = "heatmap",
        colorscale = "Viridis",
        hovertemplate = "Time: %{y}:%{x}<br>Visible Satellites: %{z}<extra></extra>"
      ) %>%
        layout(
          title = paste("Satellite Coverage Heatmap (", minutes, " minutes analysis)"),
          xaxis = list(title = "Minutes"),
          yaxis = list(title = ""),
          font = list(family = "Arial", size = 12)
        )
      
    } else {
      # For longer analysis, create hour-minute based heatmap
      heatmap_data <- plot_data %>%
        mutate(
          hour = time_minutes %/% 60,
          minute = time_minutes %% 60,
          hour_label = sprintf("%02d:00", hour)
        ) %>%
        select(hour_label, minute, count = all_of(count_col))
      
      # Create matrix for heatmap
      heatmap_matrix <- heatmap_data %>%
        complete(hour_label, minute = 0:59, fill = list(count = 0)) %>%
        arrange(hour_label, minute) %>%
        pivot_wider(names_from = minute, values_from = count, values_fill = 0) %>%
        column_to_rownames("hour_label") %>%
        as.matrix()
      
      # Create plotly heatmap
      p <- plot_ly(
        z = ~heatmap_matrix,
        x = ~colnames(heatmap_matrix),
        y = ~rownames(heatmap_matrix),
        type = "heatmap",
        colorscale = "Viridis",
        hovertemplate = "Time: %{y}:%{x}<br>Visible Satellites: %{z}<extra></extra>"
      ) %>%
        layout(
          title = paste("Satellite Coverage Heatmap (", hours, "h", minutes, "m analysis)"),
          xaxis = list(title = "Minutes"),
          yaxis = list(title = "Hours"),
          font = list(family = "Arial", size = 12),
          height = 800
        )
    }
    
    # Save interactive heatmap
    output_path <- file.path(output_dir, "coverage_heatmap.html")
    htmlwidgets::saveWidget(p, output_path, selfcontained = TRUE)
    
    message(paste("✅ Coverage heatmap saved to:", output_path))
    
  }, error = function(e) {
    warning(paste("Error generating heatmap:", e$message))
    generate_empty_heatmap(output_dir)
  })
}

#' Generate Empty Plots for Error Cases
#' 
#' @description 
#' Generate placeholder plots when data is unavailable
#' 
#' @param output_dir character output directory path
#' @keywords internal
generate_empty_plots <- function(output_dir) {
  generate_empty_satellite_plot(output_dir)
  generate_empty_elevation_plot(output_dir)
  generate_empty_heatmap(output_dir)
}

#' Generate Empty Satellite Plot
#' @keywords internal
generate_empty_satellite_plot <- function(output_dir) {
  p <- ggplot() +
    annotate("text", x = 0.5, y = 0.5, label = "No satellite data available", 
             size = 6, color = "#7f8c8d") +
    labs(title = "Visible Starlink Satellites in Taipei (No Data)",
         x = "Time (minutes)", y = "Number of Visible Satellites") +
    theme_void() +
    theme(plot.title = element_text(hjust = 0.5, size = 16))
  
  ggsave(file.path(output_dir, "visible_satellites_timeline.png"), 
         plot = p, width = 12, height = 6, dpi = 300, bg = "white")
}

#' Generate Empty Elevation Plot
#' @keywords internal
generate_empty_elevation_plot <- function(output_dir) {
  p <- ggplot() +
    annotate("text", x = 0.5, y = 0.5, label = "No elevation data available", 
             size = 6, color = "#7f8c8d") +
    labs(title = "Maximum Satellite Elevation Over Time (No Data)",
         x = "Time (minutes)", y = "Maximum Elevation (degrees)") +
    theme_void() +
    theme(plot.title = element_text(hjust = 0.5, size = 16))
  
  ggsave(file.path(output_dir, "elevation_timeline.png"), 
         plot = p, width = 12, height = 6, dpi = 300, bg = "white")
}

#' Generate Empty Heatmap
#' @keywords internal
generate_empty_heatmap <- function(output_dir) {
  p <- plot_ly() %>%
    add_annotations(
      text = "No data available for heatmap",
      x = 0.5, y = 0.5,
      showarrow = FALSE,
      font = list(size = 20, color = "#7f8c8d")
    ) %>%
    layout(
      title = "Satellite Coverage Heatmap (No Data)",
      xaxis = list(visible = FALSE),
      yaxis = list(visible = FALSE)
    )
  
  htmlwidgets::saveWidget(p, file.path(output_dir, "coverage_heatmap.html"), 
                         selfcontained = TRUE)
}

#' Generate HTML Report using R Markdown
#' 
#' @description 
#' Render an R Markdown template to produce a detailed HTML report.
#' 
#' @param data_dir character path to the directory containing input data files (stats, coverage, plots)
#' @param output_dir character path to output directory for the report
#' @param rmd_template_path character path to the R Markdown template file
#' @param output_filename character name for the output HTML report file
#' @return logical indicating success
#' @export
generate_html_report_r <- function(data_dir, 
                                   output_dir = "output", 
                                   rmd_template_path = "app/services/report_template.Rmd", 
                                   output_filename = "report_r.html") {
  tryCatch({
    message(paste("📝 Generating R Markdown HTML report using template:", rmd_template_path))
    
    # 確保輸出目錄存在
    if (!dir.exists(output_dir)) {
      dir.create(output_dir, recursive = TRUE)
    }
    
    # 檢查 Rmd 模板檔案是否存在
    if (!file.exists(rmd_template_path)) {
      stop(paste("R Markdown template file not found:", rmd_template_path))
    }
    
    # 將 data_dir 轉換為絕對路徑，以確保 R Markdown 能正確找到它
    # data_dir 參數是從 analyze_coverage_data_r 傳入的，原始值是 Python 的 output_dir (app.static_folder)
    # 如果 data_dir 已經是絕對路徑，normalizePath 不會改變它
    # 如果它是相對路徑 (例如 "app/static")，normalizePath 會將其轉換為基於當前 R 工作目錄的絕對路徑
    absolute_data_dir <- normalizePath(data_dir, mustWork = FALSE) 
    message(paste("Normalized absolute_data_dir for RMD params:", absolute_data_dir))
    # 同時也檢查一下 Rmd 模板本身的路徑是否正確
    absolute_rmd_template_path <- normalizePath(rmd_template_path, mustWork = TRUE) # 模板必須存在
    message(paste("Absolute RMD template path for render input:", absolute_rmd_template_path))

    # 新增對 rmd 模板路徑的詳細檢查
    message(paste("Class of absolute_rmd_template_path:", class(absolute_rmd_template_path)))
    message(paste("Length of absolute_rmd_template_path:", length(absolute_rmd_template_path)))
    message(paste("Value of absolute_rmd_template_path:", absolute_rmd_template_path))

    if (!is.character(absolute_rmd_template_path) || length(absolute_rmd_template_path) != 1 || !file.exists(absolute_rmd_template_path)) {
      stop(paste("Invalid RMD template path provided to rmarkdown::render. Path:", toString(absolute_rmd_template_path), # Use toString for safety
                 "Class:", class(absolute_rmd_template_path),
                 "Length:", length(absolute_rmd_template_path),
                 "Exists:", file.exists(absolute_rmd_template_path)))
    }

    # 設定 knitr 的根目錄為當前 R 腳本的工作目錄 (即專案根目錄)
    # 這有助於 R Markdown 內部正確解析相對於專案根目錄的路徑，
    # 特別是如果 Rmd 文件中的 params$data_dir 被錯誤地解釋為相對路徑時。
    original_knit_root_dir <- knitr::opts_knit$get("root.dir")
    message(paste("Original knitr root.dir before render:", original_knit_root_dir))
    # getwd() 此時應該是專案根目錄, 例如 /home/lean/Starlink-Taipei
    knitr::opts_knit$set(root.dir = normalizePath(getwd())) 
    message(paste("Set knitr root.dir for render to:", knitr::opts_knit$get("root.dir")))

    # 清理函數，確保 knitr root.dir 在函數退出時被還原
    on.exit({
        message(paste("Restoring knitr root.dir after render to:", original_knit_root_dir))
        knitr::opts_knit$set(root.dir = original_knit_root_dir)
    }, add = TRUE) # add = TRUE 很重要，以附加到現有的 on.exit 處理器 (如果有的話)

    params_list <- list(
      data_dir = absolute_data_dir, # 這個路徑需要 Rmd 檔案可以訪問到
      stats_file = "coverage_stats.json",
      coverage_file = "coverage_data.csv",
      sat_timeline_plot = "visible_satellites_timeline.png",
      elev_timeline_plot = "elevation_timeline.png",
      heatmap_plot = "coverage_heatmap.html"
    )
    
    # 確保 output_dir 是絕對路徑並且存在 (雖然之前已經檢查和創建過)
    absolute_output_dir <- normalizePath(output_dir, mustWork = FALSE) 
    if (!dir.exists(absolute_output_dir)) {
        message(paste("Creating output directory for RMD render (should exist but re-checking):", absolute_output_dir))
        dir.create(absolute_output_dir, recursive = TRUE)
    }
    message(paste("Render: Explicit absolute_output_dir for rmarkdown::render:", absolute_output_dir))
    # output_file_path 仍然用於檢查文件是否生成，但傳給 render 的是分離的 output_dir 和 output_filename
    # output_file_path <- file.path(absolute_output_dir, output_filename) # 這行現在不是主要的，但可用於後續檢查

    # 渲染 R Markdown 文件
    # output_file_path <- file.path(output_dir, output_filename) # 舊的 output_file_path 計算方式
    
    # 新的 output_file_path 計算方式 (基於絕對路徑的 output_dir)
    final_report_path <- file.path(normalizePath(output_dir), output_filename)

    # 新增的調試訊息
    message(paste("Current working directory for R:", getwd()))
    message(paste("RMD template path (input):", rmd_template_path))
    message(paste("Data directory parameter for RMD (params$data_dir):", params_list$data_dir)) # 打印實際傳遞的 data_dir
    message(paste("Output file path for RMD (used for checking existence post-render):", final_report_path))
    message(paste("Does data_dir (", params_list$data_dir, ") exist before render?", dir.exists(params_list$data_dir)))

    rmarkdown::render(
      input = absolute_rmd_template_path, # 使用絕對路徑的模板
      output_file = output_filename, # 只傳遞文件名
      output_dir = normalizePath(output_dir), # 明確設定輸出目錄為絕對路徑
      params = params_list,
      envir = new.env(), # 在新的環境中渲染以避免衝突
      quiet = FALSE # 設定為 FALSE 可以看到更多渲染過程的輸出
    )
    
    if (file.exists(final_report_path)) {
      message(paste("✅ R Markdown HTML report generated successfully:", final_report_path))
      return(TRUE)
    } else {
      warning("R Markdown HTML report generation failed or file not found.")
      return(FALSE)
    }
    
  }, error = function(e) {
    warning(paste("Error generating R Markdown HTML report:", e$message))
    return(FALSE)
  })
}

#' Main Analysis Function - R Implementation
#' 
#' @description 
#' Main function to perform statistical analysis and generate visualizations
#' 
#' @param coverage_file character path to coverage data CSV file
#' @param output_dir character path to output directory
#' @return list containing analysis results
#' @export
analyze_coverage_data_r <- function(coverage_file, output_dir = "output") {
  message("🔬 Starting R-based analysis...")
  overall_success <- TRUE # 初始化整體成功狀態
  error_messages <- c()
  
  tryCatch({
    # Read coverage data
    if (!file.exists(coverage_file)) {
      error_messages <- c(error_messages, paste("Coverage file not found:", coverage_file))
      stop(paste("Coverage file not found:", coverage_file))
    }
    
    coverage_df <- read_csv(coverage_file, show_col_types = FALSE)
    message(paste("✅ Loaded coverage data:", nrow(coverage_df), "observations"))
    
    # Calculate statistics
    stats <- calculate_stats_r(coverage_df)
    if (is.null(stats) || stats$avg_visible_satellites == 0 && nrow(coverage_df) > 0) { # 簡單檢查統計計算是否異常
        message("⚠️ Statistics calculation might have issues.")
        # 不直接設 overall_success 為 FALSE，除非有更明確的錯誤
    }
    message("✅ Statistics calculated")
    
    # Generate visualizations
    viz_success <- generate_visualizations_r(coverage_df, output_dir)
    message(ifelse(viz_success, "✅ Visualizations generated", "⚠️ Visualization generation had issues"))
    if (!viz_success) {
      overall_success <- FALSE
      error_messages <- c(error_messages, "Visualization generation failed.")
    }
    
    # 在生成報告前，詳細檢查圖片和數據文件是否存在及其權限
    message("\nPost-visualization file checks before generating HTML report:")
    # 直接使用已知的文件名列表，並結合 output_dir (這是 analyze_coverage_data_r 的參數)
    files_to_verify_for_rmd <- c(
        "coverage_stats.json",
        "coverage_data.csv",
        "visible_satellites_timeline.png",
        "elevation_timeline.png",
        "coverage_heatmap.html"
    )
    
    for (fname in files_to_verify_for_rmd) {
        f_path_to_check <- file.path(output_dir, fname)
        abs_f_path <- normalizePath(f_path_to_check, mustWork = FALSE)
        message(paste("Verifying for RMD - File:", abs_f_path))
        exists_status <- file.exists(abs_f_path)
        message(paste("  Exists:", exists_status))
        if (exists_status) {
            file_info_check <- file.info(abs_f_path)
            message(paste("  Mode:", sprintf("%04o", file_info_check$mode))) # 使用 %04o 格式化
            message(paste("  Size (bytes):", file_info_check$size))
            # mode 4 for read access check
            readable_status <- file.access(abs_f_path, mode = 4) == 0 
            message(paste("  Is R-readable:", readable_status))
            if (!readable_status) {
                error_messages <- c(error_messages, paste("File not R-readable:", abs_f_path))
                overall_success <- FALSE # 標記問題
            }
        } else {
            error_messages <- c(error_messages, paste("File missing for RMD:", abs_f_path))
            overall_success <- FALSE # 標記問題
        }
    }
    message("") # 空行分隔日誌

    # Generate HTML report using R Markdown
    # 確保 rmd_template_path 是正確的，相對於執行 Rscript 時的 getwd()
    # 確保 rmd_template_path 是相對於專案根目錄的正確路徑
    # Python 端傳遞的路徑是基於 python 腳本的相對路徑，或者是一個可以被 R 理解的路徑
    # 在 r_integration.py 的 _run_r_analysis 中，r_script_path 是絕對路徑了
    # 在 analysis_service_r.R 的 analyze_coverage_data_r 中，rmd_path 是:
    # rmd_path <- file.path(getwd(), "app", "services", "report_template.Rmd") 這是正確的絕對路徑
    
    # 維持原有的 rmd_path 產生方式，因為它已經是絕對路徑
    # current_script_dir <- dirname(sys.frame(1)$ofile) # 獲取當前 R 腳本的目錄
    # # 如果直接執行，sys.frame(1)$ofile 可能為 NULL，需要備用方案
    # if (is.null(current_script_dir)) {
    #     # 備用方案：假設執行時的工作目錄是專案根目錄
    #     # 並且 analysis_service_r.R 在 app/services/ 下
    #     current_script_dir <- file.path(getwd(), "app", "services")
    # }
    # # 模板檔案相對於目前 R 服務腳本的位置
    # rmd_path_relative_to_script <- "report_template.Rmd" 
    # # 如果 analysis_service_r.R 和 report_template.Rmd 在同一個目錄
    # # rmd_path <- file.path(current_script_dir, rmd_path_relative_to_script)

    # 簡化 rmd_path 的獲取，直接基於當前工作目錄 (專案根目錄)
    rmd_path <- file.path(getwd(), "app", "services", "report_template.Rmd")
    
    # 強制檢查 rmd_path 是否存在，如果不存在則報錯
    if (!file.exists(rmd_path)) {
        stop(paste("Critical error: R Markdown template file not found at expected path:", rmd_path, "Current working directory is:", getwd()))
    }
    message(paste("Using RMD template path in analyze_coverage_data_r:", rmd_path))

    report_success <- generate_html_report_r(
      data_dir = output_dir, 
      output_dir = output_dir,
      rmd_template_path = rmd_path
    )
    message(ifelse(report_success, "✅ R Markdown HTML report generated", "⚠️ R Markdown HTML report generation had issues"))
    if (!report_success) {
      overall_success <- FALSE
      error_messages <- c(error_messages, "R Markdown HTML report generation failed.")
    }
    
    # Save statistics to JSON
    stats_file <- file.path(output_dir, "coverage_stats.json")
    tryCatch({
        write_json(stats, stats_file, pretty = TRUE, auto_unbox = TRUE)
        message(paste("✅ Statistics saved to:", stats_file))
    }, error = function(e_json) {
        message(paste("⚠️ Error saving statistics JSON:", e_json$message))
        overall_success <- FALSE
        error_messages <- c(error_messages, paste("Error saving statistics JSON:", e_json$message))
    })
    
    # Return results
    final_message <- if (overall_success) "R analysis completed successfully" else paste("R analysis had issues:", paste(error_messages, collapse=" "))
    return(list(
      success = overall_success,
      stats = stats,
      message = final_message
    ))
    
  }, error = function(e) {
    error_msg <- paste("R analysis failed:", e$message, paste(error_messages, collapse=" "))
    warning(error_msg)
    return(list(
      success = FALSE,
      stats = default_stats(),
      message = error_msg
    ))
  })
}

# Export key functions for external use
if (!interactive()) {
  # Command line interface
  args <- commandArgs(trailingOnly = TRUE)
  
  if (length(args) >= 1) {
    coverage_file <- args[1]
    output_dir <- ifelse(length(args) >= 2, args[2], "output")
    
    result <- analyze_coverage_data_r(coverage_file, output_dir)
    
    if (result$success) {
      message("🎉 R analysis completed successfully!")
      quit(status = 0)
    } else {
      message("❌ R analysis failed!")
      quit(status = 1)
    }
  }
} 