# 台北市區 24h 衛星 Handover 週期與延遲分析

本專案旨在分析台北市區 24 小時內 Starlink 衛星的覆蓋情況、Handover 週期與延遲。專案包含 Python 和 R 的整合分析與視覺化工具，提供全方位的衛星追蹤與分析結果。

## 功能特點

- **衛星追蹤**：利用最新的 Starlink TLE 數據追蹤衛星軌道及位置
- **覆蓋分析**：分析 24 小時內台北市區的衛星覆蓋情況
- **Handover 分析**：計算衛星切換頻率與時間分布
- **視覺化呈現**：
  - 統計表：包含可見衛星數量、覆蓋率等關鍵指標
  - 時間線圖：顯示可見衛星數量變化與 Handover 時刻
  - 覆蓋熱度圖：以方位角/仰角為座標顯示衛星分布密度
  - HTML 報告：完整靜態分析報告
  - Shiny Dashboard：互動式分析儀表板

## 環境需求

- Linux 或 macOS 系統
- [Anaconda](https://www.anaconda.com/products/distribution) 或 [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- 互聯網連接 (用於下載最新的衛星 TLE 數據)

## 安裝方法

1. 複製專案

```bash
git clone https://github.com/yourusername/starlink-taipei-analysis.git
cd starlink-taipei-analysis
```

2. 使用自動化腳本設置環境與執行分析

```bash
chmod +x run_analysis.sh
./run_analysis.sh
```

## 手動安裝與操作

1. 創建並激活 conda 環境

```bash
conda env create -f environment.yml
conda activate starlink-env
```

2. 執行 Python 分析

```bash
python satellite_analysis.py
```

3. 啟動 Shiny Dashboard

```bash
R -e "shiny::runApp('app.R', host='0.0.0.0', port=3838, launch.browser=TRUE)"
```

## 腳本參數

`run_analysis.sh` 腳本支持以下參數：

- `--analysis-only`：僅執行分析，不啟動儀表板
- `--dashboard-only`：僅啟動儀表板，不執行分析
- `--help` 或 `-h`：顯示幫助訊息

## 分析結果

分析結果將保存在 `output` 目錄中，主要包括：

- `satellite_coverage.csv`：衛星覆蓋數據
- `satellite_handovers.csv`：衛星切換數據
- `coverage_stats.json`：覆蓋統計數據
- `visible_satellites_timeline.png`：可見衛星數量時間線圖
- `best_satellite_elevation.png`：最佳衛星仰角時間線圖
- `handover_timeline.png`：Handover 時間線圖
- `coverage_heatmap.html`：互動式覆蓋熱力圖
- `starlink_coverage_report.html`：完整 HTML 報告

## 調整分析參數

您可以在 Shiny Dashboard 中調整以下參數：

- 緯度/經度：調整分析位置
- 分析間隔：調整時間粒度（分鐘）

## 針對台北市的預設設定

- 緯度：25.0330
- 經度：121.5654
- 高度：10 公尺（海拔）
- 分析間隔：1 分鐘

## 環境與套件管理說明

### 關於 conda 與 R 套件

本專案使用 conda 管理 Python 與 R 的環境。所有必要的 R 與 Python 套件都已經在 `environment.yml` 中定義，並會通過 conda 自動安裝。

**重要說明**: 為避免 C 庫編譯問題，我們建議**不要**使用 R 的 `install.packages()` 函數安裝套件，而是透過 conda 安裝所有 R 套件。這樣可以避免 libcurl、openssl 等 C 庫的編譯錯誤。

### 如何添加新套件

如果需要添加新的 R 套件，請按照以下步驟：

1. 在 `environment.yml` 文件中添加套件（格式為 `r-套件名稱`，全部小寫）
2. 執行 `conda env update -f environment.yml` 更新環境

### 故障排除

#### R 套件安裝錯誤

如果遇到 R 套件安裝錯誤（尤其是與 libcurl、openssl 等 C 庫相關的錯誤），請嘗試：

1. 確保使用 conda 管理環境：`conda activate starlink-env`
2. 通過 conda 安裝相關套件：`conda install -c conda-forge r-套件名稱`
3. 避免使用 R 的 `install.packages()` 函數

#### Shiny 應用啟動問題

如果 Shiny 應用啟動失敗，請檢查：

1. 是否已啟用 conda 環境：`conda activate starlink-env`
2. 所有必要的 R 套件是否已安裝（參見 `environment.yml`）
3. 檢查端口 3838 是否被佔用，如有需要可在啟動命令中更改端口

## 相關技術

- Python：使用 Skyfield 進行衛星軌道計算
- R：使用 Shiny 建立互動式儀表板
- 資料視覺化：使用 Matplotlib、Plotly、ggplot2
- 報告生成：HTML、CSS 

## 授權條款

[MIT 授權條款](LICENSE) 