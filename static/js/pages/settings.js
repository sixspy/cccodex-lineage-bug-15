import { api } from '../api.js';

export async function renderSettings(view, setMsg) {
  const j = await api('/api/settings');
  view.innerHTML = `
    <section class="card">
      <h2>台参数</h2>
      <div class="wall">
        ${(j.items || []).map((s) => `<article class="card">
          <h3>${s.label}</h3>
          <p class="muted">${s.key}</p>
          <div class="row">
            <input data-k="${s.key}" value="${s.value}" />
            <button data-save="${s.key}" class="primary" type="button">保存</button>
          </div>
        </article>`).join('')}
      </div>
    </section>`;
  view.querySelectorAll('[data-save]').forEach((btn) => {
    btn.onclick = async () => {
      try {
        const input = view.querySelector('input[data-k="' + btn.dataset.save + '"]');
        await api('/api/settings', {
          method: 'POST',
          body: JSON.stringify({ key: btn.dataset.save, value: input.value }),
        });
        setMsg('参数已保存');
        await renderSettings(view, setMsg);
      } catch (e) { setMsg(e.message, true); }
    };
  });

  try {
    const dash = await api('/api/alias_swap/dash');
    const nodes = await api('/api/nodes');
    const opts = (nodes.items || [])
      .map((n) => `<option value="${n.id}" data-t="${n.table_name}">${n.node_code} · ${n.table_name}</option>`)
      .join('');
    view.innerHTML += `<section class="card" style="margin-top:1rem">
      <h3>表名别名</h3>
      <span class="tag">${dash.chip}</span> <span class="tag">旧名 ${dash.old_name_count}</span>
      <p class="muted">真相 ${dash.truth} · 指纹 ${dash.edge_fp || '无'} / 当前 ${dash.current_fp} · 对齐 ${dash.aligned}</p>
      <div class="row">
        <label>节点<select id="alias_node">${opts}</select></label>
        <label>新表名<input id="alias_new" placeholder="new_table_name" /></label>
        <button id="go_alias_swap" class="primary" type="button">切换别名</button>
        <button id="verify_alias_swap" type="button">核齐放行</button>
      </div>
      <h4>旧名落点行</h4>
      ${(dash.vouchers || []).map((v) => `<p class="muted">凭证 ${v.voucher_code} · ${v.node_code} · ${v.old_table_name} → ${v.new_table_name} · 旧名边 ${v.old_edge_count} · ${v.created_at}</p>`).join('') || '<p class="muted">暂无旧名落点行</p>'}
    </section>`;
    document.getElementById('go_alias_swap').onclick = async () => {
      try {
        const sel = document.getElementById('alias_node');
        const cur = sel.options[sel.selectedIndex];
        const r = await api('/api/alias_swap/commit', {
          method: 'POST',
          body: JSON.stringify({
            node_id: Number(sel.value),
            new_name: document.getElementById('alias_new').value,
            expected_old: cur ? cur.dataset.t : '',
          }),
        });
        setMsg(r.message || '别名已切');
        await renderSettings(view, setMsg);
      } catch (e) { setMsg(e.message, true); }
    };
    document.getElementById('verify_alias_swap').onclick = async () => {
      try {
        const r = await api('/api/alias_swap/verify', { method: 'POST', body: '{}' });
        setMsg('核齐放行 · 旧名 ' + r.old_name_count);
        await renderSettings(view, setMsg);
      } catch (e) { setMsg(e.message, true); }
    };
  } catch (e) { /* optional surface */ }

}
