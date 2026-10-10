from fastapi import FastAPI

app = FastAPI(title="System Auditor")


@app.get("/hello")
def hello() -> dict[str, str]:
    return {"message": "Hello, world!"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
