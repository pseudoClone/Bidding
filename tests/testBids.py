import asyncio  # I won't use the threading library
import json
import httpx
import websockets
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = "http://127.0.0.1:8000"
WS_BASE = "ws://127.0.0.1:8000"

USERNAME = "david"
PASSWORD = os.getenv("DAVID_PASSWORD")

AUCTION_ID = "43e3b902-3832-4576-bc70-9653ffb9b0c2"


async def get_token():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/token",
            data={
                "username": USERNAME,
                "password": PASSWORD,
            },
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def receiver(ws):
    try:
        while True:
            message = await ws.recv()
            print("\nReceived:")
            print(message)

    except Exception as e:
        print("Receiver stopped:", repr(e))


async def sender(ws):
    while True:
        amount = await asyncio.to_thread(
            input, "\nBid amount (or press Enter to skip): "
        )
        if not amount:
            continue
        payload = {"amount": amount}
        print("Sending:", payload)

        await ws.send(json.dumps({"amount": amount}))


async def main():
    token = await get_token()

    print("Logged in successfully.")

    ws_url = f"{WS_BASE}/auctions/{AUCTION_ID}/ws?token={token}"

    async with websockets.connect(ws_url) as ws:
        print("Connected to websocket.")

        await asyncio.gather(
            receiver(ws),
            sender(ws),
        )


asyncio.run(main())
