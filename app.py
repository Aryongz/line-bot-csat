import time
import re
import os
import gc
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

token = 'Oy/LhqxJTW2IiWK3VZ7CTTw1qXdhr6yCWWeLqVciAes0UcXhC9wzVIGDBDA9Lt8vkfEPpsl/+zn7twLyr4CYiabYo9qai6pYiIH7VJQGUOpRLgO+XYhE7+A+M655p4Z7GmpRWCBpQEL0jMskSg13JgdB04t89/1O/w1cDnyilFU='
line_bot_api = LineBotApi(token)
handler = WebhookHandler('c02971df123b7ac293031ca8a6a9d3c0')

def get_data(mode, target_id, month=None):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=640,480")
    # ⚡️ สูตรเด็ด: บังคับใช้ Process เดียว (ประหยัดแรม 50%)
    options.add_argument("--single-process")
    options.add_argument("--disable-extensions")
    # ⚡️ ไม่โหลดแม้กระทั่ง CSS และฟอนต์ (หน้าเว็บจะเหลือแต่ตัวหนังสือ)
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts": 2
    })
    
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        # ตั้งเวลา Timeout ให้สั้นลง (ถ้า 30 วิยังไม่เสร็จ ให้พังไปเลยดีกว่าค้าง)
        driver.set_page_load_timeout(30)
        wait = WebDriverWait(driver, 30)
        
        driver.get("https://backoffice-csat.com7.in/portal")
        # ... (Login และดึงข้อมูลตามเดิม) ...
        # (ผมแนะนำให้ใส่ time.sleep ให้น้อยที่สุดเท่าที่จำเป็น)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try: handler.handle(body, signature)
    except InvalidSignatureError: abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    target_id = event.source.group_id if event.source.type == 'group' else event.source.user_id

    # ดักคำสั่งให้กว้างขึ้น
    if "รายงานสาขา" in msg:
        match = re.search(r'รายงานสาขา\s*(\d+)', msg)
        if match:
            branch_id = match.group(1)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🏢 รับทราบครับ! กำลังดึงสรุปสาขา {branch_id}..."))
            line_bot_api.push_message(target_id, TextSendMessage(text=get_data("branch", branch_id)))
    elif "รายงาน" in msg:
        match = re.search(r'รายงาน\s*(\d+)', msg)
        if match:
            emp_id = match.group(1)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🔎 รับทราบครับ! กำลังดึงข้อมูลพนักงาน {emp_id}..."))
            line_bot_api.push_message(target_id, TextSendMessage(text=get_data("emp", emp_id)))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

