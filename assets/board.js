(() => {
  "use strict";
  const CATS = ["파워트레인", "전력변환", "시장·기타"];
  const PER_PAGE = 20;
  const CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩";
  const $view = document.getElementById("view");
  const state = { cat: "", imp: 0, co: "", date: "", q: "", page: 1 };
  let INDEX = null;
  const dayCache = {};

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const stars = (n) => `<span class="stars s${n}" title="중요도 ${n}">${"★".repeat(n)}${"☆".repeat(3 - n)}</span>`;
  const chip = (t, cls = "") => `<span class="chip ${cls}">${esc(t)}</span>`;
  const dateOf = (id) => `${id.slice(0, 4)}-${id.slice(4, 6)}-${id.slice(6, 8)}`;

  async function getJSON(url) {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error(`${url} (${r.status})`);
    return r.json();
  }
  async function loadIndex() {
    if (!INDEX) {
      INDEX = await getJSON("data/index.json");
      const u = new Date(INDEX.updated);
      document.getElementById("updated").textContent = isNaN(u) ? "" : `최근 갱신 ${u.toLocaleString("ko-KR", { timeZone: "Asia/Seoul", dateStyle: "medium", timeStyle: "short" })}`;
    }
    return INDEX;
  }
  async function loadDay(date) {
    if (!dayCache[date]) dayCache[date] = await getJSON(`data/posts/${date}.json`);
    return dayCache[date];
  }

  // ---------- 목록 ----------
  function filtered() {
    const q = state.q.trim().toLowerCase();
    return INDEX.items.filter((i) =>
      (!state.cat || i.category === state.cat) &&
      (!state.imp || i.importance >= state.imp) &&
      (!state.co || i.company === state.co) &&
      (!state.date || i.date === state.date) &&
      (!q || `${i.title} ${i.one_line} ${i.company} ${i.product} ${i.event_type} ${i.source_name}`.toLowerCase().includes(q))
    );
  }

  function renderList() {
    const items = filtered();
    const pages = Math.max(1, Math.ceil(items.length / PER_PAGE));
    state.page = Math.min(state.page, pages);
    const start = (state.page - 1) * PER_PAGE;
    const latest = INDEX.days[0]?.date;
    const companies = [...new Set(INDEX.items.map((i) => i.company))].sort((a, b) => a.localeCompare(b, "ko"));

    const rows = items.slice(start, start + PER_PAGE).map((i, k) => `
      <tr class="row" data-id="${esc(i.id)}">
        <td class="no">${items.length - start - k}</td>
        <td>${chip(i.category, "c-" + i.category)}</td>
        <td>${stars(i.importance)}</td>
        <td class="tt"><a class="ttl" href="#/post/${esc(i.id)}">${esc(i.title)}</a>${i.date === latest ? '<span class="new">NEW</span>' : ""}
          <div class="ol">${chip(i.company)}${esc(i.one_line)}</div></td>
        <td class="src">${esc(i.source_name)}</td>
        <td class="dt">${esc(i.date.slice(2).replace(/-/g, "."))}</td>
      </tr>`).join("");

    const pager = pages > 1 ? `<div class="pager">${Array.from({ length: pages }, (_, n) =>
      `<button data-page="${n + 1}" class="${n + 1 === state.page ? "on" : ""}">${n + 1}</button>`).join("")}</div>` : "";

    const days = INDEX.days.map((d) => `
      <li><div><a class="d" data-date="${esc(d.date)}">${esc(d.date.replace(/-/g, "."))}</a>
        <div class="meta">${d.count}건 · ★★★ ${d.stars["3"] || 0} · ★★ ${d.stars["2"] || 0}</div></div>
        ${d.pdf ? `<a class="pdf" href="${esc(d.pdf)}" target="_blank" rel="noopener">PDF</a>` : '<span class="pdf off" title="PDF 생성 대기">PDF</span>'}</li>`).join("");

    $view.innerHTML = `
      <div class="grid">
        <section class="card">
          <div class="filters">
            <div class="tabs">${["", ...CATS].map((c) => `<button class="tab ${state.cat === c ? "on" : ""}" data-cat="${esc(c)}">${c || "전체"}</button>`).join("")}</div>
            <select id="f-imp"><option value="0">중요도 전체</option><option value="3" ${state.imp === 3 ? "selected" : ""}>★★★만</option><option value="2" ${state.imp === 2 ? "selected" : ""}>★★ 이상</option></select>
            <select id="f-co"><option value="">기업 전체</option>${companies.map((c) => `<option ${state.co === c ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>
            <select id="f-date"><option value="">날짜 전체</option>${INDEX.days.map((d) => `<option value="${d.date}" ${state.date === d.date ? "selected" : ""}>${d.date}</option>`).join("")}</select>
            <input id="f-q" type="search" placeholder="제목·기업·품목 검색" value="${esc(state.q)}">
          </div>
          <div class="count">총 ${items.length}건${state.cat || state.imp || state.co || state.date || state.q ? ' · <a href="#" id="f-reset">필터 초기화</a>' : ""}</div>
          ${items.length ? `<table class="board"><thead><tr><th>번호</th><th>구분</th><th>중요도</th><th>제목</th><th>출처</th><th>날짜</th></tr></thead><tbody>${rows}</tbody></table>` : '<div class="empty">조건에 맞는 게시글이 없습니다.</div>'}
          ${pager}
        </section>
        <aside class="card side">
          <h3>일일 리포트</h3>
          <ul class="days">${days || '<li class="meta">아직 리포트가 없습니다.</li>'}</ul>
          <div class="help">날짜를 누르면 그날 게시글만 보입니다. PDF는 매일 메일로 발송되는 요약본과 같습니다.</div>
        </aside>
      </div>`;

    $view.querySelectorAll(".tab").forEach((b) => b.onclick = () => { state.cat = b.dataset.cat; state.page = 1; renderList(); });
    $view.querySelector("#f-imp").onchange = (e) => { state.imp = +e.target.value; state.page = 1; renderList(); };
    $view.querySelector("#f-co").onchange = (e) => { state.co = e.target.value; state.page = 1; renderList(); };
    $view.querySelector("#f-date").onchange = (e) => { state.date = e.target.value; state.page = 1; renderList(); };
    const q = $view.querySelector("#f-q");
    q.oninput = () => { state.q = q.value; state.page = 1; clearTimeout(q._t); q._t = setTimeout(() => { renderList(); const n = $view.querySelector("#f-q"); n.focus(); n.setSelectionRange(n.value.length, n.value.length); }, 250); };
    const reset = $view.querySelector("#f-reset");
    if (reset) reset.onclick = (e) => { e.preventDefault(); Object.assign(state, { cat: "", imp: 0, co: "", date: "", q: "", page: 1 }); renderList(); };
    $view.querySelectorAll(".pager button").forEach((b) => b.onclick = () => { state.page = +b.dataset.page; renderList(); window.scrollTo(0, 0); });
    $view.querySelectorAll("tr.row").forEach((tr) => tr.onclick = (e) => { if (!e.target.closest("a")) location.hash = `#/post/${tr.dataset.id}`; });
    $view.querySelectorAll(".days .d").forEach((a) => a.onclick = () => { state.date = a.dataset.date; state.page = 1; renderList(); window.scrollTo(0, 0); });
  }

  // ---------- 상세 ----------
  function points(list) {
    return (list || []).map((p, i) => {
      const text = typeof p === "string" ? p : p.text;
      const subs = typeof p === "string" ? [] : (p.sub || []);
      return `<div class="pt"><span>${CIRCLED[i] || i + 1 + "."}</span><div>${esc(text)}${subs.map((s) => `<div class="sub">└ ${esc(s)}</div>`).join("")}</div></div>`;
    }).join("");
  }
  function table(t) {
    if (!t) return "";
    return `${t.caption ? `<div class="tcap">${esc(t.caption)}</div>` : ""}<table class="data"><thead><tr>${(t.headers || []).map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>
      <tbody>${(t.rows || []).map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  }

  async function renderPost(id) {
    const date = dateOf(id);
    let day;
    try { day = await loadDay(date); } catch { $view.innerHTML = '<div class="card empty">게시글을 찾을 수 없습니다. <a href="#/">목록으로</a></div>'; return; }
    const it = (day.items || []).find((x) => x.id === id);
    if (!it) { $view.innerHTML = '<div class="card empty">게시글을 찾을 수 없습니다. <a href="#/">목록으로</a></div>'; return; }
    const list = filtered();
    const pos = list.findIndex((x) => x.id === id);
    const newer = pos > 0 ? list[pos - 1] : null;
    const older = pos >= 0 && pos < list.length - 1 ? list[pos + 1] : null;
    const dayInfo = INDEX.days.find((d) => d.date === date);
    const src = it.source || {};
    document.title = `${it.title} · Global Competitor Trend`;

    $view.innerHTML = `
      <article class="card detail">
        <div class="crumb"><a href="#/">게시판</a> › ${esc(it.category)} › ${esc(date)}</div>
        <h1><span>${esc(it.title)}</span><span class="srcn">출처: ${esc(src.name)}</span></h1>
        <div class="chips">${chip(it.category, "c-" + it.category)}${chip(it.company)}${it.product ? chip(it.product) : ""}${chip(it.event_type)}
          ${stars(it.importance)}<span class="why">${esc(it.importance_reason)}</span></div>
        <div class="ln">- 내용 : ${esc(it.content)}</div>
        ${it.background ? `<div class="ln arrow">→ 주요 배경 : ${esc(it.background)}</div>` : ""}
        <div class="ln arrow">→ 주요 내용</div>
        <div class="points">${points(it.points)}</div>
        ${table(it.table)}
        <div class="impl"><b>현대케피코 관점 시사점</b>${esc(it.implication)}</div>
        ${it.check_needed ? `<div class="check">확인 필요: ${esc(it.check_needed)}</div>` : ""}
        <div class="actions">
          <a class="btn pri" href="${esc(src.url)}" target="_blank" rel="noopener">원문 기사 보기 ↗</a>
          ${dayInfo && dayInfo.pdf ? `<a class="btn" href="${esc(dayInfo.pdf)}" target="_blank" rel="noopener">${esc(date)} 리포트 PDF</a>` : ""}
          <a class="btn" href="#/">목록</a>
        </div>
        <div class="extra">원문 제목: ${esc(src.original_title || "")} (${esc(src.published || "")})
          ${(it.extra_links || []).map((l) => ` · <a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.name)} ↗</a>`).join("")}</div>
        <div class="nav">
          <div>${newer ? `<span class="lbl">이전 글</span><a href="#/post/${esc(newer.id)}">${esc(newer.title)}</a>` : ""}</div>
          <div style="text-align:right">${older ? `<span class="lbl">다음 글</span><a href="#/post/${esc(older.id)}">${esc(older.title)}</a>` : ""}</div>
        </div>
      </article>`;
    window.scrollTo(0, 0);
  }

  // ---------- 라우터 ----------
  async function route() {
    try {
      await loadIndex();
    } catch (e) {
      $view.innerHTML = `<div class="card empty">데이터를 불러오지 못했습니다. (${esc(e.message)})</div>`;
      return;
    }
    const m = location.hash.match(/^#\/post\/([\w-]+)/);
    if (m) return renderPost(m[1]);
    document.title = "Global Competitor Trend · 글로벌 경쟁사 뉴스 모니터링";
    renderList();
  }
  window.addEventListener("hashchange", route);
  route();
})();
