from flask import Flask, jsonify, request
import aiohttp, asyncio, os

app = Flask(__name__)

@app.route('/mawaqit-today')
def prayer_times():
    url = f"https://mawaqit-api-c9jb.onrender.com/api/v1/mosquee-sahaba-creteil/prayer-times"

    async def get_times():
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return {"error": f"API returned status {resp.status}"}
                return await resp.json()

    data = asyncio.run(get_times())
    return jsonify(data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
