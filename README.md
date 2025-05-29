# 🛰️ Starlink 台北衛星分析系統 v4.0

一個專為分析 SpaceX Starlink 衛星在台北地區覆蓋情況而設計的互動式網頁應用系統。

## ✨ 主要特色

- 🌐 **互動式網頁界面**：基於 R Shiny 的現代化 Dashboard
- 📡 **實時衛星追蹤**：分析 7500+ 顆 Starlink 衛星的即時位置
- 📊 **智能數據視覺化**：互動式圖表、統計摘要和覆蓋分析
- ⚡ **高效能計算**：多核心並行處理，快速分析結果
- 💾 **多格式匯出**：支援 JSON、CSV、HTML、PNG 等格式下載
- 🎯 **精確定位分析**：針對台北地區的精確覆蓋率計算

## 🖥️ 系統預覽

### 主要功能模組

1. **🔧 分析參數控制**
   - 自定義觀測位置（緯度/經度）
   - 可調整分析持續時間（5-240分鐘）
   - 設定最小仰角閾值（10-45度）
   - 一鍵開始分析功能

2. **📈 統計結果展示**
   - 平均/最大可見衛星數
   - 覆蓋率百分比
   - 平均仰角統計
   - 詳細統計表格

3. **📊 視覺化圖表**
   - 互動式時間線圖表
   - 仰角變化分析
   - 覆蓋統計視覺化
   - 統計摘要圖表

4. **💾 數據下載中心**
   - 統計數據（JSON 格式）
   - 覆蓋數據（CSV 格式）
   - 完整報告（HTML 格式）
   - 圖表集合（PNG 格式）

## 🚀 快速開始

### 環境需求

- **Python 3.8+** （推薦 3.9 或更新版本）
- **R 4.0+** 及相關套件
- **作業系統**：Linux、macOS 或 Windows

### 安裝步驟

1. **複製專案**
```bash
git clone https://github.com/your-repo/Starlink-Taipei.git
cd Starlink-Taipei
```

2. **安裝 Python 依賴**
```bash
# 使用 conda（推薦）
conda env create -f environment.yml
conda activate starlink-analysis

# 或使用 pip
pip install -r requirements/requirements.txt
```

3. **安裝 R 套件**
```bash
# 系統會自動檢查並安裝必要的 R 套件
# 主要套件：shiny, shinydashboard, plotly, DT, ggplot2, dplyr, reticulate
```

### 啟動應用

```bash
# 啟動網頁應用（默認端口 3838）
python starlink.py shiny

# 自定義端口和主機
python starlink.py shiny --port 8080 --host 0.0.0.0
```

啟動成功後，在瀏覽器中訪問：**http://localhost:3838**

## 💡 使用說明

### 基本操作流程

1. **設定分析參數**
   - 在左側邊欄調整觀測位置和分析參數
   - 台北預設座標：25.0330°N, 121.5654°E

2. **執行分析**
   - 點擊 "🚀 開始分析" 按鈕
   - 觀察進度條顯示分析進度
   - 系統自動載入最新衛星數據

3. **查看結果**
   - **統計結果**：查看覆蓋統計和詳細數據表
   - **視覺化**：互動式圖表分析衛星覆蓋趨勢
   - **數據下載**：匯出所需格式的分析結果

### 進階功能

- **參數調整**：根據需求修改分析持續時間和時間間隔
- **自定義位置**：分析台北以外地區的衛星覆蓋
- **批量分析**：下載 CSV 數據進行進一步分析
- **報告生成**：HTML 報告適合分享和展示

## 📊 輸出結果說明

### 統計指標

- **平均可見衛星數**：分析期間平均可見的衛星數量
- **最大可見衛星數**：單一時間點最多可見衛星數
- **覆蓋率**：有衛星覆蓋的時間百分比
- **平均仰角**：可見衛星的平均仰角度數

### 檔案格式

- **`coverage_stats.json`**：統計摘要數據
- **`coverage_data.csv`**：詳細時間序列數據  
- **`coverage_report.html`**：完整視覺化報告
- **`*.png`**：高解析度圖表檔案

## 🛠️ 技術架構

### 後端技術

- **Python**：衛星軌道計算和數據處理
- **Skyfield**：精確的天體力學計算
- **NumPy/Pandas**：高效能數據操作
- **Matplotlib/Plotly**：專業級數據視覺化

### 前端技術

- **R Shiny**：互動式網頁框架
- **shinydashboard**：現代化 Dashboard 界面
- **plotly.js**：互動式圖表渲染
- **Bootstrap**：響應式 UI 設計

### 數據來源

- **TLE 數據**：從 CelesTrak 獲取最新的 Starlink 軌道數據
- **本地緩存**：自動緩存 TLE 數據，減少網路依賴
- **實時計算**：基於當前時間的即時覆蓋分析

## 🔧 命令列工具

除了網頁界面，系統也提供命令列工具：

```bash
# 執行分析並生成報告
python starlink.py analyze --duration 120 --interval 2

# 檢查系統健康狀態
python starlink.py health

# 更新衛星數據
python starlink.py update

# 查看完整選項
python starlink.py --help
```

## 📋 系統需求

### 最低配置

- **CPU**：雙核心 2.0 GHz
- **RAM**：4 GB
- **儲存**：2 GB 可用空間
- **網路**：寬頻連接（用於下載 TLE 數據）

### 推薦配置

- **CPU**：四核心 3.0 GHz 或更高
- **RAM**：8 GB 或更多
- **儲存**：5 GB 可用空間
- **網路**：穩定的寬頻連接

## 🚨 疑難排解

### 常見問題

1. **網頁無法載入**
   - 檢查端口是否被占用
   - 確認防火牆設定
   - 驗證 R 套件安裝

2. **分析結果異常**
   - 更新 TLE 數據：`python starlink.py update`
   - 檢查系統時間設定
   - 驗證網路連接

3. **效能問題**
   - 減少分析持續時間
   - 增加時間間隔
   - 關閉其他占用記憶體的程式

### 診斷工具

```bash
# 系統健康檢查
python starlink.py health

# 檢查 R 環境
R --version

# 測試網路連接
curl -I https://celestrak.org/
```

## 🤝 貢獻指南

歡迎貢獻代碼、報告問題或提出改進建議！

1. Fork 此專案
2. 創建功能分支：`git checkout -b feature/amazing-feature`
3. 提交變更：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

## 📄 授權條款

本專案採用 MIT 授權條款。詳見 [LICENSE](LICENSE) 檔案。

## 📧 聯絡資訊

- **專案維護者**：Starlink 台北分析團隊
- **問題回報**：請使用 GitHub Issues
- **功能建議**：歡迎提交 Pull Request

## 🏷️ 版本歷史

### v4.0 - Shiny Dashboard (最新)
- ✨ 全新互動式網頁界面
- 📊 即時數據視覺化
- ⚡ 效能優化和穩定性提升
- 💾 多格式數據匯出
- 🎯 使用者體驗改進

### v3.x - 命令列工具
- 基礎分析功能
- TLE 數據處理
- 統計報告生成

---

**🛰️ 讓我們一起探索 Starlink 衛星網路的無限可能！** 