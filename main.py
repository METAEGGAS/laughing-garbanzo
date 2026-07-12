from fastapi import FastAPI
import firebase_admin
from firebase_admin import credentials, firestore
import asyncio
import random
import time


# اتصال Firebase
cred = credentials.Certificate(
    "serviceAccountKey.json"
)

firebase_admin.initialize_app(cred)

db = firestore.client()


app = FastAPI()


price = 100.00000


async def price_generator():

    global price

    while True:

        old_price = price

        price += random.uniform(-0.05, 0.05)

        candle = {
            "time": int(time.time()),
            "open": round(old_price, 5),
            "high": round(max(old_price, price), 5),
            "low": round(min(old_price, price), 5),
            "close": round(price, 5),
            "active": True
        }


        # حفظ السعر في Firestore
        db.collection("candles") \
          .document("EURUSD") \
          .collection("1m") \
          .document(str(candle["time"])) \
          .set(candle)


        print(candle)

        await asyncio.sleep(1)



@app.on_event("startup")
async def start():

    asyncio.create_task(price_generator())
