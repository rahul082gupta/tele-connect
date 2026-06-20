from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from src.predict import predict_churn

app = FastAPI(title="Churn Prediction API")

class Customer(BaseModel):
    __root__: Dict[str, Any]

class Customers(BaseModel):
    __root__: List[Dict[str, Any]]


@app.post("/predict")
async def predict(customer: Customer):
    try:
        data = customer.__root__
        out = predict_churn(data)
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch_predict")
async def batch_predict(customers: Customers):
    try:
        results = []
        for rec in customers.__root__:
            results.append(predict_churn(rec))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
