let currentMode = 'server';
let neighborPosition = 'right';
let isRunning = false;

document.addEventListener('DOMContentLoaded', () => {
  fetchConfig();
  fetchStatus();
  setInterval(fetchStatus, 1500);

  document.getElementById('btnMainToggle').addEventListener('click', toggleService);
  document.getElementById('inputNeighborName').addEventListener('change', saveConfig);
  document.getElementById('inputServerIp')?.addEventListener('change', saveConfig);
});

async function fetchConfig() {
  try {
    const res = await fetch('/api/config');
    const data = await res.json();
    
    document.getElementById('hostScreenTitle').textContent = data.screen_name || 'kholifan-alfon';
    document.getElementById('valScreenName').textContent = data.screen_name || 'kholifan-alfon';
    document.getElementById('checkClipboard').checked = !!data.clipboard_sharing;
    
    if (data.server_host) {
      document.getElementById('valLocalIp').textContent = data.server_host;
      if (document.getElementById('inputServerIp')) {
        document.getElementById('inputServerIp').value = data.server_host;
      }
    }

    // Set mode
    setMode(data.mode || 'server', false);

    // Parse neighbor and position
    if (data.links && data.links[data.screen_name]) {
      const link = data.links[data.screen_name];
      if (link.right) {
        document.getElementById('inputNeighborName').value = link.right;
        setNeighborPosition('right', false);
      } else if (link.left) {
        document.getElementById('inputNeighborName').value = link.left;
        setNeighborPosition('left', false);
      }
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

    const pill = document.getElementById('statusPill');
    const label = document.getElementById('statusLabel');
    const btn = document.getElementById('btnMainToggle');
    const btnText = document.getElementById('btnMainToggleText');

    if (isRunning) {
      pill.className = 'live-status-pill active';
      const modeText = data.role === 'server' ? 'Server Aktif' : 'Client Aktif';
      label.textContent = `${modeText} (${data.connected_clients?.length || 0} Terhubung)`;
      btn.className = 'btn btn-danger';
      btnText.textContent = 'Hentikan Layanan';
    } else {
      pill.className = 'live-status-pill';
      label.textContent = 'Layanan Berhenti';
      btn.className = 'btn btn-glow';
      btnText.textContent = 'Mulai Layanan';
    }

    if (data.active_screen) {
      document.getElementById('cursorScreenName').textContent = `Kursor aktif di: ${data.active_screen}`;
      animateCursorSim(data.active_screen);
    }

    if (data.logs && data.logs.length > 0) {
      const consoleBox = document.getElementById('logConsole');
      consoleBox.innerHTML = data.logs.map(l => `<div class="log-entry">${escapeHtml(l)}</div>`).join('');
      consoleBox.scrollTop = consoleBox.scrollHeight;
    }
  } catch (e) {
    // offline or restarting
  }
}

function setMode(mode, save = true) {
  currentMode = mode;
  const boxServer = document.getElementById('modeServerBox');
  const boxClient = document.getElementById('modeClientBox');
  const studioContainer = document.getElementById('studioContainer');
  const clientCard = document.getElementById('clientConnectionCard');

  if (mode === 'server') {
    boxServer.classList.add('active');
    boxClient.classList.remove('active');
    studioContainer.style.display = 'block';
    clientCard.style.display = 'none';
  } else {
    boxClient.classList.add('active');
    boxServer.classList.remove('active');
    studioContainer.style.display = 'none';
    clientCard.style.display = 'block';
  }

  if (save) saveConfig();
}

function setNeighborPosition(pos, save = true) {
  neighborPosition = pos;
  const btnLeft = document.getElementById('btnPosLeft');
  const btnRight = document.getElementById('btnPosRight');
  const zoneLeft = document.getElementById('zoneLeft');
  const zoneRight = document.getElementById('zoneRight');
  const neighborMonitor = document.getElementById('neighborMonitorFrame');

  if (pos === 'left') {
    btnLeft.classList.add('active');
    btnRight.classList.remove('active');
    zoneLeft.className = 'screen-dropzone active-assigned';
    zoneLeft.innerHTML = '';
    zoneLeft.appendChild(neighborMonitor);
    zoneRight.className = 'screen-dropzone';
    zoneRight.innerHTML = '<span class="drop-hint">+ Taruh di Kanan</span>';
  } else {
    btnRight.classList.add('active');
    btnLeft.classList.remove('active');
    zoneRight.className = 'screen-dropzone active-assigned';
    zoneRight.innerHTML = '';
    zoneRight.appendChild(neighborMonitor);
    zoneLeft.className = 'screen-dropzone';
    zoneLeft.innerHTML = '<span class="drop-hint">+ Taruh di Kiri</span>';
  }

  const meta = neighborMonitor.querySelector('.screen-meta');
  if (meta) {
    meta.textContent = pos === 'left' ? 'Layar Klien (Sebelah Kiri)' : 'Layar Klien (Sebelah Kanan)';
  }

  if (save) saveConfig();
}

async function saveConfig() {
  const screen_name = document.getElementById('hostScreenTitle').textContent.trim();
  const neighbor_name = document.getElementById('inputNeighborName').value.trim();
  const server_ip = document.getElementById('inputServerIp') ? document.getElementById('inputServerIp').value.trim() : '192.168.12.61';
  const clipboard_sharing = document.getElementById('checkClipboard').checked;

  const links = {};
  if (neighbor_name) {
    if (neighborPosition === 'right') {
      links[screen_name] = { right: neighbor_name };
      links[neighbor_name] = { left: screen_name };
    } else {
      links[screen_name] = { left: neighbor_name };
      links[neighbor_name] = { right: screen_name };
    }
  }

  const payload = {
    screen_name,
    mode: currentMode,
    server_host: server_ip,
    port: 24800,
    clipboard_sharing,
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

async function toggleService() {
  const endpoint = isRunning ? '/api/stop' : '/api/start';
  try {
    await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: currentMode })
    });
    setTimeout(fetchStatus, 300);
  } catch (e) {
    alert('Gagal mengubah status layanan: ' + e);
  }
}

function copyText(elemId) {
  const text = document.getElementById(elemId).textContent;
  navigator.clipboard.writeText(text);
  alert(`Disalin ke papan klip: ${text}`);
}

function switchGuide(platform) {
  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');

  const content = document.getElementById('guideContent');
  if (platform === 'mac') {
    content.innerHTML = `
      <p><strong>Di MacBook Anda:</strong></p>
      <ol>
        <li>Buka aplikasi Barrier atau jalankan <code>synergy-next</code>.</li>
        <li>Pilih <strong>Client</strong> dan masukkan IP Server: <code class="highlight">${document.getElementById('valLocalIp').textContent}</code>.</li>
        <li>Pastikan nama layar cocok: <code>Kholifans-MacBook</code>.</li>
        <li>Klik <strong>Start</strong>. Kursor mouse Anda siap meluncur antar layar!</li>
      </ol>
    `;
  } else if (platform === 'win') {
    content.innerHTML = `
      <p><strong>Di Komputer Windows:</strong></p>
      <ol>
        <li>Jalankan <code>synergy-next.exe</code> atau Barrier.</li>
        <li>Pilih <strong>Client</strong> dan masukkan IP Server: <code class="highlight">${document.getElementById('valLocalIp').textContent}</code>.</li>
        <li>Pastikan nama layar PC Windows Anda sudah terdaftar di Studio.</li>
        <li>Klik <strong>Start</strong>.</li>
      </ol>
    `;
  } else {
    content.innerHTML = `
      <p><strong>Di Komputer Linux Lain:</strong></p>
      <ol>
        <li>Jalankan <code>./dist/synergy-next-linux-x86_64 --mode client --server ${document.getElementById('valLocalIp').textContent}</code>.</li>
        <li>Koneksi akan otomatis terjalin seketika.</li>
      </ol>
    `;
  }
}

function animateCursorSim(activeScreen) {
  const simHost = document.getElementById('cursorSimHost');
  const simNeighbor = document.getElementById('cursorSimNeighbor');
  const hostName = document.getElementById('hostScreenTitle').textContent.trim();

  if (activeScreen === hostName) {
    simHost.style.display = 'block';
    simNeighbor.style.display = 'none';
  } else {
    simHost.style.display = 'none';
    simNeighbor.style.display = 'block';
  }
}

function clearLogs() {
  document.getElementById('logConsole').innerHTML = '<div class="log-entry info">[Log dibersihkan]</div>';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
