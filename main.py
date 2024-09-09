from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/")
async def root(request: Request):
    print(request.client)
    return {
        "ip": request.client.host,
        "port": request.client.port,
    }
