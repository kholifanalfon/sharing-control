// Barrier 1:1 Controller Logic

let appConfig = null;
let isServiceRunning = false;
let gridScreens = Array(15).fill(null); // 5x3 grid

document.addEventListener('DOMContentLoaded', () => {
  initGrid();
  loadConfig();
  pollStatus();
  setInterval(pollStatus, 1500);
});

function initGrid() {
  const container = document.getElementById('screenGrid5x3');
  container.innerHTML = '';
  for (let i = 0; i < 15; i++) {
    const cell = document.createElement('div');
    cell.className = 'grid-cell';
    cell.id = `cell-${i}`;
    cell.dataset.index = i;
    cell.ondragover = allowDrop;
    cell.ondrop = onDropCell;
    cell.ondblclick = () => editCellScreen(i);
    container.appendChild(cell);
  }
}

async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    appConfig = await res.json();

    // Mode
    if (appConfig.mode === 'server') {
      document.getElementById('radioServer').checked = true;
    } else {
      document.getElementById('radioClient').checked = true;
    }
    onModeChange();

    // IP & Screen names
    document.getElementById('lblIpAddresses').textContent = `${appConfig.server_host}, 127.0.0.1`;
    document.getElementById('inputClientScreenName').value = appConfig.screen_name;
    document.getElementById('inputServerIp').value = appConfig.server_host;

    // Populate 5x3 grid (center is index 7)
    // Put host screen in center (7), and neighbor in right (8) or left (6)
    gridScreens = Array(15).fill(null);
    gridScreens[7] = appConfig.screen_name;

    if (appConfig.links && appConfig.links[appConfig.screen_name]) {
      const links = appConfig.links[appConfig.screen_name];
      if (links.right) {
        gridScreens[8] = links.right;
      } else if (links.left) {
        gridScreens[6] = links.left;
      }
    } else {
      gridScreens[8] = 'Kholifans-MacBook';
    }
    renderGrid();
  } catch (e) {
    console.error('Failed to load config:', e);
  }
}

function renderGrid() {
  for (let i = 0; i < 15; i++) {
    const cell = document.getElementById(`cell-${i}`);
    if (!cell) continue;
    const name = gridScreens[i];
    if (name) {
      cell.className = 'grid-cell occupied';
      cell.draggable = true;
      cell.ondragstart = (e) => onDragStartCell(e, i);
      cell.innerHTML = `
        <div style="font-size: 20px;">🖥️</div>
        <div class="grid-screen-name" title="${name}">${name}</div>
      `;
    } else {
      cell.className = 'grid-cell';
      cell.draggable = false;
      cell.innerHTML = '';
    }
  }
}

async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    isServiceRunning = data.running;

    const dot = document.getElementById('statusDot');
    const msg = document.getElementById('statusMessage');
    const btnToggle = document.getElementById('btnToggleService');

    if (isServiceRunning) {
      dot.className = 'status-indicator-dot active';
      msg.textContent = `Barrier is running. (${data.role.toUpperCase()} MODE)`;
      btnToggle.textContent = 'Stop';
    } else {
      dot.className = 'status-indicator-dot';
      msg.textContent = 'Barrier is stopped.';
      btnToggle.textContent = 'Start';
    }

    if (data.logs && data.logs.length > 0) {
      const box = document.getElementById('logBox');
      box.innerHTML = data.logs.map(l => `<div class="log-line">${escapeHtml(l)}</div>`).join('');
      box.scrollTop = box.scrollHeight;
    }
  } catch (e) {
    // offline
  }
}

function onModeChange() {
  const isServer = document.getElementById('radioServer').checked;
  const serverBox = document.getElementById('serverGroupBox').querySelector('.group-content');
  const clientBox = document.getElementById('clientGroupBox').querySelector('.group-content');

  if (isServer) {
    serverBox.classList.remove('disabled-content');
    clientBox.classList.add('disabled-content');
  } else {
    clientBox.classList.remove('disabled-content');
    serverBox.classList.add('disabled-content');
  }
}

async function toggleService() {
  const endpoint = isServiceRunning ? '/api/stop' : '/api/start';
  try {
    await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: document.getElementById('radioServer').checked ? 'server' : 'client' })
    });
    setTimeout(pollStatus, 300);
  } catch (e) {
    alert('Error toggling service: ' + e);
  }
}

async function applyConfig() {
  await saveConfigFromUI();
  alert('Configuration applied successfully!');
}

async function reloadService() {
  await fetch('/api/stop', { method: 'POST' });
  await new Promise(r => setTimeout(r, 400));
  await fetch('/api/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: document.getElementById('radioServer').checked ? 'server' : 'client' })
  });
  pollStatus();
}

async function saveConfigFromUI() {
  const isServer = document.getElementById('radioServer').checked;
  const screen_name = document.getElementById('inputClientScreenName').value.trim();
  const server_host = document.getElementById('inputServerIp').value.trim();

  // Compute neighbor relationships from grid
  const hostIdx = gridScreens.indexOf(screen_name);
  const links = {};

  if (hostIdx !== -1) {
    const leftIdx = hostIdx % 5 > 0 ? hostIdx - 1 : -1;
    const rightIdx = hostIdx % 5 < 4 ? hostIdx + 1 : -1;

    links[screen_name] = {};
    if (leftIdx !== -1 && gridScreens[leftIdx]) {
      const neighbor = gridScreens[leftIdx];
      links[screen_name].left = neighbor;
      links[neighbor] = { right: screen_name };
    }
    if (rightIdx !== -1 && gridScreens[rightIdx]) {
      const neighbor = gridScreens[rightIdx];
      links[screen_name].right = neighbor;
      links[neighbor] = { left: screen_name };
    }
  }

  const payload = {
    screen_name,
    mode: isServer ? 'server' : 'client',
    server_host,
    port: 24800,
    clipboard_sharing: true,
    links
  };

  try {
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  } catch (e) {
    console.error('Failed to save config:', e);
  }
}

// Modal handling
function openServerConfigModal() {
  document.getElementById('serverConfigModal').style.display = 'flex';
}

function closeServerConfigModal() {
  document.getElementById('serverConfigModal').style.display = 'none';
}

function saveServerConfigModal() {
  saveConfigFromUI();
  closeServerConfigModal();
}

// Drag & drop on 5x3 Grid
function allowDrop(e) {
  e.preventDefault();
}

let draggedFromIndex = null;
let isDraggingNew = false;

function onDragStartCell(e, index) {
  draggedFromIndex = index;
  isDraggingNew = false;
  e.dataTransfer.setData('text/plain', gridScreens[index]);
}

function onDragNewScreen(e) {
  isDraggingNew = true;
  draggedFromIndex = null;
  e.dataTransfer.setData('text/plain', 'NewScreen');
}

function onDropCell(e) {
  e.preventDefault();
  const targetIndex = parseInt(e.currentTarget.dataset.index);
  if (isDraggingNew) {
    const name = prompt('Enter screen name:', 'New-Screen');
    if (name) {
      gridScreens[targetIndex] = name;
      renderGrid();
    }
  } else if (draggedFromIndex !== null) {
    const temp = gridScreens[targetIndex];
    gridScreens[targetIndex] = gridScreens[draggedFromIndex];
    gridScreens[draggedFromIndex] = temp;
    renderGrid();
  }
}

function onDropTrash(e) {
  e.preventDefault();
  if (draggedFromIndex !== null) {
    gridScreens[draggedFromIndex] = null;
    renderGrid();
  }
}

function editCellScreen(index) {
  const current = gridScreens[index];
  if (current) {
    const name = prompt('Edit screen name:', current);
    if (name) {
      gridScreens[index] = name;
      renderGrid();
    }
  } else {
    const name = prompt('Add screen name:', 'Kholifans-MacBook');
    if (name) {
      gridScreens[index] = name;
      renderGrid();
    }
  }
}

function showSettings() {
  alert('Settings: Port 24800, Clipboard Sharing Enabled, Native High Performance Core.');
}

function toggleLogWindow() {
  const box = document.getElementById('logBox');
  box.style.display = box.style.display === 'none' ? 'block' : 'none';
}

function showAbout() {
  alert('Barrier / Synergy Next v0.1.0\nHigh-Performance KM Switch in Rust.\nCompatible with Barrier & Synergy 1.6 wire protocol.');
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
