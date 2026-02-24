# ใช้ Python เวอร์ชัน 3.9
FROM python:3.9

# ติดตั้ง Google Chrome สำหรับ Selenium
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get -y update
RUN apt-get install -y google-chrome-stable

# ตั้งค่าโฟลเดอร์ทำงาน
WORKDIR /app

# ก๊อปปี้ไฟล์และติดตั้งไลบรารี
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ก๊อปปี้โค้ดทั้งหมด
COPY . .

# คำสั่งรันบอท (ตั้ง Timeout ไว้ 120 วินาที เผื่อเวลาเว็บโหลด 1 นาทีของเรา)
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--timeout", "120"]