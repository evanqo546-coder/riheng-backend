# riheng-backend

「日衡」App 的後端 Proxy：接收餐點文字描述和/或照片，呼叫 Anthropic Claude API 估算熱量與三大營養素，回傳結構化 JSON。

## 端點

- `GET /ping`：健康檢查，回傳 `{"status": "ok"}`
- `POST /estimate-meal`：估算餐點營養（需要驗證，見下方）
  - 必要 request header：`X-App-Secret: <BACKEND_SHARED_SECRET>`，不符合會回 401
  - 請求 body（JSON）：
    ```json
    {
      "description": "一碗滷肉飯加一顆滷蛋",
      "photo_base64": "（可選，圖片的 base64 編碼，不含 data URI 前綴）",
      "photo_media_type": "image/jpeg"
    }
    ```
    `description` 和 `photo_base64` 至少要有一個。
  - 回應（JSON）：
    ```json
    {
      "items": [{"name": "滷肉飯", "amount_g": 350, "calories": 550}],
      "total_calories": 650,
      "total_protein_g": 20,
      "total_carbs_g": 90,
      "total_fat_g": 18,
      "confidence_note": "份量為目測估算，實際依食材與烹調方式可能有差異"
    }
    ```

## 環境變數（設定在部署環境，不進 Git repo）

- `ANTHROPIC_API_KEY`：Anthropic Claude API 金鑰
- `BACKEND_SHARED_SECRET`：呼叫端（App）需要在 `X-App-Secret` header 帶上同一組值才能通過驗證，沒設定這個環境變數的話所有請求都會被拒絕（500）
- `ANTHROPIC_MODEL`（可選）：預設 `claude-sonnet-5`

## PythonAnywhere 部署步驟（免費方案，跟現有 Web App 共用一個網址、用路徑分流）

1. 打開 PythonAnywhere 的 **Bash console**，執行：
   ```bash
   cd ~
   git clone https://github.com/evanqo546-coder/riheng-backend.git
   ```
2. 建立獨立的虛擬環境，或直接把套件裝進 Web App 實際使用的環境（哪一種取決於該 Web App 的 Virtualenv 設定，兩者擇一，不要搞混）：
   ```bash
   pip install -r ~/riheng-backend/requirements.txt
   ```
3. 到 PythonAnywhere 的 **Web** 分頁，找到現有的 Web App（`<your-username>.pythonanywhere.com`），打開 **WSGI configuration file**，加入路徑分流設定，讓 `/health-api/...` 導到這支後端、其餘路徑維持原本系統的行為。
4. 在同一個 WSGI 檔案裡設定環境變數（這個檔案不在任何 Git repo 裡，不會外流）：
   ```python
   os.environ['ANTHROPIC_API_KEY'] = '你的 Anthropic 金鑰'
   os.environ['BACKEND_SHARED_SECRET'] = '一組只有你自己知道的長字串'
   ```
5. 存檔後回到 **Web** 分頁，點 **Reload** 按鈕。
6. 測試：
   ```bash
   curl https://<your-username>.pythonanywhere.com/health-api/ping
   # 應該看到 {"status": "ok"}

   curl -X POST https://<your-username>.pythonanywhere.com/health-api/estimate-meal \
     -H "Content-Type: application/json" \
     -H "X-App-Secret: 你設定的密鑰" \
     -d '{"description": "一碗白飯"}'
   ```
