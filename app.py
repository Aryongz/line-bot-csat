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

# 🔑 เช็ก Token และ Secret ให้ชัวร์ (ห้ามมีช่องว่างเกิน)
token = 'Oy/LhqxJTW2IiWK3VZ7CTTw1qXdhr6yCWWeLqVciAes0UcXhC9wzVIGDBDA9Lt8vkfEPpsl/+zn7twLyr4CYiabYo9qai6pYiIH7VJQGUOpRLgO+XYhE7+A+M655p4Z7GmpRWCBpQEL0jMskSg13JgdB04t89/1O/w1cDnyilFU='
line_bot_api = LineBotApi(token)
handler = WebhookHandler('c02971df123b7ac293031ca8a6a9d3c0')

def get_data(mode, target_id, month=None):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=800,600")
    # ⚡️ สูตรประหยัดแรม
    options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    options.add_argument("--single-process")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 60)
        driver.get("https://backoffice-csat.com7.in/portal")
        
        # Login
        wait.until(EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'ชื่อผู้ใช้งาน')]"))).send_keys("22898")
        driver.find_element(By.XPATH, "//input[contains(@placeholder, 'รหัสผ่าน')]").send_keys("K@lf491883046" + Keys.ENTER)
        
        time.sleep(10)
        
        if month:
            date_picker = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ant-picker")))
            driver.execute_script("arguments[0].click();", date_picker)
            time.sleep(2)
            month_btn = wait.until(EC.element_to_be_clickable((By.XPATH, f"//div[@class='ant-picker-cell-inner' and text()='{month}']")))
            driver.execute_script("arguments[0].click();", month_btn)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", month_btn)
            time.sleep(2)

        search_branch = wait.until(EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'ค้นหารหัสสาขา')]")))
        search_branch.send_keys(str(target_id) if mode == "branch" else "251")
        driver.find_element(By.XPATH, "//button[contains(.,'ค้นหา')]").click()
        time.sleep(5)

        detail_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'รายละเอียด')]")))
        driver.execute_script("arguments[0].click();", detail_btn)
        time.sleep(10)

        if mode == "emp":
            search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ant-select-selection-search-input")))
            driver.execute_script("arguments[0].click();", search_input)
            for char in str(target_id):
                search_input.send_keys(char)
                time.sleep(0.1)
            time.sleep(5)
            suggestion = wait.until(EC.element_to_be_clickable((By.XPATH, f"//div[contains(@class, 'ant-select-item-option-content') and contains(., '{target_id}')]")))
            header_name = suggestion.text.strip()
            driver.execute_script("arguments[0].click();", suggestion)
            time.sleep(15)
        else:
            header_name = f"สรุปภาพรวมสาขา {target_id}"
            if month: header_name += f" (เดือน {month})"
            time.sleep(12)

        page_text = driver.find_element(By.TAG_NAME, "body").text
        def get_val(label_text):
            try:
                xpath = f"//*[contains(text(), '{label_text}')]/following::*[self::span or self::div][1]"
                return driver.find_element(By.XPATH, xpath).text.replace("ครั้ง","").replace("บิล","").strip()
            except: return "0"

        bills = get_val("จำนวนบิลทั้งหมด")
        answered = get_val("จำนวนการตอบแบบสอบถาม")
        target = get_val("เป้าหมาย")
        rate = "0%"
        try:
            b = float(bills.replace(',', ''))
            a = float(answered.replace(',', ''))
            if b > 0: rate = f"{(a/b)*100:.2f}%"
        except: pass
        
        nps = "0"
        try:
            match = re.search(r'Promoters\D*?([0-9.]+)%', page_text, re.IGNORECASE)
            nps = match.group(1) if match else "0"
        except: pass

        return (f"📊 {header_name}\n━━━━━━━━━━━━━━━\n"
                f"📉 อัตราการตอบ: {rate}\n✅ ตอบแล้ว: {answered} ครั้ง\n🎯 เป้าหมาย: {target} ครั้ง\n🧾 จำนวนบิล: {bills} บิล\n"
                f"⭐ คะแนน NPS: {nps}\n━━━━━━━━━━━━━━━")
    except Exception as e:
        return f"❌ ระบบขัดข้อง (แรมอาจจะเต็ม) ลองใหม่นะครับน๊อตตี้"
    finally:
        if driver: driver.quit()
        os.system("pkill -f chrome")
        gc.collect()

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
    msg = event.message.text.replace(" ", "")
    
    # 💡 ระบบเช็กชื่อกลุ่ม/ส่วนตัว
    target_id = event.source.group_id if event.source.type == 'group' else event.source.user_id

    # ✅ ด่านทดสอบ 1: พิมพ์ Test ต้องตอบ
    if msg.lower() == "test":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="บอทยังมีชีวิตอยู่ครับน๊อตตี้! ลองเรียกรายงานดูได้เลย"))
        return

    month_match = re.search(r'เดือน([ก-ฮ]\.[ค-ศ]\.)', msg)
    target_month = month_match.group(1) if month_match else None
    
    if "รายงานสาขา" in msg:
        try:
            branch_id = re.search(r'รายงานสาขา(\d+)', msg).group(1)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🏢 รับทราบครับ! กำลังดึงสรุปสาขา {branch_id}..."))
            line_bot_api.push_message(target_id, TextSendMessage(text=get_data("branch", branch_id, target_month)))
        except: pass
    elif "รายงาน" in msg:
        try:
            emp_id = re.search(r'รายงาน(\d+)', msg).group(1)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🔎 รับทราบครับ! กำลังดึงข้อมูลพนักงาน {emp_id}..."))
            line_bot_api.push_message(target_id, TextSendMessage(text=get_data("emp", emp_id, target_month)))
        except: pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
