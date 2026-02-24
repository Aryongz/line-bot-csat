import time
import re
import os
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

def get_employee_report(emp_id):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # เพิ่ม User-Agent ให้เหมือนคนจริงๆ ใช้เครื่อง Mac
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 60) # เพิ่มเวลารอเป็น 60 วินาที
    
    try:
        driver.get("https://backoffice-csat.com7.in/portal")
        user_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'ชื่อผู้ใช้งาน')]")))
        user_field.send_keys("22898")
        pass_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'รหัสผ่าน')]")))
        pass_field.send_keys("K@lf491883046" + Keys.ENTER)
        
        time.sleep(15) # รอหน้าแรกโหลดนานขึ้นนิดนึงบน Server
        
        detail_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'รายละเอียด')]")))
        driver.execute_script("arguments[0].click();", detail_btn)
        time.sleep(10)

        search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ant-select-selection-search-input")))
        driver.execute_script("arguments[0].click();", search_input)
        for char in str(emp_id):
            search_input.send_keys(char)
            time.sleep(0.3) # พิมพ์ช้าลงนิดนึงให้ระบบหาเจอ
        
        time.sleep(7) 
        suggestion = wait.until(EC.element_to_be_clickable((By.XPATH, f"//div[contains(@class, 'ant-select-item-option-content') and contains(., '{emp_id}')]")))
        full_name = suggestion.text.strip()
        driver.execute_script("arguments[0].click();", suggestion)
        
        time.sleep(20) # รอหน้าแสดงผล NPS โหลด (หัวใจสำคัญ)

        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        def get_val(label_text):
            try:
                xpath = f"//*[contains(text(), '{label_text}')]/following::*[self::span or self::div][1]"
                return driver.find_element(By.XPATH, xpath).text.replace("ครั้ง","").replace("บิล","").strip()
            except: return "0"

        bills = get_val("จำนวนบิลทั้งหมด")
        answered = get_val("จำนวนการตอบแบบสอบถาม")
        target = get_val("เป้าหมาย")

        # คำนวณอัตราตอบ
        rate = "0%"
        try:
            b = float(bills.replace(',', ''))
            a = float(answered.replace(',', ''))
            if b > 0: rate = f"{(a/b)*100:.2f}%"
        except: pass

        # สแกนหา NPS
        nps = "0"
        try:
            match = re.search(r'Promoters\D*?([0-9.]+)%', page_text, re.IGNORECASE)
            nps = match.group(1) if match else "0"
            if nps == "0":
                nps = driver.find_element(By.XPATH, "//*[contains(text(), 'Promoters')]/following::*[contains(text(), '%')][1]").text.split('(')[0].replace('%','').strip()
        except: pass

        return (f"👤 รายงานผลงานพนักงาน\n━━━━━━━━━━━━━━━\n🆔 รหัส: {emp_id}\n📛 ชื่อ: {full_name}\n━━━━━━━━━━━━━━━\n"
                f"📉 อัตราการตอบ: {rate}\n✅ ตอบแล้ว: {answered} ครั้ง\n🎯 เป้าหมาย: {target} ครั้ง\n🧾 จำนวนบิล: {bills} บิล\n"
                f"⭐ คะแนน NPS: {nps}\n━━━━━━━━━━━━━━━")
    except Exception as e:
        return f"❌ เกิดข้อผิดพลาดในการดึงข้อมูล (รหัส {emp_id})"
    finally:
        driver.quit()

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try: handler.handle(body, signature)
    except InvalidSignatureError: abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    if "รายงาน" in msg:
        emp_id = msg.replace("รายงาน", "").strip()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"กำลังดึงข้อมูลรหัส {emp_id} จาก Server... (อาจใช้เวลา 1-2 นาทีครับ)"))
        result = get_employee_report(emp_id)
        line_bot_api.push_message(event.source.user_id, TextSendMessage(text=result))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
