# Starlink 台北衛星覆蓋分析系統

專為台北地區設計的 Starlink 衛星覆蓋分析系統，提供即時的衛星可見數量、覆蓋率、最佳連接仰角分析，並具備互動式網頁界面。

## 主要功能

-   **互動式網頁界面**: 使用者可選擇分析時長，即時查看分析進度與結果。
-   **即時 TLE 數據**: 自動獲取最新的 Starlink 衛星軌道數據。
-   **詳細分析報告**: 生成 HTML 報告，包含統計數據、時間線圖表與互動式熱力圖。
-   **進度回報**: 分析過程中，後端會回報進度至前端界面。
-   **命令行工具**: 提供 `starlink.py` 進行分析、系統檢查等操作。

## 快速啟動

1.  **安裝環境** (若尚未安裝):
    ```bash
    conda env create -f environment.yml
    conda activate starlink-env
    ```

2.  **啟動網頁服務**:
    ```bash
    ./start.sh
    ```
    或者直接執行 Flask App (開發模式):
    ```bash
    python app.py
    ```
    然後在瀏覽器中打開 `http://localhost:8080` (或 `app.py` 中配置的地址)。

## 命令行工具 (`starlink.py`)

提供一個統一的命令行界面 `starlink.py` 進行各項操作。

-   **啟動網頁服務器**:
    ```bash
    python starlink.py web
    python starlink.py web --port 8000 --host 127.0.0.1
    ```

-   **執行分析** (結果會自動更新到運作中的網頁服務):
    ```bash
    # 快速分析 (10 分鐘)
    python starlink.py analyze --quick

    # 標準分析 (預設 30 分鐘，可於 app.py 中調整預設值)
    python starlink.py analyze

    # 自定義時長與參數分析
    python starlink.py analyze --duration 60 --interval 0.5 --min_elevation 30
    ```

-   **系統健康檢查**:
    ```bash
    python starlink.py health
    ```

## 專案結構

```
Starlink-Taipei/
├── app.py                   # Flask 網頁應用程式
├── starlink.py              # 主命令行工具
├── start.sh                 # 快速啟動腳本 (啟動 Flask 應用)
├── satellite_analysis.py    # 核心分析引擎
├── scripts/
│   └── start_web.sh         # 網頁服務啟動輔助腳本
├── templates/
│   └── index.html           # Flask HTML 模板 (前端主頁)
├── utils/
│   ├── health_check.py      # 系統健康檢查
│   └── view_results.py      # CLI 結果查看器 (可考慮移除或簡化)
├── output/                  # 分析結果輸出目錄
│   ├── report.html          # HTML 完整報告
│   ├── coverage_heatmap.html  # HTML 互動熱力圖
│   ├── coverage_data.csv    # CSV 原始數據
│   ├── coverage_stats.json  # JSON 統計摘要
│   └── *.png                # PNG 圖表文件
├── environment.yml          # Conda 環境配置
└── README.md                # 本文件
```

## 分析結果範例 (台北地區)

-   **平均可見衛星**: 約 28-32 顆
-   **最大可見衛星**: 約 35-39 顆
-   **覆蓋率**: 通常為 100%
-   **平均最佳仰角**: 約 70-80°

## 進階使用

### 修改觀測位置

直接修改 `satellite_analysis.py` 中的預設經緯度，或在通過 `starlink.py analyze` 命令時使用 `--lat` 和 `--lon` 參數。

### 並行處理

`satellite_analysis.py` 支援使用 `--cpu` 參數指定並行處理的核心數。
`starlink.py analyze` 也支援此參數。

## 故障排除

-   **環境問題**: 確保 Conda 環境已正確安裝並啟動。執行 `conda activate starlink-env`，然後運行 `conda env update -f environment.yml --prune`。
    -   如果 `conda env update` 失敗並提示 `PackagesNotFoundError`，請檢查 `environment.yml` 文件。可能需要移除或替換找不到的套件，或者尋找其他 Conda 頻道。
-   **Flask 啟動失敗**: 檢查端口是否被佔用，或 `app.py` 中是否有語法錯誤。常見錯誤如 `ModuleNotFoundError: No module named 'flask'` 通常表示 Flask 未正確安裝，請重新執行環境更新指令。
-   **分析失敗**: 查看終端輸出與 `output/` 目錄下的日誌或錯誤訊息。可使用 `python starlink.py health` 檢查。
-   **權限問題**: 確保腳本有執行權限 (`chmod +x start.sh scripts/start_web.sh starlink.py app.py`)。

## 更新日誌

**v3.0**

-   引入 Flask 實現互動式網頁界面，允許用戶自選分析時長。
-   實現分析進度條與狀態回報。
-   簡化啟動流程，主要通過 `app.py` 提供服務。
-   更新 `starlink.py` 命令行工具以配合 Flask 應用。
-   調整專案結構，將 HTML 主頁移至 `templates` 目錄。
-   移除舊的 `update_index.py`。

**v2.0** 

-   專業網頁界面。
-   一鍵啟動功能。

**v1.5**

-   字型警告修復。
-   TLE 數據重試機制。

---

**啟動系統**: 執行 `./start.sh` 或 `python app.py`，然後訪問 `http://localhost:8080`。 