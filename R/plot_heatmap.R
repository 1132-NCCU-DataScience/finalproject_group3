#!/usr/bin/env Rscript
# plot_heatmap.R - 繪製衛星覆蓋熱力圖

#' 繪製衛星覆蓋熱力圖
#'
#' @param visible_data 衛星可見性數據
#' @return 熱力圖物件列表
plot_heatmap <- function(visible_data) {
  library(dplyr)
  library(ggplot2)
  library(leaflet)
  library(sf)
  library(htmltools)
  library(plotly)
  
  # 檢查輸入
  if (!is.data.frame(visible_data)) {
    stop("輸入必須是data.frame或tibble格式")
  }
  
  # 確保方位角和仰角欄位存在
  if (!("az" %in% names(visible_data)) || !("elev" %in% names(visible_data))) {
    stop("輸入數據必須包含'az'(方位角)和'elev'(仰角)欄位")
  }
  
  message("開始生成衛星覆蓋熱力圖...")
  
  # 1. 方位角-仰角熱力圖 ----
  
  # 創建二維柱狀圖資料
  az_elev_density <- visible_data %>%
    mutate(
      # 將方位角分組為5度一組
      az_bin = cut(az, breaks = seq(0, 360, by = 5), include.lowest = TRUE, labels = FALSE),
      # 將仰角分組為5度一組 (從25度開始，因為數據過濾時已經用了這個閾值)
      elev_bin = cut(elev, breaks = seq(25, 90, by = 5), include.lowest = TRUE, labels = FALSE)
    ) %>%
    count(az_bin, elev_bin) %>%
    mutate(
      # 轉換回中心點值以便畫圖
      az_mid = (az_bin * 5) - 2.5,
      elev_mid = (elev_bin * 5) + 22.5  # 25度開始，所以加22.5
    )
  
  # ggplot2熱力圖
  p1 <- ggplot(az_elev_density, aes(x = az_mid, y = elev_mid, fill = n)) +
    geom_tile() +
    scale_fill_viridis_c(name = "衛星頻次", 
                        option = "plasma", 
                        trans = "log1p") +
    coord_polar(theta = "x", start = 0, direction = -1) +
    scale_x_continuous(breaks = seq(0, 315, by = 45),
                      labels = c("北", "東北", "東", "東南", "南", "西南", "西", "西北")) +
    scale_y_continuous(breaks = seq(30, 90, by = 15)) +
    labs(title = "衛星覆蓋熱力圖 (極座標)",
         x = "",
         y = "仰角") +
    theme_minimal() +
    theme(
      plot.title = element_text(hjust = 0.5, face = "bold"),
      axis.text = element_text(size = 10),
      legend.position = "right",
      panel.grid.major = element_line(color = "gray80"),
      panel.grid.minor = element_line(color = "gray90")
    )
  
  # 2. 互動式熱力圖 (使用plotly) ----
  p2 <- plot_ly(
    z = matrix(0, nrow = 72, ncol = 13), # Placeholder matrix
    type = "heatmap",
    colorscale = "Plasma"
  )
  
  # 填充熱力圖數據
  heatmap_matrix <- matrix(0, nrow = 13, ncol = 72)  # 仰角 x 方位角
  
  for (i in 1:nrow(az_elev_density)) {
    row_idx <- az_elev_density$elev_bin[i]
    col_idx <- az_elev_density$az_bin[i]
    if (!is.na(row_idx) && !is.na(col_idx)) {
      if (row_idx >= 1 && row_idx <= 13 && col_idx >= 1 && col_idx <= 72) {
        heatmap_matrix[row_idx, col_idx] <- az_elev_density$n[i]
      }
    }
  }
  
  # 定義方位角和仰角軸
  az_labels <- seq(0, 355, by = 5)
  elev_labels <- seq(27.5, 87.5, by = 5)
  
  p2 <- plot_ly(
    z = heatmap_matrix,
    x = az_labels,
    y = elev_labels,
    type = "heatmap",
    colorscale = "Plasma",
    colorbar = list(title = "衛星頻次")
  ) %>%
    layout(
      title = "衛星覆蓋熱力圖",
      xaxis = list(title = "方位角", tickvals = seq(0, 360, by = 45),
                 ticktext = c("北", "東北", "東", "東南", "南", "西南", "西", "西北", "北")),
      yaxis = list(title = "仰角")
    )
  
  # 3. 空間分佈熱力圖 (使用Leaflet) ----
  
  # 定義台北市的中心位置
  taipei_lat <- 25.0330
  taipei_lon <- 121.5654
  
  # 創建示例資料點
  # 針對每個方位角-仰角組合，計算在地面上的投影點
  ground_points <- visible_data %>%
    sample_n(min(5000, nrow(visible_data))) %>%  # 取樣避免過多點造成瀏覽器卡頓
    mutate(
      # 將仰角轉換為地面距離 (簡單近似，以10km為最遠可見距離)
      # 仰角越高，距離越近；仰角25度時距離約10km
      ground_distance_km = 10 * cos((elev * pi) / 180) / cos((25 * pi) / 180),
      # 將方位角和距離轉換為經緯度偏移
      lat_offset = ground_distance_km * cos((az * pi) / 180) / 111,  # 每1度緯度約111km
      lon_offset = ground_distance_km * sin((az * pi) / 180) / (111 * cos((taipei_lat * pi) / 180)),
      # 計算投影點座標
      proj_lat = taipei_lat + lat_offset,
      proj_lon = taipei_lon + lon_offset
    )
  
  # 創建leaflet熱力圖
  heatmap_leaflet <- leaflet() %>%
    addTiles() %>%  # 添加基本地圖
    addCircleMarkers(
      lng = taipei_lon, 
      lat = taipei_lat, 
      color = "red", 
      radius = 8, 
      popup = "台北市中心"
    ) %>%
    setView(lng = taipei_lon, lat = taipei_lat, zoom = 10) %>%
    addHeatmap(
      lng = ground_points$proj_lon, 
      lat = ground_points$proj_lat,
      intensity = ground_points$elev,  # 使用仰角作為強度
      radius = 12,
      blur = 15,
      max = 90,
      gradient = list(
        "0.0" = "#0000FF",
        "0.5" = "#00FF00", 
        "1.0" = "#FF0000"
      )
    ) %>%
    addLegend(
      position = "bottomright",
      colors = c("#0000FF", "#00FF00", "#FF0000"),
      labels = c("低", "中", "高"),
      title = "衛星密度"
    )
  
  # 保存結果
  result <- list(
    static_heatmap = p1,
    interactive_heatmap = p2,
    leaflet_heatmap = heatmap_leaflet
  )
  
  return(result)
}

# 如果從命令行直接執行此文件
if (sys.nframe() == 0) {
  args <- commandArgs(trailingOnly = TRUE)
  if (length(args) >= 1) {
    # 從CSV文件讀取數據
    visible_data <- readr::read_csv(args[1])
    
    # 生成熱力圖
    heatmaps <- plot_heatmap(visible_data)
    
    # 設定輸出目錄
    output_dir <- ifelse(length(args) >= 2, args[2], "output")
    if (!dir.exists(output_dir)) {
      dir.create(output_dir, recursive = TRUE)
    }
    
    # 保存ggplot2靜態熱力圖
    ggplot2::ggsave(file.path(output_dir, "satellite_heatmap.png"), 
                   heatmaps$static_heatmap, width = 10, height = 8)
    
    # 保存互動式熱力圖
    htmlwidgets::saveWidget(as_widget(heatmaps$interactive_heatmap), 
                           file.path(output_dir, "interactive_heatmap.html"), 
                           selfcontained = TRUE)
    
    # 保存Leaflet熱力圖
    htmlwidgets::saveWidget(heatmaps$leaflet_heatmap, 
                           file.path(output_dir, "spatial_heatmap.html"), 
                           selfcontained = TRUE)
    
    cat("熱力圖已保存至:", output_dir, "\n")
  }
}

# 返回函數作為targets調用函數
plot_heatmap 