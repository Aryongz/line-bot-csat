import time
import re
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

# --- [ตั้งค่า LINE] ---
token = 'Oy/LhqxJTW2IiWK3VZ7CTTw1qXdhr6yCWWeLqVciAes0UcXhC9wzVIGDBDA9Lt8vkfEPpsl/+zn7twLyr4CYiabYo9qai6pYiIH7VJQGUOpRLgO+XYhE7+A+M655p4Z7GmpRWCBpQEL0jMskSg13JgdB04t89/1O/w1cDnyilFU='
line_bot_api = LineBotApi(token)
handler = WebhookHandler('c02971df123b7ac293031ca8a6a9d3c0')

def get_employee_report(emp_id):
    options = Options()
    # เปิดโหมด Headless ทำงานเบื้องหลัง ไม่แสดงหน้าจอ
    options.add_argument("--headless") 
    options.add_argument("--disable-gpu") # เพิ่มความเสถียรเมื่อรันบน Server
    options.add_argument("--no-sandbox")  # ป้องกัน Error สิทธิ์การเข้าถึงบน Server
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 45)
    
    try:
        # 1. Login
        driver.get("https://backoffice-csat.com7.in/portal")
        user_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'ชื่อผู้ใช้งาน')]")))
        user_field.send_keys("22898")
        pass_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'รหัสผ่าน')]")))
        pass_field.send_keys("K@lf491883046" + Keys.ENTER)
        
        time.sleep(12) 
        
        # 2. ข้ามการค้นหาสาขา แล้วพุ่งไปคลิกปุ่มรายละเอียดเลยเพื่อความไว
        detail_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'รายละเอียด')]")))
        driver.execute_script("arguments[0].click();", detail_btn)
        time.sleep(8)

        # 3. ค้นหาพนักงาน
        search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ant-select-selection-search-input")))
        driver.execute_script("arguments[0].click(); arguments[0].focus();", search_input)
        for char in str(emp_id):
            search_input.send_keys(char)
            time.sleep(0.2)
        
        time.sleep(5) 
        suggestion = wait.until(EC.element_to_be_clickable((By.XPATH, f"//div[contains(@class, 'ant-select-item-option-content') and contains(., '{emp_id}')]")))
        full_name = suggestion.text.strip()
        driver.execute_script("arguments[0].click();", suggestion)
        
        time.sleep(15) 

        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text
        except:
            page_text = ""

        def get_val(label_text):
            try:
                xpath = f"//*[contains(text(), '{label_text}')]/following::*[self::span or self::div][1]"
                val = driver.find_element(By.XPATH, xpath).text
                return val.replace("ครั้ง", "").replace("บิล", "").replace(" ", "").strip()
            except:
                return "0"

        # 4. ดึงข้อมูลตัวเลขดิบ
        bills = get_val("จำนวนบิลทั้งหมด")
        answered = get_val("จำนวนการตอบแบบสอบถาม")
        target = get_val("เป้าหมาย")

        # 5. คำนวณอัตราการตอบด้วยสมการคณิตศาสตร์ (ชัวร์ 100%)
        rate = "0%"
        try:
            b = float(bills.replace(',', ''))
            a = float(answered.replace(',', ''))
            if b > 0:
                rate = f"{(a / b) * 100:.2f}%"
        except:
            pass

        # 6. สแกนหา NPS จาก Promoters
        nps = "0"
        try:
            if page_text:
                match = re.search(r'Promoters\D*?([0-9.]+)%', page_text, re.IGNORECASE)
                if match:
                    nps = match.group(1)
            
            if nps == "0":
                raw_nps = driver.find_element(By.XPATH, "//*[contains(text(), 'Promoters')]/following::*[contains(text(), '%')][1]").text
                nps = raw_nps.split('(')[0].replace('%', '').strip()
        except:
            pass

        # ประกอบร่าง (ลบคำว่า สาขา 251 ออก เพื่อให้เป็นรายงานส่วนกลางที่ใช้ได้กับทุกคน)
        report = (
            f"👤 รายงานผลงานพนักงาน\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🆔 รหัส: {emp_id}\n"
            f"📛 ชื่อ: {full_name}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📉 อัตราการตอบ: {rate}\n"
            f"✅ ตอบแล้ว: {answered} ครั้ง\n"
            f"🎯 เป้าหมาย: {target} ครั้ง\n"
            f"🧾 จำนวนบิล: {bills} บิล\n"
            f"⭐ คะแนน NPS: {nps}\n"
            f"━━━━━━━━━━━━━━━"
        )
        return report

    except Exception as e:
        return f"❌ เกิดข้อผิดพลาดในการดึงข้อมูล (รหัส {emp_id})"
    finally:
        driver.quit()

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    if "รายงาน" in msg:
        emp_id = msg.replace("รายงาน", "").strip()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"กำลังรวบรวมข้อมูลรหัส {emp_id} รอสักครู่นะครับ..."))
        result = get_employee_report(emp_id)
        line_bot_api.push_message(event.source.user_id, TextSendMessage(text=result))

if __name__ == "__main__":
    app.run(port=5000)