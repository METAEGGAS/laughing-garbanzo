from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, firestore
import asyncio
import random
import time


# ============ اتصال Firebase ============
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

app = FastAPI()

# CORS للسماح لصفحة HTML بالاتصال
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ إعدادات السعر ============
price = 1.08500                # سعر البداية (EUR/USD)
trend = 0.0                    # اتجاه السوق
volatility = 0.00015           # التقلب (واقعي للفوركس)
CANDLE_DURATION = 60           # مدة الشمعة = 60 ثانية
TICKS_PER_CANDLE = 60          # 60 تحديث داخلي (بدون حفظ)


def generate_realistic_tick(current_price: float, trend_bias: float) -> float:
    """
    توليد سعر واقعي:
    - حركة براونية (Brownian motion)
    - انحياز اتجاه (trend bias)
    - عودة للمتوسط (mean reversion)
    - قفزات نادرة (news spikes)
    """
    noise = random.gauss(0, volatility)
    trend_component = trend_bias * volatility * 0.3
    mean_reversion = (1.08500 - current_price) * 0.001

    spike = 0
    if random.random() < 0.01:  # 1% احتمال قفزة
        spike = random.uniform(-volatility * 5, volatility * 5)

    return current_price + noise + trend_component + mean_reversion + spike


async def price_generator():
    global price, trend

    while True:
        # بداية شمعة جديدة — تقريب الوقت لأقرب دقيقة
        candle_start_time = int(time.time())
        candle_start_time = candle_start_time - (candle_start_time % 60)

        open_price = price
        high_price = price
        low_price = price

        # تغيير الاتجاه أحياناً
        if random.random() < 0.1:
            trend = random.uniform(-1, 1)

        print(f"\n🕐 بدء شمعة جديدة | Open: {open_price:.5f}")

        # توليد 60 tick داخلياً — بدون أي حفظ في Firestore
        for tick in range(TICKS_PER_CANDLE):
            price = generate_realistic_tick(price, trend)
            high_price = max(high_price, price)
            low_price = min(low_price, price)

            print(f"  ⏱  {tick+1}/60 | Price: {price:.5f} | H:{high_price:.5f} L:{low_price:.5f}")

            await asyncio.sleep(1)

        # ✅ بعد اكتمال 60 ثانية — حفظ الشمعة النهائية مرة واحدة فقط
        final_candle = {
            "time": candle_start_time,
            "open": round(open_price, 5),
            "high": round(high_price, 5),
            "low": round(low_price, 5),
            "close": round(price, 5),
            "active": False,
        }

        db.collection("candles") \
          .document("EURUSD") \
          .collection("1m") \
          .document(str(candle_start_time)) \
          .set(final_candle)

        print(f"✅ شمعة مكتملة ومحفوظة في Firestore:")
        print(f"   {final_candle}\n")


@app.on_event("startup")
async def start():
    asyncio.create_task(price_generator())


@app.get("/")
def root():
    return {"status": "running", "pair": "EURUSD", "current_price": round(price, 5)}
