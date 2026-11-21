import { api } from '../api.js';

export async function renderEdges(view, setMsg) {
  const nodes = await api('/api/nodes');
  const edges = await api('/api/edges');
  const opts = (nodes.items || []).map((n) => `<option value="${n.id}">${n.node_code}</option>`).join('');
  view.innerHTML = `
    <section class="card">
      <h2>边关系</h2>
      <div class="row">
        <label>边号<input id="code" value="E-NEW-1" /></label>
        <label>上游<select id="up">${opts}</select></label>
        <label>下游<select id="down">${opts}</select></label>
        <label>变换<input id="kind" value="直抽" /></label>
        <button class="primary" id="create" type="button">创建边</button>
      </div>
    </section>
    <section class="wall" style="margin-top:1rem">
      ${(edges.items || []).map((e) => `<article class="card">
        <h3>${e.edge_code}</h3>
        <span class="tag">${e.status}</span>
        <p>${e.upstream_code} → ${e.downstream_code}</p>
        <p class="muted">${e.transform_kind} · ${e.upstream_table} → ${e.downstream_table}</p>
        <div class="row">
          <button data-pub="${e.id}" class="primary" type="button">发布</button>
          <button data-void="${e.id}" type="button">作废</button>
        </div>
      </article>`).join('') || '<p class="muted">暂无边</p>'}
    </section>`;
  document.getElementById('create').onclick = async () => {
    try {
      await api('/api/edges', {
        method: 'POST',
        body: JSON.stringify({
          edge_code: document.getElementById('code').value,
          upstream_id: Number(document.getElementById('up').value),
          downstream_id: Number(document.getElementById('down').value),
          transform_kind: document.getElementById('kind').value,
        }),
      });
      setMsg('边已创建');
      await renderEdges(view, setMsg);
    } catch (e) { setMsg(e.message, true); }
  };
  view.querySelectorAll('[data-pub]').forEach((btn) => {
    btn.onclick = async () => {
      try {
        await api('/api/edges/' + btn.dataset.pub + '/publish', { method: 'POST', body: '{}' });
        setMsg('边已发布');
        await renderEdges(view, setMsg);
      } catch (e) { setMsg(e.message, true); }
    };
  });
  view.querySelectorAll('[data-void]').forEach((btn) => {
    btn.onclick = async () => {
      try {
        await api('/api/edges/' + btn.dataset.void + '/void', { method: 'POST', body: '{}' });
        setMsg('边已作废');
        await renderEdges(view, setMsg);
      } catch (e) { setMsg(e.message, true); }
    };
  });
}
