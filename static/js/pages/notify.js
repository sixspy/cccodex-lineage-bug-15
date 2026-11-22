import { api } from '../api.js';

export async function renderNotify(view, setMsg) {
  const jobs = await api('/api/impact/jobs');
  const notes = await api('/api/notify');
  const opts = (jobs.items || []).filter((j) => j.status === '成功')
    .map((j) => `<option value="${j.id}">${j.job_code}</option>`).join('');
  view.innerHTML = `
    <section class="card">
      <h2>下游通知</h2>
      <div class="row">
        <label>成功作业<select id="jid">${opts || '<option value="">无</option>'}</select></label>
        <button class="primary" id="go" type="button">按作业派发</button>
      </div>
    </section>
    <section class="wall" style="margin-top:1rem">
      ${(notes.items || []).map((n) => `<article class="card">
        <h3>${n.job_code} · ${n.node_code}</h3>
        <span class="tag">${n.status}</span>
        <p class="muted">${n.body}</p>
      </article>`).join('') || '<p class="muted">暂无通知</p>'}
    </section>`;
  document.getElementById('go').onclick = async () => {
    try {
      const jid = Number(document.getElementById('jid').value);
      if (!jid) throw new Error('请选择成功作业');
      const r = await api('/api/notify/dispatch', {
        method: 'POST',
        body: JSON.stringify({ job_id: jid }),
      });
      setMsg('已派发 ' + r.sent + ' 条');
      await renderNotify(view, setMsg);
    } catch (e) { setMsg(e.message, true); }
  };
}
