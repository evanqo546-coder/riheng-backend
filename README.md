# riheng-backend

「日衡」App 的後端 Proxy：接收餐點文字描述和/或照片，呼叫 Anthropic Claude API 估算熱量與三大營養素，回傳結構化 JSON。

## 端點

- `GET /ping`：健康檢查，回傳 `{"status": "ok"}`
- `POST /estimate-meal`：估算餐點營養
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

## PythonAnywhere 部署步驟（免費方案，跟現有 Web App 共用一個網址、用路徑分流）

1. 打開 PythonAnywhere 的 **Bash console**，執行：
   ```bash
   cd ~
   git clone https://github.com/evanqo546-coder/riheng-backend.git
   ```
2. 建立獨立的虛擬環境（跟公司系統用的環境分開，避免套件版本互相干擾）：
   ```bash
   mkvirtualenv --python=python3.10 riheng-backend-venv
   pip install -r ~/riheng-backend/requirements.txt
   ```
   （如果 `mkvirtualenv` 指令找不到，改用 `python3.10 -m venv ~/.virtualenvs/riheng-backend-venv && source ~/.virtualenvs/riheng-backend-venv/bin/activate` 再執行 `pip install`）
3. 到 PythonAnywhere 的 **Web** 分頁，找到現有的 Web App（`qo546.pythonanywhere.com`），點進去左下角 **WSGI configuration file** 的連結（就是 `/var/www/qo546_pythonanywhere_com_wsgi.py`）打開編輯。
4. **這一步先暫停，把這個檔案目前的完整內容貼給我**，我會照你原本公司系統的寫法，幫你寫好合併路徑分流後的版本（讓 `qo546.pythonanywhere.com/health-api/...` 導到這支健康 App 的後端，其餘路徑維持原本公司系統的行為），你再貼回去存檔即可。
5. Anthropic API 金鑰**只寫在這個 WSGI 檔案裡**（例如 `os.environ['ANTHROPIC_API_KEY'] = '你的金鑰'`），這個檔案完全不在任何 Git repo 裡，不會外流。
6. 存檔後回到 **Web** 分頁，點綠色的 **Reload qo546.pythonanywhere.com** 按鈕。
7. 測試：瀏覽器打開 `https://qo546.pythonanywhere.com/health-api/ping`，應該會看到 `{"status": "ok"}`。
