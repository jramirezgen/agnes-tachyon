const { spawn } = await import('node:child_process');

const tasks = [
  'Analiza flujo de caja trimestral con ingresos 15000 y gastos 12800, con plan de mejora.',
  'Aprende sobre metodo 50/30/20 y crea una guia practica para aplicarla en negocio pequeno.',
];

function runTask(task) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ['agents/submit-task.mjs', task], {
      stdio: 'inherit',
    });
    child.on('exit', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`submit-task fallo con codigo ${code}`));
    });
  });
}

for (const task of tasks) {
  // Envia en paralelo para demostrar concurrencia
  runTask(task).catch((err) => console.error(err.message));
}
