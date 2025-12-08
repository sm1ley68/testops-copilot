from fastapi import FastAPI

app = FastAPI(title="TestOps Copilot API")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
