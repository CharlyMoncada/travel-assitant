const resultOutput = document.getElementById('resultOutput');
const messageInput = document.getElementById('messageInput');
const executeInput = document.getElementById('executeInput');

const setResult = (data) => {
  resultOutput.textContent = JSON.stringify(data, null, 2);
};

const requestJson = async (url, options = {}) => {
  const response = await fetch(url, options);
  const data = await response.json();
  setResult(data);
  return data;
};

document.getElementById('statusButton').addEventListener('click', () => {
  requestJson('/status');
});

document.getElementById('expensesButton').addEventListener('click', () => {
  requestJson('/expenses');
});

document.getElementById('remindersButton').addEventListener('click', () => {
  requestJson('/reminders');
});

document.getElementById('toolsButton').addEventListener('click', () => {
  requestJson('/mcp/tools');
});

document.getElementById('sendMessageButton').addEventListener('click', async () => {
  const text = messageInput.value.trim();
  if (!text) {
    setResult({ error: 'Escribe un mensaje antes de enviar.' });
    return;
  }
  await requestJson('/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
});

document.getElementById('executeButton').addEventListener('click', async () => {
  const text = executeInput.value.trim();
  if (!text) {
    setResult({ error: 'Escribe una entrada para MCP antes de ejecutar.' });
    return;
  }
  await requestJson('/mcp/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
});

document.getElementById('llmButton').addEventListener('click', async () => {
  const text = document.getElementById('llmInput').value.trim();
  if (!text) {
    setResult({ error: 'Escribe un mensaje para probar el LLM.' });
    return;
  }
  await requestJson('/llm/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
});
