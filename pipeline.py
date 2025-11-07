import requests
import sqlite3
import time
import os
import traceback
from dagster import (
    job, 
    op, 
    OpExecutionContext, 
    Failure,
    HookContext,
    failure_hook,
    HookDefinition  
)
from dotenv import load_dotenv

load_dotenv() 

# --- AI 哨兵 Hook (保持不變) ---

BRAIN_API_URL = "http://127.0.0.1:8000/diagnose"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
SLACK_CHANNEL_NAME = "#aio-alerts"

@failure_hook 
def ai_failure_sentinel(context: HookContext):
    """
    使用 'requests' 模組發送訊息到 Webhook URL。
    """
    op_name = context.op.name
    error = context.op_exception
    log_content = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    context.log.info(f"Op '{op_name}' 失敗。正在啟動 AI 診斷引擎...")

    try:
        # --- 步驟 A: 調用 Brain API (不變) ---
        response = requests.post(
            BRAIN_API_URL,
            json={"log_content": log_content},
            timeout=60
        )
        response.raise_for_status()
        ai_analysis = response.json()
        context.log.info(f"AI 診斷完成。正在發送報告至 Slack...")

        # --- 步驟 B: 使用 'requests' 發送 Slack ---
        slack_message = f"""
        :rotating_light: *AIOps 哨兵警報* :rotating_light:
        *管道 (Job)*: `{context.job_name}`
        *操作 (Op)*: `{op_name}`
        *狀態*: :x: *失敗*
        ---
        *AI 診斷 - 根本原因*:
        {ai_analysis.get('root_cause', 'N/A')}
        *AI 診斷 - 失敗位置*:
        `{ai_analysis.get('failing_function', 'N/A')}`
        *AI 診斷 - 修復建議*:
        ```{ai_analysis.get('suggested_fix', '無建議')}```
        """

        # 這是 Webhook 的正確 JSON 格式
        slack_payload = {"text": slack_message} 
        
        # 直接使用 requests.post
        slack_response = requests.post(
            SLACK_WEBHOOK_URL, 
            json=slack_payload,
            timeout=10
        )
        slack_response.raise_for_status() # 檢查 Slack 是否發送成功
        
        context.log.info(f"成功發送報告至 Slack。")

    except Exception as e:
        context.log.error(f"AI 哨兵執行失敗 (在 try 區塊): {e}")
        
        # --- 步驟 C: 緊急備援訊息 (也使用 'requests') ---
        try:
            emergency_message = f":alert: *AI 哨兵系統自我故障* :alert:\n無法分析 Op '{op_name}' 的失敗。\n錯誤: {e}"
            requests.post(
                SLACK_WEBHOOK_URL,
                json={"text": emergency_message},
                timeout=10
            )
        except Exception as final_err:
            context.log.error(f"連緊急 Slack 訊息都發送失敗: {final_err}")

# --- Op (操作) ---

@op 
def extract_data(context: OpExecutionContext) -> dict:
    """ 
    (Extract) - 模擬 (Mock) 版本
    100% 穩定，不依賴任何網路 API。
    """
    context.log.info("正在加載 Mock 數據 (無網路請求)...")

    mock_data = {
        "time": {
            "updatedISO": "2025-11-07T08:00:00.000Z",
            "updated": "Nov 7, 2025 08:00:00 UTC"
        },
        "bpi": {
            "USD": {
                "code": "USD",
                "rate": "50,000.00",
                "description": "United States Dollar",
                "rate_float": 50000.0
            }
        }
    }

    context.log.info("Mock 數據加載完畢。")
    return mock_data

@op
def transform_data(context: OpExecutionContext, data: dict) -> dict:
    """ (Transform) 保持不變，我們的 Bug 依然在這裡。 """
    try:
        # 恢復使用 V1 API 的數據結構
        bpi = data.get("bpi", {})
        usd_rate_str = bpi.get("USD", {}).get("rate_float", "0")
        
        usd_rate_float = float(usd_rate_str)
        
        context.log.info("正在執行關鍵計算...")
        
        # --- 🚩 我們的 Bug 仍然在這裡 🚩 ---
        problematic_calculation = 1 / 0  # 這將引發 ZeroDivisionError
        # --- Bug 結束 ---

        processed_data = {
            "timestamp": data.get("time", {}).get("updatedISO"),
            "usd_rate": usd_rate_float,
            "processed_at": time.time()
        }
        
        context.log.info(f"數據轉換完成。")
        return processed_data

    except Exception as e:
        context.log.error(f"轉換數據時發生嚴重錯誤: {e}", exc_info=True)
        raise

@op
def load_data(context: OpExecutionContext, processed_data: dict):
    """ (Load) 保持不變 """
    conn = sqlite3.connect("local_database.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS bitcoin_price (timestamp TEXT, usd_rate REAL, processed_at REAL)")
    cursor.execute(
        "INSERT INTO bitcoin_price (timestamp, usd_rate, processed_at) VALUES (?, ?, ?)",
        (processed_data["timestamp"], processed_data["usd_rate"], processed_data["processed_at"])
    )
    conn.commit()
    conn.close()
    context.log.info("成功將數據加載到 local_database.db。")


# --- Job (職位) ---

@job(
    hooks={ai_failure_sentinel}
)
def aio_pipeline():
    """
    定義我們的數據管道：E -> T -> L
    """
    transformed_data = transform_data(extract_data())
    load_data(transformed_data)