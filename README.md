# AIOps 數據管道哨兵 (AIOps Data Pipeline Sentinel)

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://www.python.org)
[![Dagster](https://img.shields.io/badge/Dagster-1.7+-blue?logo=dagster)](https://dagster.io)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini API](https://img.shields.io/badge/Gemini_API-blue?logo=google)](https://aistudio.google.com/)
[![Slack](https://img.shields.io/badge/Slack-blue?logo=slack)](https://slack.com)

**一個 AIOps 驅動的自動化系統，用於即時監控、診斷數據管道 (Data Pipeline) 故障，並自動發送 AI 分析的修復建議至 Slack。**

---

### 🏁 最終成果：自動化 AI 警報

當數據管道失敗時，系統會自動介入。AI 診斷引擎會分析根本原因，並立即在 10 秒內將詳細的分析報告推送到 Slack，將手動除錯時間 (MTTR) 從數小時縮短到數秒鐘。

![AIOps 哨兵的最終 Slack 警報](https://github.com/7Jerrybf/AIOps-Data-Pipeline-Sentinel/blob/main/assets/slack_alert.png)


---

### 🎯 專案核心價值

在現代數據工程中，管道失敗是常態。但「發現失敗」和「分析原因」往往是手動、被動且耗時的。

本專案的核心價值在於**實現了極高的工程槓桿率**：
* **從「被動」到「主動」**：系統 7x24 自動監控，失敗即觸發。
* **從「手動」到「自動」**：AI 自動完成根本原因分析 (RCA)。
* **從「猜測」到「建議」**：AI 不僅報告問題，還直接提供程式碼修復建議。

這完美呼應了「數據系統優化工程師」的核心職責：**專注於解決流程本身的痛點，並編寫程式進行自動化和優化。**

---

### 🏛️ 系統架構

本系統由兩個核心服務和一個自動化迴路組成：

1.  **靶子 (The Target - Dagster)**：一個 `aio_pipeline` 數據管道，其中 `transform_data` 步驟故意埋有 `1 / 0` Bug。
2.  **大腦 (The Brain - FastAPI)**：一個 `brain_api.py` 伺服器，提供 `/diagnose` API，內部封裝了 Google Gemini AI 的分析邏輯。
3.  **迴路 (The Loop - Hook)**：Dagster 的 `@failure_hook` (哨兵) 會在失敗時自動觸發，調用 Brain API，並使用 `requests` 將 AI 結果發送到 Slack Webhook。


![系統架構圖](https://github.com/7Jerrybf/AIOps-Data-Pipeline-Sentinel/blob/main/assets/Untitled%20diagram-2025-11-07-013145.png)
---

### 🚀 技術棧 (Technology Stack)
* 數據管道 (Orchestration): Dagster
* AI 診斷 API (The Brain): FastAPI
* 伺服器 (Server): Uvicorn
* AI 核心 (LLM): Google Gemini API (gemini-flash-lite-latest)
* 核心語言: Python 3.11+
* 依賴管理: venv & requirements.txt
* 環境變數: python-dotenv (.env)
* 網路請求: requests (用於調用 Brain API 和 Slack Webhook)
* 告警終端: Slack (Incoming Webhooks)

### 🔧 安裝與啟動 (Setup & Usage)
1. 克隆專案並設定環境
```Bash
git clone https://github.com/7Jerrybf/AIOps-Data-Pipeline-Sentinel.git
cd aio_sentinel
python -m venv venv
venv\Scripts\activate
```
**2. 安裝依賴**

所有依賴都已在 requirements.txt 中定義：
```Bash
pip install -r requirements.txt
```
**3. 設定環境變數**
複製 .env.example (您需要手動建立這個檔案) 為 .env：
```.env
# .env.example (請建立此檔案，並填入您的金鑰後，另存為 .env)
# .env 檔案已被加入 .gitignore，保護您的金鑰安全

GOOGLE_API_KEY="您申請到的Gemini金鑰"

SLACK_WEBHOOK_URL="[https://hooks.slack.com/services/](https://hooks.slack.com/services/)..."
```
**4. 啟動服務 (需要兩個終端機)**

➡️ 終端機 1：啟動 AI 大腦 (Brain API)
```Bash
python brain_api.py
```
➡️ 終端機 2：啟動數據管道 (Dagit UI)
```Bash
dagster dev -f pipeline.py -p 4000
```
**5. 觸發測試**

打開瀏覽器，訪問 http://127.0.0.1:4000 (Dagit UI)。

點擊 aio_pipeline。

點擊 "Launch run" 啟動執行。

觀察 transform_data 步驟變為紅色 (失敗)。

檢查您的 Slack 頻道，AI 分析報告應在幾秒鐘內送達！
