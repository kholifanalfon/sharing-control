document.addEventListener('DOMContentLoaded', () => {
  const statusBadge = document.getElementById('statusBadge');
  const statusText = document.getElementById('statusText');
  const btnToggle = document.getElementById('btnToggleService');
  const radioServer = document.getElementById('radioServer');
  const radioClient = document.getElementById('radioClient');
  const labelServer = document.getElementById('labelServerMode');
  const labelClient = document.getElementById('labelClientMode');
  const configForm = document.getElementById('configForm');
  const inputScreenName = document.getElementById('inputScreenName');
  const inputPort = document.getElementById('inputPort');
  const inputServerHost = document.getElementById('inputServerHost');
  const clientSettingsRow = document.getElementById('clientSettingsRow');
  const checkTls = document.getElementById('checkTls');
  const checkClipboard = document.getElementById('checkClipboard');
  const hostScreenLabel = document.getElementById('hostScreenLabel');
  const inputNeighborName = document.getElementById('inputNeighborName');
  const consoleBox = document.getElementById('consoleBox');
  const btnClearLogs = document.getElementById('btnClearLogs');
  const topologyCard = document.getElementById('topologyCard');

  let isRunning = false;

  function updateModeUI(mode) {
    if (mode === 'server') {
      radioServer.checked = true;
      labelServer.classList.add('active');
      labelClient.classList.remove('active');
      clientSettingsRow.style.display = 'none';
      topologyCard.style.display = 'block';
    } else {
      radioClient.checked = true;
      labelClient.classList.add('active');
      labelServer.classList.remove('active');
      clientSettingsRow.style.display = 'flex';
      topologyCard.style.display = 'none';
    }
  }

  radioServer.addEventListener('change', () => updateModeUI('server'));
  radioClient.addEventListener('change', () => updateModeUI('client'));

  async function fetchConfig() {
    try {
      const res = await fetch('/api/config');
      const data = await res.json();
      inputScreenName.value = data.screen_name || '';
      hostScreenLabel.textContent = data.screen_name || 'Local Screen';
      inputPort.value = data.port || 24800;
      inputServerHost.value = data.server_host || '';
      checkTls.checked = !!data.tls_enabled;
      checkClipboard.checked = !!data.clipboard_sharing;
      updateModeUI(data.mode || 'server');

      // Populate neighbor screen from links
      if (data.links && data.links[data.screen_name]) {
        const rightNeighbor = data.links[data.screen_name].right || '';
        inputNeighborName.value = rightNeighbor;
      }
    } catch (e) {
      console.error('Error fetching config:', e);
    }
  }

  async function fetchStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      isRunning = data.running;

      if (isRunning) {
        statusBadge.className = 'status-badge running';
        const role = data.role === 'server' ? 'Server Active' : 'Client Active';
        statusText.textContent = `${role} (${data.connected_clients?.length || 0} clients)`;
        btnToggle.textContent = 'Stop Service';
        btnToggle.className = 'btn btn-danger';
      } else {
        statusBadge.className = 'status-badge stopped';
        statusText.textContent = 'Service Stopped';
        btnToggle.textContent = 'Start Service';
        btnToggle.className = 'btn btn-primary';
      }

      // Update logs
      if (data.logs && data.logs.length > 0) {
        consoleBox.innerHTML = data.logs.map(log => `<div class="log-line">${escapeHtml(log)}</div>`).join('');
        consoleBox.scrollTop = consoleBox.scrollHeight;
      }
    } catch (e) {
      statusBadge.className = 'status-badge';
      statusText.textContent = 'Offline';
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  btnToggle.addEventListener('click', async () => {
    const endpoint = isRunning ? '/api/stop' : '/api/start';
    const mode = radioServer.checked ? 'server' : 'client';
    try {
      await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode })
      });
      setTimeout(fetchStatus, 300);
    } catch (e) {
      alert('Failed to toggle service: ' + e);
    }
  });

  configForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const mode = radioServer.checked ? 'server' : 'client';
    const screen_name = inputScreenName.value.trim();
    const neighbor = inputNeighborName.value.trim();

    const links = {};
    if (neighbor) {
      links[screen_name] = { right: neighbor };
      links[neighbor] = { left: screen_name };
    }

    const payload = {
      mode,
      screen_name,
      port: parseInt(inputPort.value, 10),
      server_host: inputServerHost.value.trim(),
      tls_enabled: checkTls.checked,
      clipboard_sharing: checkClipboard.checked,
      links
    };

    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        hostScreenLabel.textContent = screen_name;
        alert('Configuration saved successfully!');
      }
    } catch (err) {
      alert('Error saving configuration: ' + err);
    }
  });

  btnClearLogs.addEventListener('click', () => {
    consoleBox.innerHTML = '<div class="log-line info">[Console cleared]</div>';
  });

  fetchConfig();
  fetchStatus();
  setInterval(fetchStatus, 1500);
});
