from controller import circuit_controller
from fastapi import FastAPI
app = FastAPI(
    title="Simulador F1 API",
    description="API para simulação de corridas e histórico de circuitos e layouts da Fórmula 1.",
    version="1.0.0",
)

app.include_router(circuit_controller.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)