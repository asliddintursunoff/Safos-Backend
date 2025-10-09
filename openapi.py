import requests

url = "http://127.0.0.1:8000/openapi.json"
r = requests.get(url)
with open("openapi.json", "w", encoding="utf-8") as f:
    f.write(r.text)
