from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/")
async def root(request: Request):
    return {
        "ip": request.client.host,
        "port": request.client.port,
    }
