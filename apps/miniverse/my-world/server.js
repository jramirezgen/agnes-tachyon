import { createServer, request as httpRequest } from 'node:http';
import { createServer as createNetServer } from 'node:net';
import { readFileSync, writeFileSync, appendFileSync, existsSync, statSync, mkdirSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { MiniverseServer } from '@miniverse/server';

const requestedPort = parseInt(process.env.PORT || '4331', 10);

function canListen(port) {
  return new Promise((resolve) => {
    const tester = createNetServer();
    tester.once('error', () => resolve(false));
    tester.once('listening', () => {
      tester.close(() => resolve(true));
    });
    tester.listen(port, '0.0.0.0');
  });
}

async function findPortPair(startPort) {
  let candidate = startPort;
  for (let index = 0; index < 100; index += 1) {
    const webFree = await canListen(candidate);
    const apiFree = await canListen(candidate + 1);
    if (webFree && apiFree) {
      return { port: candidate, apiPort: candidate + 1 };
    }
    candidate += 10;
  }
  throw new Error(`No se encontro un par libre de puertos desde ${startPort}`);
}

const { port, apiPort } = await findPortPair(requestedPort);

// Start miniverse API + WebSocket server on internal port
const mv = new MiniverseServer({ port: apiPort, publicDir: './public' });
await mv.start();
console.log(`[miniverse] API on internal port ${apiPort}`);
if (port !== requestedPort) {
  console.log(`[miniverse-public] puerto solicitado ${requestedPort} ocupado, usando ${port}`);
}

const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml', '.woff2': 'font/woff2',
};

const runtimeRoot = path.resolve(process.env.MINIVERSE_RUNTIME_ROOT || '../my-miniverse');
const runtimeGeneratedDir = path.join(runtimeRoot, 'generated');
const commandFile = path.join(runtimeGeneratedDir, 'command_center_commands.jsonl');
const stateFile = path.join(runtimeGeneratedDir, 'command_center_state.json');
const snapshotsDir = path.join(runtimeGeneratedDir, 'snapshots');

mkdirSync(runtimeGeneratedDir, { recursive: true });
mkdirSync(snapshotsDir, { recursive: true });

const distDir = path.resolve('dist');
const publicDir = path.resolve('public');

function readJsonSafe(filePath, fallback) {
  if (!existsSync(filePath)) return fallback;
  try {
    return JSON.parse(readFileSync(filePath, 'utf-8'));
  } catch {
    return fallback;
  }
}

function nowIso() {
  return new Date().toISOString();
}

function makeCommand(action, body) {
  const rand = Math.random().toString(36).slice(2, 8);
  return {
    id: `cc_${Date.now()}_${rand}`,
    issuedAt: nowIso(),
    action,
    target: body.target ?? 'all',
    message: body.message ?? '',
    params: body.params ?? {},
    source: body.source ?? 'ui',
  };
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => {
      data += chunk;
      if (data.length > 1024 * 1024) {
        reject(new Error('Payload demasiado grande'));
      }
    });
    req.on('end', () => resolve(data));
    req.on('error', reject);
  });
}

function tryServe(res, filePath) {
  if (!existsSync(filePath) || !statSync(filePath).isFile()) return false;
  const ext = path.extname(filePath);
  res.writeHead(200, {
    'Content-Type': MIME[ext] || 'application/octet-stream',
    'Access-Control-Allow-Origin': '*',
    'Cache-Control': ext === '.html' ? 'no-cache' : 'public, max-age=86400',
  });
  res.end(readFileSync(filePath));
  return true;
}

function proxy(req, res) {
  const opts = { hostname: '127.0.0.1', port: apiPort, path: req.url, method: req.method, headers: { ...req.headers, host: `127.0.0.1:${apiPort}` } };
  const p = httpRequest(opts, (pRes) => {
    res.writeHead(pRes.statusCode, pRes.headers);
    pRes.pipe(res);
  });
  p.on('error', () => { res.writeHead(502); res.end('Bad gateway'); });
  req.pipe(p);
}

const server = createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${port}`);

  // CORS preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    });
    res.end();
    return;
  }

  // Centro de Comando: estado runtime
  if (req.method === 'GET' && url.pathname === '/api/command-center/status') {
    const state = readJsonSafe(stateFile, {
      updatedAt: nowIso(),
      runtime: {
        pausedAll: false,
        pausedAgents: {},
        parameters: {},
        lastCommandId: null,
      },
      agents: [],
      tasks: { total: 0, byStatus: {}, recent: [] },
      responses: [],
    });
    res.writeHead(200, {
      'Content-Type': 'application/json; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
    });
    res.end(JSON.stringify(state));
    return;
  }

  // Centro de Comando: snapshots guardados
  if (req.method === 'GET' && url.pathname === '/api/command-center/snapshots') {
    let files = [];
    try {
      files = readdirSync(snapshotsDir)
        .filter((name) => name.endsWith('.json'))
        .sort()
        .reverse()
        .slice(0, 20);
    } catch {
      files = [];
    }
    res.writeHead(200, {
      'Content-Type': 'application/json; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
    });
    res.end(JSON.stringify({ snapshots: files }));
    return;
  }

  // Centro de Comando: enviar comandos al runtime
  if (req.method === 'POST' && url.pathname === '/api/command-center/command') {
    readBody(req)
      .then((rawBody) => {
        let body = {};
        try {
          body = rawBody ? JSON.parse(rawBody) : {};
        } catch {
          res.writeHead(400, {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
          });
          res.end(JSON.stringify({ ok: false, error: 'JSON invalido' }));
          return;
        }

        const action = String(body.action || '').trim();
        const allowed = new Set(['pause_all', 'resume_all', 'pause_agent', 'resume_agent', 'save_snapshot', 'set_params', 'dispatch', 'spark_conversation']);
        if (!allowed.has(action)) {
          res.writeHead(400, {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
          });
          res.end(JSON.stringify({ ok: false, error: 'Accion no soportada' }));
          return;
        }

        const cmd = makeCommand(action, body);
        appendFileSync(commandFile, `${JSON.stringify(cmd)}\n`, 'utf-8');

        res.writeHead(202, {
          'Content-Type': 'application/json; charset=utf-8',
          'Access-Control-Allow-Origin': '*',
        });
        res.end(JSON.stringify({ ok: true, command: cmd }));
      })
      .catch((err) => {
        res.writeHead(500, {
          'Content-Type': 'application/json; charset=utf-8',
          'Access-Control-Allow-Origin': '*',
        });
        res.end(JSON.stringify({ ok: false, error: String(err?.message || err) }));
      });
    return;
  }

  // Proxy API requests
  if (url.pathname.startsWith('/api/')) return proxy(req, res);

  // Serve static: dist first, then public
  const clean = decodeURIComponent(url.pathname);
  let fp = path.join(distDir, clean);
  if (clean === '/' || (!path.extname(clean) && !existsSync(fp))) {
    fp = path.join(distDir, 'index.html');
  }
  if (tryServe(res, fp)) return;

  fp = path.join(publicDir, clean);
  if (tryServe(res, fp)) return;

  res.writeHead(404);
  res.end('Not found');
});

// Proxy WebSocket upgrades
server.on('upgrade', (req, socket, head) => {
  const p = httpRequest({
    hostname: '127.0.0.1', port: apiPort, path: req.url,
    method: req.method, headers: { ...req.headers, host: `127.0.0.1:${apiPort}` },
  });
  p.on('upgrade', (pRes, pSocket) => {
    socket.write(
      `HTTP/1.1 101 Switching Protocols\r\n` +
      Object.entries(pRes.headers).map(([k, v]) => `${k}: ${v}`).join('\r\n') +
      '\r\n\r\n'
    );
    pSocket.pipe(socket);
    socket.pipe(pSocket);
  });
  p.on('error', () => socket.destroy());
  p.end();
});

server.listen(port, () => {
  console.log(`[miniverse-public] http://localhost:${port}`);
});

process.on('SIGINT', () => process.exit(0));
process.on('SIGTERM', () => process.exit(0));
