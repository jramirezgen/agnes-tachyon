import { Miniverse, PropSystem } from '@miniverse/core';

const WORLD_ID = 'cozy-startup';
const basePath = `/worlds/${WORLD_ID}`;

function buildSceneConfig(cols, rows, floor, tiles) {
  const safeFloor = floor ?? Array.from({ length: rows }, () => Array(cols).fill(''));
  const walkable = [];
  for (let r = 0; r < rows; r++) {
    walkable[r] = [];
    for (let c = 0; c < cols; c++) walkable[r][c] = (safeFloor[r]?.[c] ?? '') !== '';
  }

  const resolvedTiles = { ...(tiles ?? {}) };
  for (const [key, src] of Object.entries(resolvedTiles)) {
    if (/^(blob:|data:|https?:\/\/)/.test(src)) continue;
    const clean = src.startsWith('/') ? src.slice(1) : src;
    resolvedTiles[key] = `${basePath}/${clean}`;
  }

  return {
    name: 'main',
    tileWidth: 32,
    tileHeight: 32,
    layers: [safeFloor],
    walkable,
    locations: {},
    tiles: resolvedTiles,
  };
}

const SPRITES = ['morty', 'dexter', 'nova', 'rio'];

function ensureCommandCenterStyles() {
  if (document.getElementById('cc-styles')) return;
  const style = document.createElement('style');
  style.id = 'cc-styles';
  style.textContent = `
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

.cc-fab {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 60;
  border: 0;
  border-radius: 999px;
  padding: 10px 16px;
  background: linear-gradient(135deg, #0f766e 0%, #f59e0b 100%);
  color: #111827;
  font: 700 13px/1 'Space Grotesk', sans-serif;
  letter-spacing: 0.04em;
  cursor: pointer;
  box-shadow: 0 10px 30px rgba(15, 118, 110, 0.35);
}

.cc-shell {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: none;
  background:
    radial-gradient(1200px 500px at 100% 0%, rgba(245, 158, 11, 0.16), transparent 60%),
    radial-gradient(900px 500px at 0% 100%, rgba(20, 184, 166, 0.18), transparent 55%),
    rgba(3, 7, 18, 0.78);
  backdrop-filter: blur(6px);
}

.cc-shell.open {
  display: block;
}

.cc-panel {
  position: absolute;
  inset: 40px;
  border-radius: 24px;
  border: 1px solid rgba(245, 158, 11, 0.32);
  background: linear-gradient(180deg, rgba(10, 14, 24, 0.94), rgba(8, 12, 20, 0.96));
  color: #f3f4f6;
  overflow: hidden;
  font-family: 'Space Grotesk', sans-serif;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
  animation: cc-fade-in .28s ease;
}

@keyframes cc-fade-in {
  from { transform: translateY(8px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.cc-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 14px;
  height: calc(100% - 86px);
  padding: 14px;
}

.cc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(90deg, rgba(245, 158, 11, 0.14), rgba(13, 148, 136, 0.14));
}

.cc-title {
  margin: 0;
  font-size: 22px;
  letter-spacing: 0.02em;
}

.cc-subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  opacity: 0.85;
}

.cc-close {
  border: 0;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.12);
  color: #f3f4f6;
  font: 600 12px/1 'IBM Plex Mono', monospace;
  padding: 10px 12px;
  cursor: pointer;
}

.cc-card {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.03);
  padding: 14px;
}

.cc-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.cc-btn {
  border: 0;
  border-radius: 10px;
  padding: 10px 12px;
  color: #111827;
  font: 700 12px/1 'Space Grotesk', sans-serif;
  cursor: pointer;
}

.cc-btn.pause {
  background: #f59e0b;
}

.cc-btn.resume {
  background: #14b8a6;
}

.cc-btn.save {
  background: #93c5fd;
}

.cc-btn.secondary {
  background: rgba(255, 255, 255, 0.16);
  color: #f3f4f6;
}

.cc-agent-list {
  margin-top: 10px;
  display: grid;
  gap: 8px;
}

.cc-agent {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.02);
}

.cc-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border-radius: 999px;
  font: 600 11px/1 'IBM Plex Mono', monospace;
  padding: 6px 8px;
  background: rgba(20, 184, 166, 0.2);
}

.cc-badge.paused {
  background: rgba(245, 158, 11, 0.25);
}

.cc-input,
.cc-select,
.cc-textarea {
  width: 100%;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(0, 0, 0, 0.35);
  color: #f3f4f6;
  font: 500 13px/1.4 'IBM Plex Mono', monospace;
  padding: 10px;
  box-sizing: border-box;
}

.cc-textarea {
  min-height: 94px;
  resize: vertical;
}

.cc-log {
  margin-top: 10px;
  max-height: 230px;
  overflow: auto;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(2, 6, 23, 0.6);
  padding: 8px;
  font: 500 12px/1.4 'IBM Plex Mono', monospace;
}

.cc-log-item {
  border-bottom: 1px dashed rgba(255, 255, 255, 0.12);
  padding: 8px 6px;
}

.cc-log-item:last-child {
  border-bottom: 0;
}

.cc-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 8px;
}

.cc-kpis {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.cc-kpi {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  padding: 8px;
}

.cc-kpi-label {
  font: 500 11px/1 'IBM Plex Mono', monospace;
  opacity: 0.8;
}

.cc-kpi-value {
  margin-top: 4px;
  font: 700 20px/1 'Space Grotesk', sans-serif;
}

.cc-chip-row {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.cc-chip {
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 999px;
  padding: 6px 10px;
  font: 600 11px/1 'IBM Plex Mono', monospace;
  background: rgba(255, 255, 255, 0.06);
}

.cc-chip.ok {
  border-color: rgba(20, 184, 166, 0.5);
  background: rgba(20, 184, 166, 0.2);
}

.cc-chip.warn {
  border-color: rgba(245, 158, 11, 0.5);
  background: rgba(245, 158, 11, 0.22);
}

@media (max-width: 1040px) {
  .cc-panel {
    inset: 10px;
  }

  .cc-grid {
    grid-template-columns: 1fr;
    height: calc(100% - 80px);
    overflow: auto;
  }

  .cc-actions {
    grid-template-columns: 1fr;
  }

  .cc-kpis {
    grid-template-columns: 1fr;
  }
}
`;
  document.head.appendChild(style);
}

function mountCommandCenter() {
  ensureCommandCenterStyles();

  const fab = document.createElement('button');
  fab.className = 'cc-fab';
  fab.type = 'button';
  fab.textContent = 'Centro de Comando';

  const shell = document.createElement('div');
  shell.className = 'cc-shell';
  shell.innerHTML = `
    <section class="cc-panel" aria-label="Centro de Comando">
      <header class="cc-header">
        <div>
          <h2 class="cc-title">Centro de Comando de Agentes</h2>
          <p class="cc-subtitle">Control táctico, conversaciones multiagente y snapshots en tiempo real</p>
        </div>
        <button type="button" class="cc-close">ESC / Cerrar</button>
      </header>
      <div class="cc-grid">
        <div class="cc-card">
          <div id="cc-status-badge" class="cc-badge">Estado: cargando</div>
          <div class="cc-kpis">
            <div class="cc-kpi"><div class="cc-kpi-label">Tareas totales</div><div id="cc-kpi-total" class="cc-kpi-value">0</div></div>
            <div class="cc-kpi"><div class="cc-kpi-label">Completadas</div><div id="cc-kpi-completed" class="cc-kpi-value">0</div></div>
            <div class="cc-kpi"><div class="cc-kpi-label">En revisión</div><div id="cc-kpi-review" class="cc-kpi-value">0</div></div>
            <div class="cc-kpi"><div class="cc-kpi-label">Agentes activos</div><div id="cc-kpi-active" class="cc-kpi-value">0</div></div>
            <div class="cc-kpi"><div class="cc-kpi-label">Durmiendo</div><div id="cc-kpi-sleep" class="cc-kpi-value">0</div></div>
          </div>
          <div class="cc-chip-row">
            <span id="cc-chip-learner" class="cc-chip">Learner: --</span>
            <span id="cc-chip-autochat" class="cc-chip">Auto chat: --</span>
            <span id="cc-chip-updated" class="cc-chip">Sync: --</span>
          </div>
          <div class="cc-actions">
            <button type="button" class="cc-btn pause" data-action="pause_all">Pausar Todo + Guardar</button>
            <button type="button" class="cc-btn resume" data-action="resume_all">Reanudar Todo</button>
            <button type="button" class="cc-btn save" data-action="save_snapshot">Guardar Snapshot</button>
          </div>
          <div id="cc-agent-list" class="cc-agent-list"></div>
        </div>
        <div class="cc-card">
          <label for="cc-target">Objetivo</label>
          <select id="cc-target" class="cc-select">
            <option value="boss">Boss (orquestación)</option>
            <option value="accountant">Contador</option>
            <option value="librarian">Bibliotecaria</option>
            <option value="auditor">Auditor</option>
          </select>
          <div class="cc-row">
            <div>
              <label for="cc-poll">pollSec</label>
              <input id="cc-poll" class="cc-input" type="number" min="0.5" step="0.5" placeholder="3" />
            </div>
            <div>
              <label for="cc-heartbeat">heartbeatSec</label>
              <input id="cc-heartbeat" class="cc-input" type="number" min="3" step="1" placeholder="20" />
            </div>
          </div>
          <div class="cc-row">
            <div>
              <label for="cc-visual">visualInterval</label>
              <input id="cc-visual" class="cc-input" type="number" min="1" step="1" placeholder="15" />
            </div>
            <div>
              <label for="cc-conv-interval">conversationSec</label>
              <input id="cc-conv-interval" class="cc-input" type="number" min="10" step="5" placeholder="90" />
            </div>
          </div>
          <div class="cc-row">
            <div>
              <label for="cc-auto-conv">Auto conversación</label>
              <select id="cc-auto-conv" class="cc-select">
                <option value="0">Desactivada</option>
                <option value="1">Activada</option>
              </select>
            </div>
            <div>
              <label>&nbsp;</label>
              <button id="cc-apply-params" type="button" class="cc-btn secondary" style="width:100%">Aplicar Parámetros</button>
            </div>
          </div>
          <label for="cc-message" style="display:block;margin-top:10px">Instrucción</label>
          <textarea id="cc-message" class="cc-textarea" placeholder="Escribe una orden o tarea..."></textarea>
          <div class="cc-actions" style="margin-top:8px">
            <button id="cc-send" type="button" class="cc-btn resume">Enviar Instrucción</button>
            <button id="cc-pause-agent" type="button" class="cc-btn pause">Pausar Objetivo</button>
            <button id="cc-resume-agent" type="button" class="cc-btn secondary">Reanudar Objetivo</button>
          </div>
          <label for="cc-conv-topic" style="display:block;margin-top:10px">Tema conversación</label>
          <input id="cc-conv-topic" class="cc-input" type="text" placeholder="coordinación operativa, revisión financiera, etc." />
          <div class="cc-actions" style="margin-top:8px">
            <button id="cc-spark-conv" type="button" class="cc-btn save">Iniciar Conversación</button>
          </div>
          <div id="cc-log" class="cc-log"></div>
        </div>
      </div>
    </section>
  `;

  document.body.appendChild(fab);
  document.body.appendChild(shell);

  const closeBtn = shell.querySelector('.cc-close');
  const statusBadge = shell.querySelector('#cc-status-badge');
  const agentList = shell.querySelector('#cc-agent-list');
  const log = shell.querySelector('#cc-log');
  const kpiTotal = shell.querySelector('#cc-kpi-total');
  const kpiCompleted = shell.querySelector('#cc-kpi-completed');
  const kpiReview = shell.querySelector('#cc-kpi-review');
  const kpiActive = shell.querySelector('#cc-kpi-active');
  const kpiSleep = shell.querySelector('#cc-kpi-sleep');
  const chipLearner = shell.querySelector('#cc-chip-learner');
  const chipAutoChat = shell.querySelector('#cc-chip-autochat');
  const chipUpdated = shell.querySelector('#cc-chip-updated');

  const targetSelect = shell.querySelector('#cc-target');
  const messageInput = shell.querySelector('#cc-message');
  const pollInput = shell.querySelector('#cc-poll');
  const heartbeatInput = shell.querySelector('#cc-heartbeat');
  const visualInput = shell.querySelector('#cc-visual');
  const convIntervalInput = shell.querySelector('#cc-conv-interval');
  const autoConvInput = shell.querySelector('#cc-auto-conv');
  const convTopicInput = shell.querySelector('#cc-conv-topic');

  const toggle = (open) => {
    shell.classList.toggle('open', open);
  };

  const openFromQuery = new URLSearchParams(location.search).has('cc');
  toggle(openFromQuery);

  fab.addEventListener('click', () => {
    toggle(!shell.classList.contains('open'));
  });
  closeBtn.addEventListener('click', () => toggle(false));

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') toggle(false);
    if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      toggle(!shell.classList.contains('open'));
    }
  });

  const postCommand = async (action, extra = {}) => {
    const payload = { action, source: 'command-center-ui', ...extra };
    const response = await fetch('/api/command-center/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const raw = await response.text();
      throw new Error(raw || `HTTP ${response.status}`);
    }
    return response.json();
  };

  const renderLog = (responses = []) => {
    if (!responses.length) {
      log.innerHTML = '<div class="cc-log-item">Sin respuestas todavía.</div>';
      return;
    }
    log.innerHTML = responses
      .slice()
      .reverse()
      .map((entry) => {
        const state = entry.ok === false ? 'ERROR' : 'OK';
        return `<div class="cc-log-item"><strong>${state}</strong> ${entry.kind || 'runtime'}<br/>${entry.message || ''}<br/><small>${entry.at || ''}</small></div>`;
      })
      .join('');
  };

  const renderAgents = (agents = []) => {
    agentList.innerHTML = agents
      .map((agent) => {
        const paused = !!agent.paused;
        const badge = paused ? 'cc-badge paused' : 'cc-badge';
        const stateLabel = paused ? 'sleeping' : (agent.state || 'idle');
        return `
          <div class="cc-agent">
            <div>
              <div style="font-weight:700">${agent.name}</div>
              <div style="font-size:12px;opacity:.85">${agent.task || 'Sin tarea'}</div>
            </div>
            <div style="display:flex;gap:8px;align-items:center">
              <span class="${badge}">${stateLabel}</span>
              <button type="button" class="cc-btn secondary" data-agent-toggle="${agent.key}|${paused ? 'resume_agent' : 'pause_agent'}">${paused ? 'Reanudar' : 'Pausar'}</button>
            </div>
          </div>
        `;
      })
      .join('');

    agentList.querySelectorAll('[data-agent-toggle]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const [target, action] = btn.getAttribute('data-agent-toggle').split('|');
        try {
          await postCommand(action, { target });
        } catch (error) {
          console.error(error);
        }
      });
    });
  };

  const syncStatus = async () => {
    try {
      const state = await fetch('/api/command-center/status').then((r) => r.json());
      const runtime = state.runtime || {};
      const pausedAll = !!runtime.pausedAll;
      statusBadge.className = pausedAll ? 'cc-badge paused' : 'cc-badge';
      statusBadge.textContent = pausedAll ? 'Estado: PAUSA GLOBAL' : 'Estado: OPERATIVO';

      const byStatus = state.tasks?.byStatus || {};
      kpiTotal.textContent = String(state.tasks?.total || 0);
      kpiCompleted.textContent = String(byStatus.completed || 0);
      kpiReview.textContent = String(byStatus.needs_revision || 0);
      const agents = state.agents || [];
      const activeAgents = agents.filter((agent) => !agent.paused).length;
      const sleepAgents = agents.filter((agent) => agent.paused || agent.state === 'sleeping').length;
      kpiActive.textContent = String(activeAgents);
      kpiSleep.textContent = String(sleepAgents);

      const parameters = runtime.parameters || {};
      pollInput.value = parameters.pollSec || pollInput.value || '';
      heartbeatInput.value = parameters.heartbeatSec || heartbeatInput.value || '';
      visualInput.value = parameters.visualInterval || visualInput.value || '';
      convIntervalInput.value = parameters.conversationIntervalSec || convIntervalInput.value || '';
      autoConvInput.value = parameters.autoConversation ? '1' : '0';

      chipLearner.className = `cc-chip ${runtime.librarianLearnerActive ? 'ok' : 'warn'}`;
      chipLearner.textContent = `Learner: ${runtime.librarianLearnerActive ? 'activo' : 'apagado'}`;
      chipAutoChat.className = `cc-chip ${parameters.autoConversation ? 'ok' : 'warn'}`;
      chipAutoChat.textContent = `Auto chat: ${parameters.autoConversation ? 'encendido' : 'apagado'}`;
      chipUpdated.className = 'cc-chip';
      chipUpdated.textContent = `Sync: ${String(state.updatedAt || '--').replace('T', ' ').slice(0, 19)}Z`;

      renderAgents(agents);
      renderLog(state.responses || []);
    } catch (error) {
      statusBadge.className = 'cc-badge paused';
      statusBadge.textContent = 'Estado: sin conexión';
    }
  };

  shell.querySelectorAll('[data-action]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const action = btn.getAttribute('data-action');
      try {
        const params = action === 'pause_all' ? { params: { saveSnapshot: true } } : {};
        await postCommand(action, params);
        await syncStatus();
      } catch (error) {
        console.error(error);
      }
    });
  });

  shell.querySelector('#cc-send').addEventListener('click', async () => {
    const message = messageInput.value.trim();
    if (!message) return;
    try {
      await postCommand('dispatch', { target: targetSelect.value, message });
      messageInput.value = '';
      await syncStatus();
    } catch (error) {
      console.error(error);
    }
  });

  shell.querySelector('#cc-pause-agent').addEventListener('click', async () => {
    try {
      await postCommand('pause_agent', { target: targetSelect.value });
      await syncStatus();
    } catch (error) {
      console.error(error);
    }
  });

  shell.querySelector('#cc-resume-agent').addEventListener('click', async () => {
    try {
      await postCommand('resume_agent', { target: targetSelect.value });
      await syncStatus();
    } catch (error) {
      console.error(error);
    }
  });

  shell.querySelector('#cc-apply-params').addEventListener('click', async () => {
    const params = {};
    if (pollInput.value) params.pollSec = Number(pollInput.value);
    if (heartbeatInput.value) params.heartbeatSec = Number(heartbeatInput.value);
    if (visualInput.value) params.visualInterval = Number(visualInput.value);
    if (convIntervalInput.value) params.conversationIntervalSec = Number(convIntervalInput.value);
    params.autoConversation = autoConvInput.value === '1';
    if (!Object.keys(params).length) return;
    try {
      await postCommand('set_params', { params });
      await syncStatus();
    } catch (error) {
      console.error(error);
    }
  });

  shell.querySelector('#cc-spark-conv').addEventListener('click', async () => {
    const topic = convTopicInput.value.trim() || 'coordinación operativa';
    try {
      await postCommand('spark_conversation', {
        message: topic,
      });
      await syncStatus();
    } catch (error) {
      console.error(error);
    }
  });

  syncStatus();
  setInterval(syncStatus, 2000);
}

async function main() {
  const container = document.getElementById('world');
  const sceneData = await fetch(`${basePath}/world.json`).then(r => r.json()).catch(() => null);

  const gridCols = sceneData?.gridCols ?? 16;
  const gridRows = sceneData?.gridRows ?? 12;
  const sceneConfig = buildSceneConfig(gridCols, gridRows, sceneData?.floor, sceneData?.tiles);
  const tileSize = 32;

  // WebSocket signal — use current host
  const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${location.host}/ws`;

  const mv = new Miniverse({
    container,
    world: WORLD_ID,
    scene: 'main',
    signal: {
      type: 'websocket',
      url: wsUrl,
    },
    citizens: [],
    defaultSprites: SPRITES,
    scale: 2,
    width: gridCols * tileSize,
    height: gridRows * tileSize,
    sceneConfig,
    objects: [],
  });

  // Props system
  const props = new PropSystem(tileSize, 2);

  const rawSpriteMap = sceneData?.propImages ?? {};
  await Promise.all(
    Object.entries(rawSpriteMap).map(([id, src]) => {
      const clean = src.startsWith('/') ? src : '/' + src;
      return props.loadSprite(id, `${basePath}${clean}`);
    }),
  );

  props.setLayout(sceneData?.props ?? []);
  if (sceneData?.wanderPoints) {
    props.setWanderPoints(sceneData.wanderPoints);
  }

  props.setDeadspaceCheck((col, row) => {
    const floor = mv.getFloorLayer();
    return floor?.[row]?.[col] === '';
  });

  const syncProps = () => {
    mv.setTypedLocations(props.getLocations());
    mv.updateWalkability(props.getBlockedTiles());
  };
  syncProps();
  props.onSave(syncProps);

  await mv.start();

  mv.addLayer({ order: 5, render: (ctx) => props.renderBelow(ctx) });
  mv.addLayer({ order: 15, render: (ctx) => props.renderAbove(ctx) });

  mountCommandCenter();
}

main().catch(console.error);
