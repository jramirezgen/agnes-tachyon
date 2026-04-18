import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

const SERVER = process.env.MINIVERSE_SERVER_URL || 'http://localhost:4321';
const HEARTBEAT_MS = Number(process.env.MINIVERSE_HEARTBEAT_MS || 20000);
const POLL_MS = Number(process.env.MINIVERSE_POLL_MS || 3000);
const BOOTSTRAP_DEMO = (process.env.MINIVERSE_BOOTSTRAP_DEMO || '1') === '1';

const __filename = fileURLToPath(import.meta.url);
const __dirname = resolve(__filename, '..');
const PROJECT_ROOT = resolve(__dirname, '..');
const OUTPUT_DIR = resolve(PROJECT_ROOT, 'generated');

const TOOL_QWEN = '/home/kaitokid/.local/bin/oc_ollama_qwen.sh';
const TOOL_QWEN_WINDOWS = '/home/kaitokid/.local/bin/oc_ollama_qwen_windows.sh';

const AGENTS = {
  boss: {
    id: 'boss-agent',
    name: 'Jefe Orquestador',
    channels: ['management'],
    state: 'idle',
    task: 'Coordinando equipo',
  },
  accountant: {
    id: 'accountant-agent',
    name: 'Contador',
    channels: ['management', 'finance'],
    state: 'idle',
    task: 'Esperando tareas de finanzas',
  },
  librarian: {
    id: 'librarian-agent',
    name: 'Bibliotecaria',
    channels: ['management', 'knowledge'],
    state: 'idle',
    task: 'Curando conocimiento',
  },
  auditor: {
    id: 'auditor-agent',
    name: 'Auditor',
    channels: ['management', 'audit'],
    state: 'idle',
    task: 'Verificando calidad',
  },
};

const tasks = new Map();

function nowIso() {
  return new Date().toISOString();
}

function short(text, max = 140) {
  if (!text) return '';
  return text.length <= max ? text : `${text.slice(0, max - 3)}...`;
}

async function waitForServer(maxAttempts = 60) {
  for (let i = 1; i <= maxAttempts; i += 1) {
    try {
      const res = await fetch(`${SERVER}/api/agents`);
      if (res.ok) return;
    } catch {
      // no-op, retry
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error(`No pude conectar con Miniverse en ${SERVER}`);
}

async function heartbeat(agent, patch = {}) {
  AGENTS[agent].state = patch.state || AGENTS[agent].state;
  AGENTS[agent].task = patch.task || AGENTS[agent].task;

  await fetch(`${SERVER}/api/heartbeat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      agent: AGENTS[agent].id,
      name: AGENTS[agent].name,
      state: AGENTS[agent].state,
      task: AGENTS[agent].task,
      energy: patch.energy ?? 0.8,
      metadata: patch.metadata || {},
    }),
  });
}

async function act(agent, action) {
  await fetch(`${SERVER}/api/act`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent: AGENTS[agent].id, action }),
  });
}

async function joinChannels(agent) {
  const { channels } = AGENTS[agent];
  for (const channel of channels) {
    await act(agent, { type: 'join_channel', channel });
  }
}

async function readInbox(agent) {
  const response = await fetch(`${SERVER}/api/inbox?agent=${encodeURIComponent(AGENTS[agent].id)}`);
  if (!response.ok) return [];
  const data = await response.json();
  return data.messages || [];
}

async function saveArtifact(agent, taskId, kind, content) {
  const dir = resolve(OUTPUT_DIR, AGENTS[agent].id);
  await mkdir(dir, { recursive: true });
  const path = resolve(dir, `${taskId}_${kind}.md`);
  await writeFile(path, content, 'utf8');
  return path;
}

function inferTaskType(text = '') {
  const lower = text.toLowerCase();
  if (lower.includes('finanza') || lower.includes('presupuesto') || lower.includes('gasto') || lower.includes('ingreso')) {
    return 'finance';
  }
  if (lower.includes('abrir') || lower.includes('word') || lower.includes('excel') || lower.includes('brave') || lower.includes('carpeta')) {
    return 'windows_action';
  }
  return 'knowledge';
}

function buildTask(request, from = 'external') {
  const id = `task_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
  return {
    id,
    from,
    title: short(request, 80),
    request,
    type: inferTaskType(request),
    status: 'queued',
    createdAt: nowIso(),
    updatedAt: nowIso(),
  };
}

async function callTool(tool, input, timeoutMs = 120000) {
  const { stdout, stderr } = await execFileAsync(tool, [input], {
    timeout: timeoutMs,
    maxBuffer: 1024 * 1024 * 8,
  });
  return short(`${stdout || ''}${stderr ? `\n${stderr}` : ''}`.trim(), 5000);
}

async function handleBossMessage(msg) {
  const text = String(msg.message || '').trim();

  if (text.startsWith('RESULT|') || text.startsWith('AUDIT|')) {
    const [, rawPayload] = text.split('|', 2);
    let payload;
    try {
      payload = JSON.parse(rawPayload);
    } catch {
      return;
    }
    const task = tasks.get(payload.taskId);
    if (!task) return;

    if (text.startsWith('RESULT|')) {
      task.result = payload;
      task.status = 'waiting_audit';
      task.updatedAt = nowIso();
      tasks.set(task.id, task);

      await act('boss', {
        type: 'message',
        to: AGENTS.auditor.id,
        message: `AUDIT_REQUEST|${JSON.stringify({ taskId: task.id, owner: payload.owner, summary: payload.summary, artifact: payload.artifact })}`,
      });
      await act('boss', { type: 'speak', message: `Recibido resultado de ${payload.owner}. Enviando a auditoria.` });
      return;
    }

    if (text.startsWith('AUDIT|')) {
      task.audit = payload;
      task.status = payload.ok ? 'completed' : 'needs_revision';
      task.updatedAt = nowIso();
      tasks.set(task.id, task);

      const completion = [
        `# Cierre de tarea ${task.id}`,
        '',
        `- Solicitud: ${task.request}`,
        `- Estado: ${task.status}`,
        `- Resultado: ${task.result?.summary || 'N/A'}`,
        `- Auditoria: ${payload.summary}`,
        `- Artefacto resultado: ${task.result?.artifact || 'N/A'}`,
        `- Artefacto auditoria: ${payload.artifact || 'N/A'}`,
      ].join('\n');
      const closePath = await saveArtifact('boss', task.id, 'closure', completion);

      await act('boss', {
        type: 'speak',
        message: payload.ok
          ? `Tarea ${task.id} completada y validada.`
          : `Tarea ${task.id} requiere revision.`,
      });
      await heartbeat('boss', { state: 'idle', task: `Cierre listo: ${task.id}` });

      await act('boss', {
        type: 'message',
        to: task.assigneeId,
        message: `TASK_STATUS|${JSON.stringify({ taskId: task.id, status: task.status, closeArtifact: closePath })}`,
      });
      return;
    }
  }

  const task = buildTask(text, msg.from || 'external');
  const assignee = task.type === 'finance' ? 'accountant' : task.type === 'knowledge' ? 'librarian' : 'accountant';

  task.assignee = assignee;
  task.assigneeId = AGENTS[assignee].id;
  task.status = 'assigned';
  tasks.set(task.id, task);

  await heartbeat('boss', { state: 'working', task: `Asignando ${task.type}: ${short(task.request, 40)}` });
  await act('boss', { type: 'speak', message: `Asignando ${task.type} a ${AGENTS[assignee].name}` });

  await act('boss', {
    type: 'message',
    to: AGENTS[assignee].id,
    message: `TASK|${JSON.stringify(task)}`,
  });
}

async function handleWorkerMessage(worker, msg) {
  const text = String(msg.message || '').trim();
  if (!text.startsWith('TASK|')) return;

  const [, rawPayload] = text.split('|', 2);
  let task;
  try {
    task = JSON.parse(rawPayload);
  } catch {
    return;
  }

  await heartbeat(worker, { state: 'working', task: `${task.type}: ${short(task.request, 40)}` });
  await act(worker, { type: 'status', state: 'working', task: short(task.request, 50) });

  try {
    const rolePrompt = worker === 'accountant'
      ? `Actua como contador senior. Analiza esta solicitud financiera y responde con: resumen ejecutivo, riesgos, recomendaciones accionables y checklist final. Solicitud: ${task.request}`
      : `Actua como bibliotecaria investigadora. Aprende y sintetiza esta solicitud con: conceptos clave, fuentes sugeridas, plan de aprendizaje y resumen aplicable. Solicitud: ${task.request}`;

    let output;
    if (task.type === 'windows_action') {
      output = await callTool(TOOL_QWEN_WINDOWS, task.request, 90000);
    } else {
      output = await callTool(TOOL_QWEN, rolePrompt, 120000);
    }

    const artifact = await saveArtifact(
      worker,
      task.id,
      'result',
      `# Resultado ${AGENTS[worker].name}\n\n## Solicitud\n${task.request}\n\n## Salida\n${output}\n`,
    );

    await act(worker, {
      type: 'message',
      to: AGENTS.boss.id,
      message: `RESULT|${JSON.stringify({
        taskId: task.id,
        owner: AGENTS[worker].id,
        summary: short(output, 220),
        artifact,
      })}`,
    });

    await act(worker, { type: 'speak', message: `Termine ${task.id}` });
    await heartbeat(worker, { state: 'idle', task: `Esperando nueva tarea (${task.id})` });
  } catch (error) {
    const err = error instanceof Error ? error.message : String(error);
    await act(worker, { type: 'speak', message: `Error en ${task.id}` });
    await heartbeat(worker, { state: 'error', task: short(err, 60) });

    await act(worker, {
      type: 'message',
      to: AGENTS.boss.id,
      message: `RESULT|${JSON.stringify({ taskId: task.id, owner: AGENTS[worker].id, summary: `ERROR: ${err}`, artifact: null })}`,
    });
  }
}

async function handleAuditorMessage(msg) {
  const text = String(msg.message || '').trim();
  if (!text.startsWith('AUDIT_REQUEST|')) return;

  const [, rawPayload] = text.split('|', 2);
  let payload;
  try {
    payload = JSON.parse(rawPayload);
  } catch {
    return;
  }

  await heartbeat('auditor', { state: 'working', task: `Auditando ${payload.taskId}` });

  const prompt = `Actua como auditor de calidad. Evalua esta salida de agente y responde en formato breve con: estado (OK/REVISION), observaciones y acciones correctivas. Resumen a auditar: ${payload.summary}`;
  let auditOutput = '';
  let ok = true;

  try {
    auditOutput = await callTool(TOOL_QWEN, prompt, 90000);
    ok = !/revision|error|inconsisten|riesgo alto/i.test(auditOutput);
  } catch (error) {
    const err = error instanceof Error ? error.message : String(error);
    auditOutput = `Fallo auditoria automatica: ${err}`;
    ok = false;
  }

  const artifact = await saveArtifact(
    'auditor',
    payload.taskId,
    'audit',
    `# Auditoria ${payload.taskId}\n\n## Entrada\n${payload.summary}\n\n## Evaluacion\n${auditOutput}\n\n## Estado\n${ok ? 'OK' : 'REVISION'}\n`,
  );

  await act('auditor', {
    type: 'message',
    to: AGENTS.boss.id,
    message: `AUDIT|${JSON.stringify({ taskId: payload.taskId, ok, summary: short(auditOutput, 220), artifact })}`,
  });
  await act('auditor', { type: 'speak', message: ok ? `Auditoria OK ${payload.taskId}` : `Revision requerida ${payload.taskId}` });
  await heartbeat('auditor', { state: 'idle', task: `Auditado ${payload.taskId}` });
}

async function processInbox(agentKey) {
  const messages = await readInbox(agentKey);
  for (const msg of messages) {
    if (agentKey === 'boss') {
      await handleBossMessage(msg);
      continue;
    }
    if (agentKey === 'auditor') {
      await handleAuditorMessage(msg);
      continue;
    }
    await handleWorkerMessage(agentKey, msg);
  }
}

async function bootstrapDemoTasks() {
  const demoTasks = [
    'Revisa el presupuesto mensual: ingresos 5000, gastos 4200, sugiere acciones para mejorar margen.',
    'Aprende sobre indicadores financieros clave para pymes y entrega una guia breve aplicable.',
  ];

  for (const text of demoTasks) {
    await act('boss', {
      type: 'message',
      to: AGENTS.boss.id,
      message: text,
    });
  }
}

async function start() {
  await mkdir(OUTPUT_DIR, { recursive: true });
  await waitForServer();

  for (const key of Object.keys(AGENTS)) {
    await heartbeat(key, { state: 'idle' });
    await joinChannels(key);
    await act(key, { type: 'speak', message: `${AGENTS[key].name} en linea` });
  }

  if (BOOTSTRAP_DEMO) {
    await bootstrapDemoTasks();
  }

  setInterval(async () => {
    for (const key of Object.keys(AGENTS)) {
      try {
        await heartbeat(key);
      } catch {
        // retried on next interval
      }
    }
  }, HEARTBEAT_MS);

  setInterval(async () => {
    for (const key of Object.keys(AGENTS)) {
      try {
        await processInbox(key);
      } catch {
        // continue processing other agents
      }
    }
  }, POLL_MS);

  console.log('[agents] runtime iniciado: boss/accountant/librarian/auditor');
}

start().catch((error) => {
  console.error('[agents] fallo de inicio:', error);
  process.exitCode = 1;
});
