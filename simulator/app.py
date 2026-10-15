from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from model import simulate, compare, optimize

app=FastAPI(title='VoltLab Simulator',version='0.1.0')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173'],allow_methods=['*'],allow_headers=['*'])
class Scenario(BaseModel):
    model_config=ConfigDict(extra='forbid')
    chemistry:str='NMC'
    series:int=4
    parallel:int=3
    current:float=8
    ambient:float=25
    cooling:float=1
    duration:float=60
    soc:float=90
    age:float=0
    variation:float=0
@app.get('/health')
def health(): return {'status':'ok'}
@app.post('/simulate')
def run(s:Scenario):
    try: return simulate(s.model_dump())
    except (ValueError,OverflowError) as e: raise HTTPException(422,str(e))
@app.post('/compare')
def run_comparison(s:Scenario):
    try: return compare(s.model_dump())
    except (ValueError,OverflowError) as e: raise HTTPException(422,str(e))

class OptimizationRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    config: Scenario
    constraints: dict = {}

@app.post('/optimize')
def run_optimizer(request: OptimizationRequest):
    try: return optimize(request.config.model_dump(), request.constraints)
    except (ValueError,OverflowError) as e: raise HTTPException(422,str(e))
