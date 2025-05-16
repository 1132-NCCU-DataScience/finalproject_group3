# 台北市區 24h 衛星 Handover 週期與延遲分析

本專案旨在分析台北市區 24 小時內 Starlink 衛星的覆蓋情況、Handover 週期與延遲。專案整合 Python 和 R 的分析與視覺化能力，提供全方位的衛星追蹤與分析結果。

## 功能特點

- **衛星追蹤**：利用最新的 Starlink TLE 數據追蹤衛星軌道及位置
- **覆蓋分析**：分析 24 小時內台北市區的衛星覆蓋情況
- **Handover 分析**：計算衛星切換頻率與時間分布
- **視覺化呈現**：
  - 統計表：包含可見衛星數量、覆蓋率等關鍵指標
  - 互動式時間線圖：顯示可見衛星數量變化與 Handover 時刻
  - 互動式覆蓋熱度圖：以方位角/仰角為座標顯示衛星分布密度
  - HTML 互動式報告：包含完整分析結果與互動式圖表

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
chmod +x start.sh
./start.sh
```

執行此腳本將會：
- 建立並更新必要的 conda 環境
- 執行 Python 衛星分析模組
- 生成互動式 HTML 報告
- 自動打開生成的分析報告（如果系統支援）

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

3. 生成 R Markdown 互動式報告

```bash
# 確保啟用了 conda 環境
conda activate starlink-env

# 渲染 R Markdown 報告
R -e "rmarkdown::render('Rmd/enhanced_report.Rmd', output_file = '../output/starlink_coverage_report.html')"

# 查看報告
xdg-open output/starlink_coverage_report.html  # Linux
# 或
open output/starlink_coverage_report.html      # macOS
```

## 分析結果

分析結果將保存在 `output` 目錄中，主要包括：

- `satellite_coverage.csv`：衛星覆蓋數據
- `satellite_handovers.csv`：衛星切換數據
- `coverage_stats.json`：覆蓋統計數據
- `visible_satellites_timeline.png`：可見衛星數量時間線圖
- `best_satellite_elevation.png`：最佳衛星仰角時間線圖
- `handover_timeline.png`：Handover 時間線圖
- `coverage_heatmap.html`：互動式覆蓋熱力圖
- `starlink_coverage_report.html`：**完整互動式 HTML 報告** (主要查看結果的文件)

## 調整分析參數

若要調整分析參數，可以直接編輯 `satellite_analysis.py` 文件中的設定：

```python
# 台北市經緯度座標
TAIPEI_LAT = 25.0330
TAIPEI_LON = 121.5654
ELEVATION = 10.0  # 假設高度(公尺)
```

針對台北市的預設設定：
- 緯度：25.0330
- 經度：121.5654
- 高度：10 公尺（海拔）
- 分析間隔：1 分鐘

## 技術說明

### 專案架構

- **Python 部分**：使用 Skyfield 進行衛星軌道計算，分析 24 小時衛星覆蓋情況
  - `satellite_analysis.py`：主分析腳本
  - `py/visibility.py`：衛星可見度計算模組

- **R 部分**：視覺化與報告生成
  - `Rmd/enhanced_report.Rmd`：R Markdown 互動式報告模板
  - `R/`：輔助分析與繪圖函數

### 更新說明

本專案最初使用 Shiny 儀表板呈現結果，現已改為使用 R Markdown 生成互動式 HTML 報告。這一改進帶來以下優勢：

1. **無需運行伺服器**：報告生成後即可直接在瀏覽器中打開，無需啟動 Shiny 伺服器
2. **更穩定的套件相容性**：減少 R 套件依賴，提高在不同環境中的兼容性
3. **更易於分享**：生成的 HTML 文件可直接分享，而無需接收方安裝特定環境
4. **保留互動性**：通過 plotly 和 DT 等套件，報告仍具有豐富的互動功能

## 環境與套件管理說明

### 關於 conda 與 R 套件

本專案使用 conda 管理 Python 與 R 的環境。所有必要的 R 與 Python 套件都已經在 `environment.yml` 中定義，並會通過 conda 自動安裝。

**重要說明**: 為避免 C 庫編譯問題，建議**不要**使用 R 的 `install.packages()` 函數安裝套件，而是透過 conda 安裝所有 R 套件。

### 如何添加新套件

如果需要添加新的 R 套件，請按照以下步驟：

1. 在 `environment.yml` 文件中添加套件（格式為 `r-套件名稱`，全部小寫）
2. 執行 `conda env update -f environment.yml` 更新環境

### 故障排除

#### 常見問題與解決方案

1. **NumPy 類型序列化問題**：如果出現 `TypeError: Object of type int64 is not JSON serializable` 等錯誤，這是因為 NumPy 數值類型（如 `np.int64` 或 `np.float64`）無法直接序列化為 JSON。解決方案：將 NumPy 類型轉換為 Python 原生類型（如 `int` 或 `float`）。

2. **R 套件缺失**：如果 R Markdown 報告生成失敗，並顯示套件缺失錯誤，請使用 conda 安裝缺失的套件：
   ```bash
   conda install -c conda-forge r-缺失套件名稱
   ```

3. **TLE 數據下載問題**：如果衛星 TLE 數據無法下載，可能是網絡連接問題或 API 變更。可嘗試手動下載 TLE 數據，並使用 `load_tle` 方法代替自動下載：
   ```python
   analyzer = StarlinkAnalysis(tle_file="path/to/your/tle_file.txt")
   ```

## 相關技術

- Python：使用 Skyfield 進行衛星軌道計算
- R：使用 ggplot2、plotly、DT 等套件進行數據視覺化
- 資料視覺化：使用 Matplotlib、Plotly、ggplot2
- 報告生成：R Markdown、HTML、CSS、JavaScript

## 授權條款

[MIT 授權條款](LICENSE) 