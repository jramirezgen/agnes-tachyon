const SERVER = process.env.MINIVERSE_SERVER_URL || 'http://localhost:4321';
const BOSS_ID = 'boss-agent';
const EXTERNAL_ID = 'external-user';

const text = process.argv.slice(2).join(' ').trim();
if (!text) {
  console.error('Uso: node agents/submit-task.mjs "tu tarea"');
  process.exit(1);
}

async function request(path, body) {
  const res = await fetch(`${SERVER}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} en ${path}`);
  }
}

async function main() {
  await request('/api/heartbeat', {
    agent: EXTERNAL_ID,
    name: 'Usuario Externo',
    state: 'speaking',
    task: 'Enviando tarea al jefe',
  });

  await request('/api/act', {
    agent: EXTERNAL_ID,
    action: {
      type: 'message',
      to: BOSS_ID,
      message: text,
    },
  });

  await request('/api/act', {
    agent: EXTERNAL_ID,
    action: {
      type: 'speak',
      message: 'Tarea enviada al jefe',
    },
  });

  console.log(`Tarea enviada a ${BOSS_ID}: ${text}`);
}

main().catch((err) => {
  console.error('No se pudo enviar la tarea:', err.message);
  process.exit(1);
});
