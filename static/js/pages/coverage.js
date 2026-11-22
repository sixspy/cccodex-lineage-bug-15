import { api } from '../api.js';

export async function renderCoverage(view, setMsg) {
  const reports = await api('/api/coverage/reports');
  view.innerHTML = `
    <section class="card">
      <h2>覆盖对账</h2>
      <div class="row">
        <button class="primary" id="go" type="button">跑覆盖对账</button>
      </div>
    </section>
    <section class="wall" style="margin-top:1rem">
      ${(reports.items || []).map((r) => `<article class="card">
        <h3>报告 #${r.id}</h3>
        <p>${r.summary}</p>
        <p class="muted">节点 ${r.node_count} · 已发布边 ${r.edge_count} · 孤儿 ${r.orphan_count} · 草稿边 ${r.uncovered_edges}</p>
      </article>`).join('') || '<p class="muted">暂无对账报告</p>'}
    </section>`;
  document.getElementById('go').onclick = async () => {
    try {
      const r = await api('/api/coverage/reports', { method: 'POST', body: '{}' });
      setMsg(r.report.summary);
      await renderCoverage(view, setMsg);
    } catch (e) { setMsg(e.message, true); }
  };
}
