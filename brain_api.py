import os
import uvicorn
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv 

load_dotenv()

# --- Pydantic 模型定義 ---
# Pydantic 用於驗證 API 的請求 (Request) 和回應 (Response) 格式

class DiagnoseRequest(BaseModel):
    """API 請求的 body 格式"""
    log_content: str # 我們期望收到一個叫做 log_content 的字串

class DiagnoseResponse(BaseModel):
    """API 回應的 body 格式 (我們要求 AI 回傳的)"""
    root_cause: str
    failing_function: str
    suggested_fix: str

# --- FastAPI 應用程式實例 ---
app = FastAPI(
    title="AIOps 哨兵 - 診斷引擎 API",
    description="接收日誌並使用 AI 進行根本原因分析 (RCA)"
)

# --- AI 設定 ---
try:
    # 1. 從環境變數讀取 API Key
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY 環境變數未設定！")
    
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # 2. 設定 AI 模型
    generation_config = {
        "temperature": 0.2, # 低溫，讓 AI 回答更具確定性
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 2048,
    }
    
    # 3. 設定安全設定 (避免 AI 拒絕分析日誌)
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    # 4. 初始化模型
    model = genai.GenerativeModel(
        model_name="gemini-flash-lite-latest", 
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    
    # 5. 🚩 我們的黃金 Prompt (The "Brain") 🚩
    SYSTEM_PROMPT = """
    你是一位頂尖的 SRE 專家與 Python 數據工程師，專精於分析 Dagster 數據管道的錯誤日誌。
    你的任務是精確、簡潔地分析使用者提供的日誌，並以中文回覆。

    使用者將提供一段 Dagster 失敗日誌。
    你必須分析日誌，並「只」回傳一個格式化的 JSON 物件，格式如下：

    {
      "root_cause": "對根本原因的簡短中文描述 (例如：零除錯誤)。",
      "failing_function": "具體出錯的函式或檔案 (例如：在 pipeline.py 中的 transform_data 函式)。",
      "suggested_fix": "建議的程式碼修復方案 (以 Markdown 格式，包含程式碼區塊)。"
    }

    **規則：**
    1.  不要有任何 JSON 以外的開場白或結語 (例如，不要說「這是一個...」或「希望這有幫助...」)。
    2.  分析必須基於日誌中的 Traceback。
    3.  `root_cause` 必須非常簡潔。
    4.  `suggested_fix` 必須提供可操作的程式碼建議。
    """
    
except Exception as e:
    print(f"AI 模型初始化失敗: {e}")
    model = None

# --- API 端點 (Endpoint) ---

@app.get("/", summary="健康檢查")
def read_root():
    """一個簡單的端點，用於確認 API 伺服器正在運行。"""
    return {"status": "AIOps 診斷引擎已啟動"}

@app.post("/diagnose", response_model=DiagnoseResponse, summary="診斷日誌")
async def diagnose_log(request: DiagnoseRequest):
    """
    接收 Dagster 日誌，使用 AI 分析其根本原因並回傳修復建議。
    """
    if not model:
        raise HTTPException(status_code=500, detail="AI 模型未初始化，請檢查 API Key 或伺服器日誌。")

    try:
        # 準備要發送給 AI 的完整 Prompt
        full_prompt = f"{SYSTEM_PROMPT}\n\n【使用者提供的日誌】:\n{request.log_content}"
        
        # 產生內容
        response = model.generate_content(full_prompt)
        
        # 提取 AI 的回覆 (通常在 response.text 中，且應為 JSON 字串)
        ai_response_text = response.text.strip()
        
        # 為了穩定性，移除 AI 可能夾帶的 markdown 標記 (```json ... ```)
        if ai_response_text.startswith("```json"):
            ai_response_text = ai_response_text[7:-3].strip()
        
        # 在伺服器端印出 AI 的原始回覆，方便除錯
        print("--- AI 原始回覆 ---")
        print(ai_response_text)
        print("---------------------")

        # FastAPI 會自動解析 Pydantic 模型
        # 我們假設 AI 完美地回傳了我們要求的 JSON 格式
        # (這裡我們依靠 Pydantic 來驗證 AI 的回覆是否符合格式)
        return DiagnoseResponse.parse_raw(ai_response_text)

    except Exception as e:
        # 我們只需要印出 'e'，它就包含了所有錯誤訊息 (像您剛貼上的)
        print(f"AI 分析或 JSON 解析失敗: {e}") 
        raise HTTPException(
            status_code=500, 
            # 直接將錯誤訊息 'e' 傳回給瀏覽器，更乾淨
            detail=f"AI 分析失敗: {str(e)}" 
        )

# --- 啟動伺服器 ---
if __name__ == "__main__":
    """
    允許我們直接用 python brain_api.py 來啟動這個伺服器。
    """
    print("正在啟動 AIOps 診斷引擎 API 伺服器...")
    uvicorn.run(
        "brain_api:app",  # 格式: "檔名:FastAPI實例名"
        host="127.0.0.1", 
        port=8000,        # 我們將 API 運行在 8000 埠號
        reload=True       # "reload=True" 會在程式碼變更時自動重啟，方便開發
    )