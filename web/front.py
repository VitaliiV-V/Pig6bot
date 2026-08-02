from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="P6T Market API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def index():
    return FileResponse("index.html")


@app.get("/styles.css")
def get_styles():
    return FileResponse("styles.css")


@app.get("/marketApi.js")
def get_market_api():
    return FileResponse("marketApi.js")


@app.get("/app.js")
def get_market_api_alias():
    return FileResponse("app.js")
