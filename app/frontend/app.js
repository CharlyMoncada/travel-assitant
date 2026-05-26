const resultOutput = document.getElementById('resultOutput');
const messageInput = document.getElementById('messageInput');


// Get or create a session_id in localStorage to maintain session state
let sessionId = localStorage.getItem('travel_assistant_session_id');
if (!sessionId) {
  sessionId = 'session_' + Math.random().toString(36).substring(2, 11);
  localStorage.setItem('travel_assistant_session_id', sessionId);
}

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
    setResult({ error: 'Write a message before sending.' });
    return;
  }
  await requestJson('/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, thread_id: sessionId }),
  });
});
