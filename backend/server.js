
import express from 'express';
import cors from 'cors';
import { z } from 'zod';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';

const app = express();

const allowedOrigins = [
  'http://localhost:5173',
  'https://voltlab-goatofiiit.onrender.com',
  process.env.FRONTEND_ORIGIN
].filter(Boolean);

app.use(cors({
  origin(origin, callback) {
    if (!origin || allowedOrigins.includes(origin)) {
      return callback(null, true);
    }
    return callback(new Error(`CORS blocked origin: ${origin}`));
  },
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

app.use(express.json({ limit: '50kb' }));

const SIM_URL = (
  process.env.SIM_URL || 'https://voltlab-yeyo.onrender.com'
).replace(/\/$/, '');

const dbPath = path.resolve('designs.json');

const scenario = z.object({
  chemistry: z.enum(['NMC', 'LFP']),
  series: z.number().int().min(1).max(24),
  parallel: z.number().int().min(1).max(24),
  current: z.number().min(0).max(200),
  ambient: z.number().min(-10).max(60),
  cooling: z.number().min(0.2).max(8),
  duration: z.number().min(1).max(240),
  soc: z.number().min(0).max(100),
  age: z.number().min(0).max(100),
  variation: z.number().min(0).max(20)
}).strict();

const getDesigns = async () => {
  try {
    return JSON.parse(await fs.readFile(dbPath, 'utf8'));
  } catch (error) {
    if (error.code === 'ENOENT') return [];
    throw error;
  }
};

// Basic API homepage
app.get('/', (req, res) => {
  res.json({ name: 'VoltLab API', status: 'ok' });
});

// Health check
app.get('/api/health', async (req, res) => {
  try {
    const response = await fetch(`${SIM_URL}/health`);
    res.status(response.ok ? 200 : 503).json({
      api: 'ok',
      simulator: response.ok ? 'ok' : 'unavailable'
    });
  } catch {
    res.status(503).json({
      api: 'ok',
      simulator: 'unavailable'
    });
  }
});

// Simulation and comparison
for (const endpoint of ['simulate', 'compare']) {
  app.post(`/api/${endpoint}`, async (req, res) => {
    const parsed = scenario.safeParse(req.body);

    if (!parsed.success) {
      return res.status(400).json({
        error: 'Invalid scenario',
        details: parsed.error.flatten()
      });
    }

    try {
      const response = await fetch(`${SIM_URL}/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed.data)
      });

      const payload = await response.json();
      return res.status(response.status).json(payload);
    } catch {
      return res.status(503).json({
        error: 'Simulation service unavailable. Check SIM_URL and the Python service.'
      });
    }
  });
}

// Optimizer
app.post('/api/optimize', async (req, res) => {
  const body = req.body ?? {};

  const parsed = scenario.safeParse(body.config);

  const constraints = z.object({
    minEnergyWh: z.number().min(10).max(10000),
    maxTempC: z.number().min(20).max(80),
    maxCostUsd: z.number().min(1).max(100000),
    maxMassKg: z.number().min(0.1).max(1000)
  }).safeParse(body.constraints);

  if (!parsed.success || !constraints.success) {
    return res.status(400).json({
      error: 'Invalid optimizer inputs',
      details: {
        config: parsed.success
          ? undefined
          : parsed.error.flatten(),
        constraints: constraints.success
          ? undefined
          : constraints.error.flatten()
      }
    });
  }

  try {
    const response = await fetch(`${SIM_URL}/optimize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        config: parsed.data,
        constraints: constraints.data
      })
    });

    const payload = await response.json();
    return res.status(response.status).json(payload);
  } catch {
    return res.status(503).json({
      error: 'Simulation service unavailable. Check SIM_URL and the Python service.'
    });
  }
});

// Get saved designs
app.get('/api/designs', async (req, res) => {
  try {
    return res.json(await getDesigns());
  } catch {
    return res.status(500).json({
      error: 'Unable to read designs'
    });
  }
});

// Save a design
app.post('/api/designs', async (req, res) => {
  const body = req.body ?? {};

  const parsed = scenario.safeParse(body.config);
  const name = z.string().trim().min(1).max(80).safeParse(body.name);

  if (!parsed.success || !name.success) {
    return res.status(400).json({ error: 'Invalid design' });
  }

  try {
    const all = await getDesigns();

    const design = {
      id: crypto.randomUUID(),
      name: name.data,
      config: parsed.data,
      createdAt: new Date().toISOString()
    };

    all.unshift(design);

    await fs.writeFile(
      dbPath,
      JSON.stringify(all.slice(0, 100), null, 2)
    );

    return res.status(201).json(design);
  } catch {
    return res.status(500).json({
      error: 'Unable to save design'
    });
  }
});

const port = Number(process.env.PORT || 3001);

app.listen(port, '0.0.0.0', () => {
  console.log(`VoltLab API listening on port ${port}`);
});
