import express from 'express';
import cors from 'cors';
import { z } from 'zod';
import fs from 'node:fs/promises';
import path from 'node:path';
const app=express(); app.use(cors({origin:process.env.FRONTEND_ORIGIN || 'http://localhost:5173'})); app.use(express.json({limit:'50kb'}));
const SIM_URL=process.env.SIM_URL || 'http://localhost:8000';
const dbPath=path.resolve('designs.json');
const scenario=z.object({chemistry:z.enum(['NMC','LFP']),series:z.number().int().min(1).max(24),parallel:z.number().int().min(1).max(24),current:z.number().min(0).max(200),ambient:z.number().min(-10).max(60),cooling:z.number().min(0.2).max(8),duration:z.number().min(1).max(240),soc:z.number().min(0).max(100),age:z.number().min(0).max(100),variation:z.number().min(0).max(20)}).strict();
const getDesigns=async()=>{try{return JSON.parse(await fs.readFile(dbPath,'utf8'))}catch(e){if(e.code==='ENOENT')return [];throw e}};
app.get('/api/health',async(req,res)=>{try{const r=await fetch(`${SIM_URL}/health`);res.json({api:'ok',simulator:r.ok?'ok':'unavailable'})}catch{res.status(503).json({api:'ok',simulator:'unavailable'})}});
for(const endpoint of ['simulate','compare'])app.post(`/api/${endpoint}`,async(req,res)=>{
 const parsed=scenario.safeParse(req.body);if(!parsed.success)return res.status(400).json({error:'Invalid scenario',details:parsed.error.flatten()});
 try{const upstream=await fetch(`${SIM_URL}/${endpoint}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(parsed.data)});const payload=await upstream.json();res.status(upstream.status).json(payload)}catch{res.status(503).json({error:'Simulation service unavailable. Start FastAPI on port 8000.'})}
});
app.post('/api/optimize',async(req,res)=>{
 const parsed=scenario.safeParse(req.body.config);
 const constraints=z.object({minEnergyWh:z.number().min(10).max(10000),maxTempC:z.number().min(20).max(80),maxCostUsd:z.number().min(1).max(100000),maxMassKg:z.number().min(0.1).max(1000)}).safeParse(req.body.constraints);
 if(!parsed.success||!constraints.success)return res.status(400).json({error:'Invalid optimizer inputs',details:{config:parsed.success?undefined:parsed.error.flatten(),constraints:constraints.success?undefined:constraints.error.flatten()}});
 try{const upstream=await fetch(`${SIM_URL}/optimize`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({config:parsed.data,constraints:constraints.data})});const payload=await upstream.json();res.status(upstream.status).json(payload)}catch{res.status(503).json({error:'Simulation service unavailable. Start FastAPI on port 8000.'})}
});
app.get('/api/designs',async(req,res)=>{try{res.json(await getDesigns())}catch{res.status(500).json({error:'Unable to read designs'})}});
app.post('/api/designs',async(req,res)=>{const parsed=scenario.safeParse(req.body.config);const name=z.string().trim().min(1).max(80).safeParse(req.body.name);if(!parsed.success||!name.success)return res.status(400).json({error:'Invalid design'});try{const all=await getDesigns();const design={id:crypto.randomUUID(),name:name.data,config:parsed.data,createdAt:new Date().toISOString()};all.unshift(design);await fs.writeFile(dbPath,JSON.stringify(all.slice(0,100),null,2));res.status(201).json(design)}catch{res.status(500).json({error:'Unable to save design'})}});
const port=Number(process.env.PORT||3001);app.listen(port,()=>console.log(`VoltLab API on http://localhost:${port}`));
