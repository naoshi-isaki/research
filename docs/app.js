(() => {
  'use strict';
  const sessions = [
    ['イントロダクション：政治と政策','Introduction: politics and policy'],
    ['政策形成①：政策課題の形成','Policy formation I: agenda-setting'],
    ['政策形成②：政党と政策競争','Policy formation II: parties and policy competition'],
    ['政策決定①：政策決定の過程','Decision-making I: decision processes'],
    ['政策決定②：政策決定の制度','Decision-making II: institutions'],
    ['政策実施①：実施過程と現場の裁量','Implementation I: processes and discretion'],
    ['政策実施②：行政組織と政策フィードバック','Implementation II: organisations and policy feedback'],
    ['政策評価①：政策の効果を測る','Evaluation I: assessing policy effects'],
    ['政策評価②：評価とアカウンタビリティ','Evaluation II: accountability'],
    ['政策構造①：資源','Policy structures I: resources'],
    ['政策構造②：時間','Policy structures II: time'],
    ['政策構造③：空間','Policy structures III: space'],
    ['政策構造④：領域','Policy structures IV: territory'],
    ['総括：政治から政策へ、政策から政治へ','Conclusion: from politics to policy, and back']
  ];
  let lang = 'ja';
  const courseDialog = document.getElementById('course-dialog');
  const citationDialog = document.getElementById('citation-dialog');
  let toastTimeout;
  function updateSessions() {
    const list = document.querySelector('.session-list');
    list.replaceChildren(...sessions.map(session => {
      const li = document.createElement('li');
      li.textContent = session[lang === 'ja' ? 0 : 1];
      return li;
    }));
  }
  function setLanguage(next) {
    lang = next === 'en' ? 'en' : 'ja';
    document.documentElement.lang = lang;
    document.title = lang === 'ja' ? '伊﨑直志 | 比較政治学・政党政治' : 'Naoshi Isaki | Comparative Politics & Party Politics';
    document.querySelectorAll('[data-language]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.language === lang)));
    document.querySelectorAll('.dialog-close').forEach(button=>button.setAttribute('aria-label',lang === 'ja' ? '閉じる' : 'Close'));
    updateSessions();
    updateFilterStatus();
    try { localStorage.setItem('isaki-site-language',lang); } catch (_) {}
  }
  document.querySelectorAll('[data-language]').forEach(button => button.addEventListener('click',()=>setLanguage(button.dataset.language)));
  let preferred = 'ja';
  try { preferred = localStorage.getItem('isaki-site-language') || 'ja'; } catch (_) {}
  setLanguage(preferred);
  document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click',() => {
    const filter = button.dataset.filter;
    document.querySelectorAll('[data-filter]').forEach(other => {
      const active = other === button;
      other.classList.toggle('active',active);
      other.setAttribute('aria-pressed',String(active));
    });
    let count = 0;
    document.querySelectorAll('.publication').forEach(publication => {
      const show = filter === 'all' || publication.dataset.type === filter;
      publication.hidden = !show;
      if(show)count++;
    });
    updateFilterStatus();
  }));
  function updateFilterStatus() {
    const count = [...document.querySelectorAll('.publication')].filter(row => !row.hidden).length;
    document.getElementById('filter-status').textContent = lang === 'ja'
      ? `${count}件の業績を表示しています。`
      : `Showing ${count} ${count === 1 ? 'publication' : 'publications'}.`;
  }
  function toast(message) {
    const el = document.getElementById('toast');
    clearTimeout(toastTimeout);
    el.textContent = message;
    el.classList.add('visible');
    toastTimeout = setTimeout(()=>el.classList.remove('visible'),2800);
  }
  document.getElementById('publication-list').addEventListener('click', async event => {
    const button = event.target.closest('.copy-citation');
    if (!button) return;
    const citation = button.dataset.citation;
    try {
      if (!navigator.clipboard) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(citation);
      toast(lang === 'ja' ? '引用情報をコピーしました' : 'Citation copied to clipboard');
    } catch (_) {
      document.getElementById('citation-text').value = citation;
      citationDialog.showModal();
      document.getElementById('citation-text').focus();
      document.getElementById('citation-text').select();
    }
  });
  function element(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value) node.textContent = value;
    return node;
  }
  function bilingual(parent, ja, en) {
    const a = element('span', '', ja), b = element('span', '', en);
    a.setAttribute('data-ja', ''); b.setAttribute('data-en', '');
    parent.append(a, b);
  }
  function publicationElement(record) {
    if (!['article', 'translation', 'book'].includes(record.type) ||
        typeof record.citation !== 'string' || !record.citation.trim() ||
        typeof record.title !== 'string' || typeof record.meta_ja !== 'string' ||
        typeof record.year !== 'string' || !/^\d{4}$/.test(record.year) ||
        new URL(record.url).protocol !== 'https:') throw new Error('Invalid publication');
    const row = element('article', 'publication'); row.dataset.type = record.type;
    const year = element('div', 'pub-year', record.year);
    bilingual(year, record.label_ja, record.label_en);
    const main = element('div', 'pub-main');
    main.append(element('h3', '', record.title));
    const meta = element('p', 'pub-meta');
    bilingual(meta, record.meta_ja, record.meta_en || record.meta_ja);
    main.append(meta);
    const actions = element('div', 'pub-actions');
    const link = element('a'); link.href = record.url;
    link.target = '_blank'; link.rel = 'noopener noreferrer';
    bilingual(link, record.link_label_ja || '書誌情報', record.link_label_en || 'Publication record');
    const button = element('button', 'copy-citation');
    button.type = 'button'; button.dataset.citation = record.citation;
    bilingual(button, '引用をコピー', 'Copy citation');
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 16 16'); svg.setAttribute('aria-hidden', 'true');
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M5.5 5.5h8v8h-8zM10.5 5.5v-3h-8v8h3');
    svg.append(path); button.append(svg); actions.append(link, button);
    main.append(actions); row.append(year, main); return row;
  }
  function updateBookFilter() {
    document.querySelector('[data-filter="book"]').hidden = !document.querySelector('.publication[data-type="book"]');
  }
  updateBookFilter();
  async function refreshPublications() {
    const list = document.getElementById('publication-list');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(list.dataset.feed, { cache: 'no-cache', signal: controller.signal });
      if (!response.ok) throw new Error('Publication feed unavailable');
      const records = await response.json();
      if (!Array.isArray(records) || !records.length) throw new Error('Empty publication feed');
      const rows = records.map(publicationElement);
      const filter = document.querySelector('[data-filter].active').dataset.filter;
      rows.forEach(row => { row.hidden = filter !== 'all' && row.dataset.type !== filter; });
      // Keep an active citation button focused while the data refreshes.
      const activeCitation = document.activeElement?.classList.contains('copy-citation')
        ? document.activeElement.dataset.citation : null;
      list.replaceChildren(...rows);
      updateBookFilter();
      updateFilterStatus();
      if (activeCitation) [...list.querySelectorAll('.copy-citation')]
        .find(button => button.dataset.citation === activeCitation)?.focus({ preventScroll: true });
    } catch (_) {
      // The bundled list and its copy buttons continue to work when offline.
    } finally { clearTimeout(timeout); }
  }
  refreshPublications();
  document.querySelector('.citation-close').addEventListener('click',()=>citationDialog.close());
  document.getElementById('open-course').addEventListener('click',()=>courseDialog.showModal());
  courseDialog.querySelectorAll('.dialog-close,.dialog-close-bottom').forEach(button=>button.addEventListener('click',()=>courseDialog.close()));
  [courseDialog,citationDialog].forEach(dialog=>dialog.addEventListener('click',event=>{
    const rect = dialog.getBoundingClientRect();
    if(event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom))dialog.close();
  }));
})();
