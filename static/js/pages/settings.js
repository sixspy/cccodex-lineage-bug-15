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
    view.innerHTML += `<section class="card" style="margin-top:1rem">
      <h3>表名别名</h3>
      <span class="tag">${dash.chip}</span>
      <p class="muted">真相 ${dash.truth} · 包行 ${dash.pack_count} · 对齐差 ${dash.panel_pack_mismatch}</p>
      <div class="row">
        <button id="go_alias_swap" class="primary" type="button">落台</button>
        <button id="half_alias_swap" type="button">半修对齐</button>
        <button id="note_alias_swap" type="button">记旁路</button>
      </div>
    </section>`;
    document.getElementById('go_alias_swap').onclick = async () => {
      try {
        const r = await api('/api/alias_swap/commit', { method:'POST', body: JSON.stringify({ref:1}) });
        setMsg(r.message || '表名别名旧闭包');
        await renderSettings(view, setMsg);
      } catch (e) { setMsg(e.message, true); }
    };
    document.getElementById('half_alias_swap').onclick = async () => {
      try {
        const r = await api('/api/alias_swap/half', { method:'POST', body:'{}' });
        setMsg('半修 ' + r.panel_chip + ' / 包行 ' + r.pack_count);
        await renderSettings(view, setMsg);
      } catch (e) { setMsg(e.message, true); }
    };
    document.getElementById('note_alias_swap').onclick = async () => {
      try {
        await api('/api/alias_swap/note', { method:'POST', body: JSON.stringify({ref_id:1, note:'表名别名旧闭包'}) });
        setMsg('已记旁路');
        await renderSettings(view, setMsg);
      } catch (e) { setMsg(e.message, true); }
    };
  } catch (e) { /* optional surface */ }

}
