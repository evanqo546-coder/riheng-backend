import json
import logging
import os
import re

from anthropic import Anthropic
from flask import Flask, jsonify, request

app = Flask(__name__)

MODEL_NAME = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

# 獨立的日誌檔案，只記錄這個 App 自己的事件，跟公司系統（extinguisher_system）
# 共用同一個 PythonAnywhere Web App，但 log 完全分開、互不干擾。
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.log")
logger = logging.getLogger("riheng_backend")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _file_handler = logging.FileHandler(LOG_PATH)
    _file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(_file_handler)

PROMPT_INSTRUCTIONS = """你是一位營養師助手，任務是根據使用者提供的餐點描述和/或照片，估算這一餐的營養資訊。

請只回傳一個 JSON 物件，不要有任何其他文字、不要用 Markdown code fence 包起來，格式如下：
{
  "items": [{"name": "食物名稱", "amount_g": 份量估計（公克，數字）, "calories": 該項熱量估計（大卡，數字）}],
  "total_calories": 整餐總熱量估計（大卡，數字）,
  "total_protein_g": 蛋白質總量估計（公克，數字）,
  "total_carbs_g": 碳水化合物總量估計（公克，數字）,
  "total_fat_g": 脂肪總量估計（公克，數字）,
  "confidence_note": "簡短說明這次估算的不確定性來源，例如份量是用目測推估、或照片角度影響判斷，用繁體中文回答"
}

如果只有文字描述、沒有照片，就純粹依文字描述估算。如果同時有照片和文字，兩者互相參考。所有數字欄位都要是數字，不要帶單位文字。"""


def extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("模型回應中找不到 JSON 物件")
    return json.loads(text[start:end + 1])


@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok"})


@app.route("/estimate-meal", methods=["POST"])
def estimate_meal():
    shared_secret = os.environ.get("BACKEND_SHARED_SECRET")
    if not shared_secret:
        logger.error("BACKEND_SHARED_SECRET 未設定")
        return jsonify({"error": "伺服器尚未設定 BACKEND_SHARED_SECRET"}), 500
    if request.headers.get("X-App-Secret") != shared_secret:
        logger.warning("拒絕未授權的請求：來源 IP=%s", request.remote_addr)
        return jsonify({"error": "unauthorized"}), 401

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY 未設定")
        return jsonify({"error": "伺服器尚未設定 ANTHROPIC_API_KEY"}), 500

    data = request.get_json(silent=True) or {}
    description = (data.get("description") or "").strip()
    photo_base64 = data.get("photo_base64")
    photo_media_type = data.get("photo_media_type", "image/jpeg")

    logger.info(
        "收到 /estimate-meal 請求：has_description=%s has_photo=%s",
        bool(description), bool(photo_base64),
    )

    if not description and not photo_base64:
        return jsonify({"error": "請至少提供文字描述或照片"}), 400

    content = []
    if photo_base64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": photo_media_type,
                "data": photo_base64,
            },
        })
    text_block = PROMPT_INSTRUCTIONS
    if description:
        text_block += f"\n\n使用者描述：{description}"
    content.append({"type": "text", "text": text_block})

    client = Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1024,
            messages=[{"role": "user", "content": content}],
        )
    except Exception as exc:  # 直接把上游錯誤原因回傳給前端方便除錯
        logger.error("呼叫 Claude API 失敗：%s", exc)
        return jsonify({"error": f"呼叫 Claude API 失敗：{exc}"}), 502

    raw_text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    try:
        result = extract_json(raw_text)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.error("無法解析模型回應：%s | raw=%s", exc, raw_text)
        return jsonify({"error": f"無法解析模型回應：{exc}", "raw": raw_text}), 502

    logger.info("估算成功：total_calories=%s", result.get("total_calories"))
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
