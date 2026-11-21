import { api } from './api.js';
import { renderNodes } from './pages/nodes.js';
import { renderEdges } from './pages/edges.js';
import { renderImpact } from './pages/impact.js';
import { renderNotify } from './pages/notify.js';
import { renderCoverage } from './pages/coverage.js';
import { renderSettings } from './pages/settings.js';

const view = document.getElementById('view');
const msg = document.getElementById('msg');
const pages = {
  nodes: renderNodes,
  edges: renderEdges,
  impact: renderImpact,
  notify: renderNotify,
  coverage: renderCoverage,
  settings: renderSettings,
};

function setMsg(t, err = false) {
  msg.textContent = t || '';
  msg.className = err ? 'err' : 'muted';
}

async function boot() {
  const meta = await api('/api/meta');
  document.getElementById('lab').textContent = meta.lab || '';
  document.getElementById('chip').textContent = meta.coverage_chip || '';
  await go('nodes');
}

async function go(name) {
  document.querySelectorAll('#nav button').forEach((b) => {
    b.classList.toggle('active', b.dataset.tab === name);
  });
  await pages[name](view, setMsg);
}

document.querySelectorAll('#nav button').forEach((b) => {
  b.onclick = () => go(b.dataset.tab).catch((e) => setMsg(e.message, true));
});
document.getElementById('logout').onclick = async () => {
  await api('/api/logout', { method: 'POST', body: '{}' });
  location.href = '/login';
};

boot().catch((e) => setMsg(e.message, true));
