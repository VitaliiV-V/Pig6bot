from config.logging_config import configure_logging

configure_logging()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
import uvicorn

from web.policy import router as policy_router

app = FastAPI(title="Pig 7 Gara")
app.include_router(policy_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def index():
    return FileResponse("web/index.html")


@app.get("/common.css")
def get_styles():
    return FileResponse("web/common.css")


@app.get("/site.js")
def get_styles():
    return FileResponse("web/site.js")


@app.exception_handler(404)
async def not_found(request, exc):

    return HTMLResponse(
        open("web/404.html", encoding="utf-8").read(),
        status_code=404,
    )


def run_api():
    uvicorn.run(app, host="0.0.0.0", port=2322, log_level="info")


if __name__ == "__main__":
    run_api()
