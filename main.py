import sqlite3, requests, matplotlib.pyplot as plt, schedule
from datetime import datetime, date, time, timedelta
from dotenv import load_dotenv
import io, os, sys
import time

EXCHANGE_COURSE_API = "https://currencyapi.net/api/v1/rates?base=USD&output=json&key=7c38f25db9620cc74a31ae5cb774d11b1b43"
DB_PATH = "ExchangeCourses.db"
TOKEN = ""
GetDataForDays = 30
users = [1683086489]

def getCurrentExchangeCourses():
    response = requests.get(EXCHANGE_COURSE_API)
    convRates = response.json()["rates"]
    usdToRub = convRates["RUB"]
    eurToRub = convRates["RUB"] / convRates["EUR"]
    cnyToRub = convRates["RUB"] / convRates["CNY"]
    return usdToRub, eurToRub, cnyToRub

def saveData(conn, usdToRub, eurToRub, cnyToRub):
    cur = conn.cursor()
    currDate = date.today().isoformat()
    currTime = datetime.now().time().isoformat()
    cmd = """INSERT INTO readings (date, time, usd, eur, cny) VALUES (?, ?, ?, ?, ?);"""
    data = (currDate, currTime, usdToRub, eurToRub, cnyToRub)
    cur.execute(cmd, data)
    conn.commit()

def init_db(db_path: str):
    path = os.path.dirname(os.path.realpath(__file__))
    conn = sqlite3.connect(os.path.join(path, db_path))
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS readings (id INTEGER PRIMARY KEY AUTOINCREMENT,date TEXT NOT NULL,time TEXT NOT NULL,usd REAL NOT NULL,eur REAL NOT NULL,cny REAL NOT NULL)")
    conn.commit()
    return conn

def updateData():
    conn = init_db(DB_PATH)
    try:
        usdToRub, eurToRub, cnyToRub = getCurrentExchangeCourses()
        saveData(conn, usdToRub, eurToRub, cnyToRub)
        print(f"Data updated at {datetime.now()}")
    except Exception as e:
        print(f"Error updating data: {e}")
    conn.close()

def getHistoricalData(days):
    NDaysAgo = (date.today() - timedelta(days)).isoformat()
    today = date.today().isoformat()
    conn = init_db(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * from readings WHERE date BETWEEN ? and ?", [NDaysAgo, today])
    data = cur.fetchall()
    conn.close()
    return data

def getPlot():
    data = getHistoricalData(GetDataForDays)
    if not data:
        print("No data available")
        return None
    dates = []
    dateTimes = []
    usd = []
    eur = []
    cny = []
    for el in data:
        dates.append(el[1])
        dateTm = datetime.strptime(el[1] + " " + el[2].split(".", 1)[0], "%Y-%m-%d %H:%M:%S")
        dateTimes.append(dateTm)
        usd.append(el[3])
        eur.append(el[4])
        cny.append(el[5])

    plt.figure(figsize=(12, 6))
    plt.title("Курсы валют")
    plt.plot(dateTimes, usd, label="USD", color='r')
    plt.plot(dateTimes, eur, label="EUR", color='b')
    plt.plot(dateTimes, cny, label="CNY", color='g')
    plt.xlabel("Время")
    plt.ylabel("Цена, руб")
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    for user in users:
        try:
            sendPhoto(buf, user, "С добрым утром, вот курсы валют")
            buf.seek(0)
        except Exception as e:
            print(f"Error sending to user {user}: {e}")
    return buf

def sendPhoto(bytes_io, chatId, caption):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    bytes_io.seek(0)
    files = {"photo": ("report.png", bytes_io, "image/png")}
    data = {"chat_id": chatId, "caption": caption}
    r = requests.post(url, data=data, files=files, timeout=30)
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    load_dotenv()
    print("Введите api для получения курсов валют: ")
    EXCHANGE_COURSE_API = input()
    TOKEN = os.getenv("BOT_TOKEN")

    conn = init_db(DB_PATH)
    conn.close()
    updateData()

    schedule.every(40).minutes.do(updateData)
    schedule.every().day.at("06:00").do(getPlot)

    print("Bot started")
    while True:
        schedule.run_pending()
        time_remaining = schedule.next_run() - datetime.now()
        print(f"Времени до следующего обновления: {time_remaining}")
        time.sleep(60)