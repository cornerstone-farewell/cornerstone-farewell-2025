#!/usr/bin/env python3
from pathlib import Path
import re
import sys

INDEX_HTML = "index.html"
SERVER_JS = "server.js"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def replace_once(content: str, old: str, new: str, label: str) -> str:
    if old not in content:
        raise RuntimeError(f"Could not find expected block for {label}")
    return content.replace(old, new, 1)


def replace_if_present(content: str, old: str, new: str) -> str:
    if old in content:
        return content.replace(old, new, 1)
    return content


def insert_before_once(content: str, marker: str, block: str, label: str) -> str:
    if block in content:
        return content
    if marker not in content:
        raise RuntimeError(f"Could not find expected marker for {label}")
    return content.replace(marker, block + marker, 1)


def insert_after_once(content: str, marker: str, block: str, label: str) -> str:
    if block in content:
        return content
    if marker not in content:
        raise RuntimeError(f"Could not find expected marker for {label}")
    return content.replace(marker, marker + block, 1)


def regex_replace_first(content: str, pattern: str, repl: str, label: str, flags: int = 0) -> str:
    new_content, count = re.subn(pattern, repl, content, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"Could not replace expected pattern for {label}")
    return new_content


def regex_remove_all(content: str, pattern: str, flags: int = 0) -> str:
    return re.sub(pattern, "", content, flags=flags)


def patch_index_html(path: Path) -> None:
    content = read_text(path)

    content = replace_if_present(
        content,
        "const FF_DEFAULTS={gratitudeWall:true,superlatives:true,wishJar:true,songDedications:true,moodBoard:true,timeCapsule:true,memoryMosaic:true};",
        "const FF_DEFAULTS={gratitudeWall:true,superlatives:true,wishJar:true,songDedications:true,moodBoard:true,timeCapsule:true,memoryMosaic:false};",
    )
    content = replace_if_present(
        content,
        " window.enableAllFunFeatures=function(){['gratitudeWall','superlatives','wishJar','songDedications','moodBoard','timeCapsule','memoryMosaic'].forEach(k=>{const el=document.getElementById(`ffToggle_${k}`);if(el)el.checked=true;window.previewFunFeatureToggle(k,true)})};",
        " window.enableAllFunFeatures=function(){['gratitudeWall','superlatives','wishJar','songDedications','moodBoard','timeCapsule','memoryMosaic'].forEach(k=>{const el=document.getElementById(`ffToggle_${k}`);if(el)el.checked=(k!=='memoryMosaic');window.previewFunFeatureToggle(k,k!=='memoryMosaic')})};",
    )
    content = replace_if_present(content, " setTimeout(loadMemoryMosaic,3000);", "")

    content = replace_if_present(content, " await autoFillMemoriesOnLoad();\n", "")
    content = regex_remove_all(
        content,
        r"\n async function autoFillMemoriesOnLoad\(\) \{.*?\n\}\n",
        flags=re.S,
    )

    content = replace_if_present(
        content,
        " memLimit: 2000,",
        " memLimit: 2000,\n previewLimit: 6,\n viewingAllMemoriesPage: false,",
    )

    patch_css = """
 <style id="fixer-stable-ui-patch">
 html.hard-refresh-top, body.hard-refresh-top { scroll-behavior: auto !important; }
 .feature-tour-overlay{
  position:fixed; inset:0; background:rgba(0,0,0,0.45); z-index:11000; display:none;
 }
 .feature-tour-overlay.active{ display:block; }
 .feature-tour-spotlight{
  position:fixed; z-index:11001; pointer-events:none; border-radius:18px;
  border:2px solid var(--primary-gold); background:transparent;
  box-shadow:0 0 0 9999px rgba(0,0,0,0.45);
  transition:all 0.35s ease;
  left:-9999px; top:-9999px; width:0; height:0;
 }
 .feature-tour-card{
  position:fixed; z-index:11002; width:min(360px, calc(100vw - 24px)); background:var(--navy-medium);
  border:1px solid var(--glass-border); border-radius:18px; padding:18px;
  box-shadow:0 20px 60px rgba(0,0,0,0.45); left:-9999px; top:-9999px;
 }
 .feature-tour-card h3{ color:var(--primary-gold); margin-bottom:8px; font-family:var(--font-display); }
 .feature-tour-card p{ color:var(--text-muted); margin-bottom:12px; font-size:0.95rem; }
 .feature-tour-actions{ display:flex; justify-content:space-between; gap:10px; }
 .feature-tour-fab{
  position:fixed; right:18px; bottom:18px; z-index:2501; border:none;
  background:var(--gradient-gold); color:var(--navy-dark); border-radius:999px;
  padding:10px 14px; font-weight:700; cursor:pointer; box-shadow:var(--shadow-gold);
 }
 .memories-preview-actions{ display:flex; justify-content:center; margin-top:28px; }
 .memories-page{
  min-height:100vh; background:linear-gradient(180deg, var(--navy-dark) 0%, var(--navy-medium) 100%);
  color:var(--text-light); padding:110px 20px 60px;
 }
 .memories-page.hidden{ display:none; }
 .memories-page-header{
  max-width:var(--container-width); margin:0 auto 28px; display:flex; justify-content:space-between;
  gap:16px; align-items:center; flex-wrap:wrap;
 }
 .memories-page-grid{
  max-width:var(--container-width); margin:0 auto;
  display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:24px;
 }
 #livePill,
 #ghostCursorToggle,
 #ghostCursorPopup,
 #ghostOffModal,
 #paperTutorial,
 #wsStatusBadge,
 .ghost-cursor{ display:none !important; }
 #distanceMapWrap{
  display:block !important; position:relative !important; max-width:1200px !important; margin:0 auto !important;
 }
 #distanceGlobeCanvas{
  width:100% !important; height:650px !important; position:relative !important;
 }
 #distanceMapSection #distanceGlobeUi{
  position:relative !important; max-width:1200px !important; margin:0 auto 14px !important;
 }
 #distanceMapSection #distanceGlobeCanvas canvas,
 #distanceMapSection #distanceGlobeCanvas > div{
  margin:0 auto !important;
 }
 #distanceSearchResultsV7 .btn{
  width:100%;
  justify-content:flex-start;
  text-align:left;
  white-space:normal;
 }
 @media (max-width: 900px){
  .feature-tour-card{ left:12px !important; right:12px !important; width:auto; top:auto !important; bottom:12px !important; }
 }
 </style>
"""
    content = insert_before_once(content, "</head>", patch_css, "stable css")

    old_memories_end = """ <div class="load-more-wrap" id="loadMoreWrap" style="display:none;">
 <button class="btn btn-secondary load-more-btn" id="loadMoreBtn" type="button">Load More</button>
 </div>
 </div>
 </section>"""
    new_memories_end = """ <div class="memories-preview-actions">
 <button class="btn btn-secondary" id="viewAllMemoriesBtn" type="button">View All Memories</button>
 </div>
 <div class="load-more-wrap" id="loadMoreWrap" style="display:none;">
 <button class="btn btn-secondary load-more-btn" id="loadMoreBtn" type="button">Load More</button>
 </div>
 </div>
 </section>
 <section id="memoriesPage" class="memories-page hidden">
 <div class="memories-page-header">
 <div>
 <span class="section-badge">All Memories</span>
 <h2 class="section-title">Every <span class="highlight">Memory</span></h2>
 </div>
 <button class="btn btn-secondary" id="backToHomeFromMemoriesPage" type="button">Back to Home</button>
 </div>
 <div class="memories-page-grid" id="memoriesPageGrid" aria-live="polite"></div>
 </section>"""
    if 'id="memoriesPage"' not in content and old_memories_end in content:
        content = content.replace(old_memories_end, new_memories_end, 1)

    init_memory_old = """ function initMemoryWall() {
 document.querySelectorAll('.memory-filters .filter-btn').forEach(btn => {
 btn.addEventListener('click', async () => {
 document.querySelectorAll('.memory-filters .filter-btn').forEach(b => b.classList.remove('active'));
 btn.classList.add('active');
 state.currentFilter = btn.dataset.filter;
 await loadMemories(true);
 });
 });
 const loadMoreBtn = document.getElementById('loadMoreBtn');
 if (loadMoreBtn) {
 loadMoreBtn.addEventListener('click', async () => {
 await loadMemories(false);
 });
 }
}"""
    init_memory_new = """ function initMemoryWall() {
 document.querySelectorAll('.memory-filters .filter-btn').forEach(btn => {
 btn.addEventListener('click', async () => {
 document.querySelectorAll('.memory-filters .filter-btn').forEach(b => b.classList.remove('active'));
 btn.classList.add('active');
 state.currentFilter = btn.dataset.filter;
 await loadMemories(true);
 });
 });
 const loadMoreBtn = document.getElementById('loadMoreBtn');
 if (loadMoreBtn) {
 loadMoreBtn.addEventListener('click', async () => {
 await loadMemories(false);
 });
 }
}
function getDisplayMemories() {
 return state.viewingAllMemoriesPage ? state.memories : state.memories.slice(0, state.previewLimit);
}
function renderMemoriesPage() {
 const grid = document.getElementById('memoriesPageGrid');
 if (!grid) return;
 if (!state.memories.length) {
  grid.innerHTML = `<div class="memory-empty" style="grid-column: 1/-1;"><div class="memory-empty-icon"> </div><h3>No Memories Yet</h3><p>Be the first to share!</p></div>`;
  return;
 }
 grid.innerHTML = state.memories.map((memory, index) => `
 <div class="memory-card" data-index="${index}">
 <div class="memory-media" onclick="openLightbox(${index})">
 ${memory.file_type === 'video'
 ? `<video src="${memory.file_url}" preload="metadata"></video><div class="play-button">▶</div>`
 : `<img src="${memory.file_url}" alt="${escapeAttr(memory.caption)}" loading="lazy" />`}
 <span class="memory-type-badge">${escapeHtml(memory.memory_type)}</span>
 ${memory.featured ? `<span class="memory-featured-badge">Featured</span>` : ''}
 </div>
 <div class="memory-content">
 <div class="memory-author">
 <div class="memory-avatar">${escapeHtml((memory.student_name || '').charAt(0).toUpperCase())}</div>
 <div class="memory-author-info">
 <div class="memory-author-name">${escapeHtml(memory.student_name || '')}</div>
 <div class="memory-time">${timeAgo(memory.created_at)}</div>
 </div>
 </div>
 <p class="memory-caption">${escapeHtml(memory.caption || '')}</p>
 </div>
 </div>
 `).join('');
}
function openMemoriesPage() {
 state.viewingAllMemoriesPage = true;
 const page = document.getElementById('memoriesPage');
 if (page) page.classList.remove('hidden');
 const topTarget = document.getElementById('memoriesPage');
 if (topTarget) topTarget.scrollIntoView({ behavior: 'auto', block: 'start' });
 renderMemoriesPage();
 history.replaceState(null, '', '#memories-page');
}
function backToMainPage() {
 state.viewingAllMemoriesPage = false;
 const page = document.getElementById('memoriesPage');
 if (page) page.classList.add('hidden');
 history.replaceState(null, '', '#home');
 const home = document.getElementById('home');
 if (home) home.scrollIntoView({ behavior: 'auto', block: 'start' });
}"""
    if "function getDisplayMemories()" not in content and init_memory_old in content:
        content = content.replace(init_memory_old, init_memory_new, 1)

    render_memories_old = """function renderMemories() {
 const grid = document.getElementById('memoryGrid');
 if (!grid) return;
 const countPill = document.getElementById('memCountPill');
 if (countPill) {
 countPill.textContent = `${state.memories.length} loaded${state.memHasMore ? ' • more available' : ''}`;
 }
 if (displayMemories.length === 0) {"""
    render_memories_new = """function renderMemories() {
 const grid = document.getElementById('memoryGrid');
 if (!grid) return;
 const displayMemories = getDisplayMemories();
 const countPill = document.getElementById('memCountPill');
 if (countPill) {
 countPill.textContent = state.viewingAllMemoriesPage ? `${state.memories.length} loaded` : `${displayMemories.length} of ${state.memories.length} shown`;
 }
 if (displayMemories.length === 0) {"""
    if render_memories_old in content:
        content = content.replace(render_memories_old, render_memories_new, 1)

    content = content.replace(" grid.innerHTML = state.memories.map((memory, index) => `", " grid.innerHTML = displayMemories.map((memory, index) => `")
    content = content.replace(" loadMoreWrap.style.display = (!state.infiniteScroll && state.memHasMore) ? 'flex' : 'none';", " loadMoreWrap.style.display = (!state.infiniteScroll && state.memHasMore && state.viewingAllMemoriesPage) ? 'flex' : 'none';")

    memory_bindings = """
 document.addEventListener('DOMContentLoaded', () => {
 const viewAllBtn = document.getElementById('viewAllMemoriesBtn');
 if (viewAllBtn) viewAllBtn.addEventListener('click', openMemoriesPage);
 const backBtn = document.getElementById('backToHomeFromMemoriesPage');
 if (backBtn) backBtn.addEventListener('click', backToMainPage);
 document.querySelectorAll('a[href="#home"]').forEach(el => {
  el.addEventListener('click', (evt) => {
   evt.preventDefault();
   backToMainPage();
  });
 });
 });
 window.addEventListener('popstate', () => {
 const page = document.getElementById('memoriesPage');
 if (!page) return;
 if (location.hash === '#memories-page') {
  state.viewingAllMemoriesPage = true;
  page.classList.remove('hidden');
  renderMemoriesPage();
 } else {
  state.viewingAllMemoriesPage = false;
  page.classList.add('hidden');
 }
 });
"""
    content = insert_before_once(content, " document.addEventListener('keydown', (e) => {", memory_bindings, "memory bindings")

    stable_tour_script = """
<script id="fixer-stable-tour-script">
(function(){
 if (window.__FIXER_STABLE_TOUR__) return;
 window.__FIXER_STABLE_TOUR__ = true;
 const TOUR_KEY = 'cornerstone_tour_seen_v2';
 function addTourFab(){
  if (document.getElementById('featureTourFab')) return;
  const btn = document.createElement('button');
  btn.id = 'featureTourFab';
  btn.className = 'feature-tour-fab';
  btn.type = 'button';
  btn.textContent = 'Tutorial';
  btn.addEventListener('click', startSiteTour);
  document.body.appendChild(btn);
 }
 function ensureTourNodes(){
  if (!document.getElementById('featureTourOverlay')){
   const overlay = document.createElement('div');
   overlay.id = 'featureTourOverlay';
   overlay.className = 'feature-tour-overlay';
   overlay.innerHTML = '<div id="featureTourSpotlight" class="feature-tour-spotlight"></div><div id="featureTourCard" class="feature-tour-card"></div>';
   document.body.appendChild(overlay);
  }
 }
 function buildSteps(){
  return [
   { selector:'#home .hero-buttons', title:'Welcome', text:'Use these buttons to upload a memory or explore the memory wall.' },
   { selector:'#countdown', title:'Countdown', text:'This section shows the live countdown to the farewell event.' },
   { selector:'#memories', title:'Memories Preview', text:'The homepage shows six selected memories only for faster loading.' },
   { selector:'#viewAllMemoriesBtn', title:'View All', text:'Open the full dedicated memories page from here.' },
   { selector:'#upload', title:'Upload', text:'Approved uploads appear after admin review only.' },
   { selector:'#distanceMapSection', title:'Future Path Globe', text:'Select your name, section, and future places, then save them to the globe.' },
   { selector:'#compilations', title:'Compilations', text:'Curated slideshows appear here.' }
  ];
 }
 function stopSiteTour(){
  const overlay = document.getElementById('featureTourOverlay');
  const spot = document.getElementById('featureTourSpotlight');
  const card = document.getElementById('featureTourCard');
  if (overlay) overlay.classList.remove('active');
  if (spot) {
   spot.style.left = '-9999px';
   spot.style.top = '-9999px';
   spot.style.width = '0px';
   spot.style.height = '0px';
  }
  if (card) {
   card.style.left = '-9999px';
   card.style.top = '-9999px';
  }
 }
 function startSiteTour(){
  ensureTourNodes();
  const steps = buildSteps();
  let idx = 0;
  const overlay = document.getElementById('featureTourOverlay');
  const spot = document.getElementById('featureTourSpotlight');
  const card = document.getElementById('featureTourCard');
  function render(){
   if (idx >= steps.length) {
    stopSiteTour();
    return;
   }
   const step = steps[idx];
   const el = document.querySelector(step.selector);
   if (!el) {
    idx += 1;
    render();
    return;
   }
   el.scrollIntoView({ behavior:'smooth', block:'center' });
   setTimeout(() => {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) {
     idx += 1;
     render();
     return;
    }
    overlay.classList.add('active');
    spot.style.left = Math.max(8, r.left - 8) + 'px';
    spot.style.top = Math.max(8, r.top - 8) + 'px';
    spot.style.width = Math.max(40, r.width + 16) + 'px';
    spot.style.height = Math.max(40, r.height + 16) + 'px';
    card.style.left = Math.min(window.innerWidth - 380, Math.max(12, r.left)) + 'px';
    card.style.top = Math.min(window.innerHeight - 170, Math.max(12, r.bottom + 12)) + 'px';
    card.innerHTML = `<h3>${step.title}</h3><p>${step.text}</p><div class="feature-tour-actions"><button class="btn btn-secondary" type="button" id="tourSkipBtn">Close</button><button class="btn btn-primary" type="button" id="tourNextBtn">${idx === steps.length - 1 ? 'Done' : 'Next'}</button></div>`;
    document.getElementById('tourSkipBtn')?.addEventListener('click', stopSiteTour);
    document.getElementById('tourNextBtn')?.addEventListener('click', () => {
     idx += 1;
     render();
    });
   }, 450);
  }
  render();
 }
 window.startSiteTour = startSiteTour;
 document.addEventListener('DOMContentLoaded', () => {
  addTourFab();
  ensureTourNodes();
  const page = document.getElementById('memoriesPage');
  if (location.hash === '#memories-page' && page) {
   state.viewingAllMemoriesPage = true;
   page.classList.remove('hidden');
   if (typeof renderMemoriesPage === 'function') renderMemoriesPage();
  }
  const navType = performance.getEntriesByType && performance.getEntriesByType('navigation')[0] ? performance.getEntriesByType('navigation')[0].type : '';
  if (navType === 'reload') {
   document.documentElement.classList.add('hard-refresh-top');
   document.body.classList.add('hard-refresh-top');
   window.scrollTo(0, 0);
   setTimeout(() => {
    document.documentElement.classList.remove('hard-refresh-top');
    document.body.classList.remove('hard-refresh-top');
   }, 1200);
  }
  if (!localStorage.getItem(TOUR_KEY)) {
   setTimeout(() => {
    startSiteTour();
    localStorage.setItem(TOUR_KEY, '1');
   }, 1200);
  }
 });
})();
</script>
"""
    content = insert_before_once(content, "</body>", stable_tour_script, "stable tour script")

    content = insert_before_once(
        content,
        '<script src="https://unpkg.com/three@0.160.0/build/three.min.js"></script>',
        '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />\n<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>\n',
        "leaflet assets",
    )

    content = replace_if_present(
        content,
        """ function installCleanMultiplayer(){
 const base = (window.CONFIG && window.CONFIG.API_BASE) ? window.CONFIG.API_BASE : null;
 if (!base) {
 setWsBadge(false, 'Multiplayer: no backend URL');
 return;
 }
 connectMultiplayerWS();
 installGhostTracking();
 installSharedNotes();
 }""",
        """ function installCleanMultiplayer(){
 setWsBadge(false, 'Multiplayer removed');
 installSharedNotes();
 }""",
    )

    content = replace_if_present(
        content,
        """ function connectMultiplayerWS(){
 try{
 const base = new URL(window.CONFIG.API_BASE);
 const wsUrl = `${base.protocol === 'https:' ? 'wss' : 'ws'}://${base.host}`;
 const ws = new WebSocket(wsUrl);
 window.__SNIPER_WS__ = ws;
 ws.onopen = () => {
 SNIPER.wsConnected = true;
 setWsBadge(true, 'Multiplayer: live');
 };
 ws.onclose = () => {
 SNIPER.wsConnected = false;
 setWsBadge(false, 'Multiplayer: disconnected');
 clearTimeout(SNIPER.wsReconnectTimer);
 SNIPER.wsReconnectTimer = setTimeout(connectMultiplayerWS, 2000);
 };
 ws.onerror = () => {
 SNIPER.wsConnected = false;
 setWsBadge(false, 'Multiplayer: error');
 };
 ws.onmessage = (msg) => {
 let data = null;
 try { data = JSON.parse(msg.data); } catch(_) { return; }
 if (!data) return;
 if (data.event === 'ghost:move') handleGhostMove(data.payload);
 if (data.event === 'paper:note' && data.payload?.note) handleIncomingNote(data.payload.note);
 };
 }catch(_){
 setWsBadge(false, 'Multiplayer: unavailable');
 }
 }""",
        """ function connectMultiplayerWS(){
 return;
 }""",
    )

    content = replace_if_present(
        content,
        """ function installGhostTracking(){
 document.addEventListener('mousemove', (e) => {
 if (introVisible()) return;
 if (Date.now() - SNIPER.wsSendThrottle < 35) return;
 SNIPER.wsSendThrottle = Date.now();
 const initials = getInitialsForGhost();
 sendWS({
 type: 'ghost:move',
 id: SNIPER.ghostId,
 x: e.clientX,
 y: e.clientY,
 initials
 });
 }, { passive: true });
 }""",
        """ function installGhostTracking(){
 return;
 }""",
    )

    content = replace_if_present(
        content,
        """ function handleGhostMove(p){
 if (!p || p.id === SNIPER.ghostId) return;
 let ghost = SNIPER.ghosts.get(p.id);
 if (!ghost){
 const el = document.createElement('div');
 el.className = 'ghost-cursor';
 el.innerHTML = '<div class="tip"></div><div class="label"></div>';
 document.body.appendChild(el);
 ghost = { el };
 SNIPER.ghosts.set(p.id, ghost);
 }
 ghost.el.querySelector('.label').textContent = p.initials || 'GS';
 ghost.el.style.left = p.x + 'px';
 ghost.el.style.top = p.y + 'px';
 }""",
        """ function handleGhostMove(p){
 return;
 }""",
    )

    content = replace_if_present(
        content,
        """ function installSharedNotes(){
 clearInterval(SNIPER.notePoller);
 SNIPER.notePoller = setInterval(async () => {
 if (introVisible()) return;
 try{
 const res = await fetch(apiUrl('/api/paper-notes/random-memory'));
 const data = await res.json();
 if (!data.success || !data.note) return;
 if (SNIPER.lastIncomingNoteId === data.note.id) return;
 SNIPER.lastIncomingNoteId = data.note.id;
 handleIncomingNote(data.note);
 }catch(_){}
 }, 12000);
 const btn = document.getElementById('sendNoteBtn');
 if (btn && !btn.dataset.sniperV7Bound){
 btn.dataset.sniperV7Bound = '1';
 btn.onclick = null;
 btn.addEventListener('click', async () => {
 const memories = ((window.state && window.state.memories) || []).filter(m => m && m.id && (m.caption || '').trim());
 if (!memories.length) {
 return window.showNotification?.('info', 'No memories', 'No approved memories are available yet.');
 }
 const selected = memories[Math.floor(Math.random() * memories.length)];
 try{
 const res = await fetch(apiUrl('/api/paper-notes/from-memory'), {
 method:'POST',
 headers:{'Content-Type':'application/json'},
 body:JSON.stringify({ memoryId: selected.id })
 });
 const data = await res.json();
 if (data.success && data.note) {
 sendWS({ type:'paper:note:broadcast', note: data.note });
 launchSharedPlane(data.note);
 }
 }catch(_){}
 });
 }
 }""",
        """ function installSharedNotes(){
 const btn = document.getElementById('sendNoteBtn');
 if (!btn || btn.dataset.sniperV7Bound === '1') return;
 btn.dataset.sniperV7Bound = '1';
 btn.onclick = null;
 btn.addEventListener('click', async () => {
  const memories = ((window.state && window.state.memories) || []).filter(m => m && m.id && (m.caption || '').trim());
  if (!memories.length) {
   return window.showNotification?.('info', 'No memories', 'No approved memories are available yet.');
  }
  const selected = memories[Math.floor(Math.random() * memories.length)];
  try{
   const res = await fetch(apiUrl('/api/paper-notes/from-memory'), {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({ memoryId: selected.id })
   });
   const data = await res.json();
   if (!data.success) {
    return window.showNotification?.('error', 'Could not post note', data.error || 'Failed to post note.');
   }
   window.showNotification?.('success', 'Memory note sent', 'Your memory note was posted.');
  }catch(e){
   window.showNotification?.('error', 'Could not post note', e.message);
  }
 });
 }""",
    )

    content = replace_if_present(
        content,
        """ function handleIncomingNote(note){
 launchSharedPlane(note);
 }""",
        """ function handleIncomingNote(note){
 return;
 }""",
    )

    content = replace_if_present(
        content,
        """ function launchSharedPlane(note){
 const layer = document.getElementById('paperAirplaneLayer');
 if (!layer) return;
 const plane = document.createElement('div');
 plane.className = 'paper-plane';
 plane.title = 'Catch this memory note';
 plane.innerHTML = '<div class="plane-fold"></div><div class="plane-memory-badge">MEMORY</div>';
 layer.appendChild(plane);
 let x = -90;
 let yBase = 90 + Math.random() * Math.min(window.innerHeight * 0.48, 300);
 let t = 0;
 let vx = 3.4 + Math.random() * 1.5;
 const step = () => {
 t += 0.04;
 x += vx;
 const y = yBase + Math.sin(t * 2.3) * 16 + Math.cos(t * 1.2) * 8;
 plane.style.left = x + 'px';
 plane.style.top = y + 'px';
 plane.style.transform = `rotate(${Math.sin(t * 2.3) * 8 - 8}deg)`;
 if (x > window.innerWidth + 120){
 plane.remove();
 return;
 }
 requestAnimationFrame(step);
 };
 plane.addEventListener('click', () => {
 alert(note.caption || note.text || 'A memory from someone.');
 plane.remove();
 });
 step();
 }""",
        """ function launchSharedPlane(note){
 return;
 }""",
    )

    old_flow = """ function upgradeDistanceFlowToMaps(){
 const section = document.getElementById('distanceMapSection');
 const controls = document.getElementById('distanceControls');
 if (!section || !controls || document.getElementById('distanceMapsFlowCard')) return;
 const info = document.createElement('div');
 info.id = 'distanceMapsFlowCard';
 info.innerHTML = `
 <strong>How this works:</strong>
 choose whether you are pinning your 11th / 12th place or your university dream,
 click the map button to open Google Maps in a new tab, find the place there, copy the
 coordinates or map search result, then come back and confirm it below.
 `;
 controls.insertAdjacentElement('beforebegin', info);
 const panel = document.createElement('div');
 panel.id = 'distanceConfirmPanel';
 panel.innerHTML = `
 <div class="row">
 <div class="form-group">
 <label>Your Name</label>
 <input class="form-input" id="distanceStudentNameV7" maxlength="80" placeholder="Enter your name" />
 </div>
 <div class="form-group">
 <label>What are you pinning?</label>
 <select class="form-select" id="distancePinTypeV7">
 <option value="school">11th / 12th future place</option>
 <option value="university">University aim place</option>
 </select>
 </div>
 </div>
 <div class="row">
 <div class="form-group">
 <label>Google Maps coordinates</label>
 <input class="form-input" id="distanceCoordsV7" placeholder="Example: 12.9716,77.5946" />
 </div>
 <div class="form-group">
 <label>Place label</label>
 <input class="form-input" id="distancePlaceLabelV7" maxlength="120" placeholder="Example: Bangalore" />
 </div>
 </div>
 <div style="display:flex; gap:10px; flex-wrap:wrap; justify-content:center; margin-top:12px;">
 <button class="btn btn-primary" type="button" id="distanceOpenMapsV7">Open Google Maps</button>
 <button class="btn btn-secondary" type="button" id="distanceUseCoordsV7">Use These Coordinates</button>
 <button class="btn btn-primary" type="button" id="distanceSavePinsV7">Confirm Future Path</button>
 </div>
 <div class="hint">The site will only ask for this after the intro is done and after you scroll below the countdown.</div>
 <div id="distanceSelectedReview"></div>
 `;
 controls.insertAdjacentElement('afterend', panel);
 controls.innerHTML = `
 <button class="btn btn-primary" type="button" id="distanceLaunchBtnV7">Start Future Pinning</button>
 <button class="btn btn-secondary" type="button" id="distanceRefreshBtnV7">Refresh Globe</button>
 `;
 document.getElementById('distanceLaunchBtnV7')?.addEventListener('click', () => {
 panel.classList.add('active');
 section.scrollIntoView({ behavior: 'smooth', block: 'start' });
 });
 document.getElementById('distanceOpenMapsV7')?.addEventListener('click', () => {
 if (introVisible()) return;
 const label = document.getElementById('distancePlaceLabelV7')?.value?.trim() || 'future college';
 window.open('https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(label), '_blank');
 });
 document.getElementById('distanceUseCoordsV7')?.addEventListener('click', applyCoordsToPendingV7);
 document.getElementById('distanceSavePinsV7')?.addEventListener('click', saveFuturePathV7);
 document.getElementById('distanceRefreshBtnV7')?.addEventListener('click', () => loadClassPathsGlobeV7());
 loadClassPathsGlobeV7();
 }"""
    new_flow = """ function upgradeDistanceFlowToMaps(){
 const section = document.getElementById('distanceMapSection');
 const controls = document.getElementById('distanceControls');
 if (!section || !controls || document.getElementById('distanceMapsFlowCard')) return;
 const info = document.createElement('div');
 info.id = 'distanceMapsFlowCard';
 info.innerHTML = `
 <strong>How this works:</strong>
 first select your name and section from the admin-created list, then choose whether you are placing your 11th/12th point or university point.
 Search for the place, choose a result, fine-tune it on the map if needed, and save it. Curved lines on the globe connect Cornerstone School,
 your 11th/12th point, and your university point.
 `;
 controls.insertAdjacentElement('beforebegin', info);
 const panel = document.createElement('div');
 panel.id = 'distanceConfirmPanel';
 panel.innerHTML = `
 <div class="row">
  <div class="form-group">
   <label>Your Name</label>
   <select class="form-select" id="distanceStudentNameV7"><option value="">Select your name</option></select>
  </div>
  <div class="form-group">
   <label>Section</label>
   <select class="form-select" id="distanceSectionV7"><option value="">Select section</option></select>
  </div>
 </div>
 <div class="row">
  <div class="form-group">
   <label>What are you pinning?</label>
   <select class="form-select" id="distancePinTypeV7">
    <option value="school">11th / 12th future place</option>
    <option value="university">University aim place</option>
   </select>
  </div>
  <div class="form-group">
   <label>Place label</label>
   <input class="form-input" id="distancePlaceLabelV7" maxlength="120" placeholder="Chosen place name" />
  </div>
 </div>
 <div class="row">
  <div class="form-group">
   <label>Search place</label>
   <input class="form-input" id="distancePlaceSearchV7" placeholder="Search for a place" />
   <div id="distanceSearchResultsV7" style="margin-top:8px; display:grid; gap:8px;"></div>
  </div>
  <div class="form-group">
   <label>Coordinates</label>
   <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
    <input class="form-input" id="distanceLatV7" placeholder="Latitude" readonly />
    <input class="form-input" id="distanceLngV7" placeholder="Longitude" readonly />
   </div>
  </div>
 </div>
 <div style="margin-top:12px;">
  <div id="distanceLeafletPicker" style="height:420px; width:100%; border-radius:18px; overflow:hidden; border:1px solid rgba(255,255,255,0.12);"></div>
 </div>
 <div style="display:flex; gap:10px; flex-wrap:wrap; justify-content:center; margin-top:12px;">
  <button class="btn btn-secondary" type="button" id="distanceSearchBtnV7">Search</button>
  <button class="btn btn-primary" type="button" id="distanceSavePinsV7">Confirm Future Path</button>
 </div>
 <div class="hint">Nothing can be selected here unless it was configured by the admin first.</div>
 <div id="distanceSelectedReview"></div>
 `;
 controls.insertAdjacentElement('afterend', panel);
 controls.innerHTML = `
 <button class="btn btn-primary" type="button" id="distanceLaunchBtnV7">Start Future Pinning</button>
 <button class="btn btn-secondary" type="button" id="distanceRefreshBtnV7">Refresh Globe</button>
 `;
 document.getElementById('distanceLaunchBtnV7')?.addEventListener('click', () => {
  panel.classList.add('active');
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  setTimeout(() => {
   initLeafletDistancePickerV7();
   loadStudentDirectoryV7();
  }, 120);
 });
 document.getElementById('distanceSearchBtnV7')?.addEventListener('click', searchLeafletPlaceV7);
 document.getElementById('distanceSavePinsV7')?.addEventListener('click', saveFuturePathV7);
 document.getElementById('distanceRefreshBtnV7')?.addEventListener('click', () => loadClassPathsGlobeV7());
 loadClassPathsGlobeV7();
 }"""
    content = replace_if_present(content, old_flow, new_flow)

    if "async function loadStudentDirectoryV7()" not in content:
        helper_block = """ async function loadStudentDirectoryV7(){
 try{
  const res = await fetch(apiUrl('/api/student-directory'));
  const data = await res.json();
  if (!data.success) return;
  const nameSel = document.getElementById('distanceStudentNameV7');
  const sectionSel = document.getElementById('distanceSectionV7');
  if (nameSel) {
   nameSel.innerHTML = '<option value="">Select your name</option>' + (data.students || []).map(s => `<option value="${escapeAttr(s.name)}">${escapeHtml(s.name)}</option>`).join('');
  }
  if (sectionSel) {
   const sections = Array.from(new Set((data.students || []).map(s => String(s.section || '').trim()).filter(Boolean)));
   sectionSel.innerHTML = '<option value="">Select section</option>' + sections.map(s => `<option value="${escapeAttr(s)}">${escapeHtml(s)}</option>`).join('');
  }
 }catch(_){}
 }
 let distanceLeafletMapV7 = null;
 let distanceLeafletMarkerV7 = null;
 function setLeafletPickedPointV7(lat, lng, label){
  const latEl = document.getElementById('distanceLatV7');
  const lngEl = document.getElementById('distanceLngV7');
  const labelEl = document.getElementById('distancePlaceLabelV7');
  if (latEl) latEl.value = String(Number(lat).toFixed(6));
  if (lngEl) lngEl.value = String(Number(lng).toFixed(6));
  if (labelEl && label) labelEl.value = label;
  if (!distanceLeafletMapV7) return;
  if (!distanceLeafletMarkerV7) {
   distanceLeafletMarkerV7 = L.marker([lat, lng]).addTo(distanceLeafletMapV7);
  } else {
   distanceLeafletMarkerV7.setLatLng([lat, lng]);
  }
  distanceLeafletMapV7.setView([lat, lng], Math.max(distanceLeafletMapV7.getZoom(), 4));
 }
 function initLeafletDistancePickerV7(){
  const mapEl = document.getElementById('distanceLeafletPicker');
  if (!mapEl || typeof L === 'undefined') return;
  if (!distanceLeafletMapV7) {
   distanceLeafletMapV7 = L.map(mapEl, { center:[17.3850, 78.4867], zoom:4, worldCopyJump:true });
   L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap contributors'
   }).addTo(distanceLeafletMapV7);
   distanceLeafletMapV7.on('click', (e) => {
    setLeafletPickedPointV7(e.latlng.lat, e.latlng.lng);
    applyCoordsToPendingV7();
   });
  } else {
   distanceLeafletMapV7.invalidateSize();
  }
 }
 async function searchLeafletPlaceV7(){
  const search = document.getElementById('distancePlaceSearchV7')?.value?.trim();
  const box = document.getElementById('distanceSearchResultsV7');
  if (box) box.innerHTML = '';
  if (!search) {
   return window.showNotification?.('error', 'Search needed', 'Enter a place to search.');
  }
  try{
   const res = await fetch('https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&q=' + encodeURIComponent(search), {
    headers: { 'Accept': 'application/json' }
   });
   const data = await res.json();
   if (!Array.isArray(data) || !data.length) {
    return window.showNotification?.('error', 'Not found', 'Could not find that place.');
   }
   if (!box) {
    const item = data[0];
    const lat = Number(item.lat);
    const lng = Number(item.lon);
    const label = String(item.display_name || search).split(',').slice(0, 2).join(',').trim();
    setLeafletPickedPointV7(lat, lng, label);
    applyCoordsToPendingV7();
    return;
   }
   box.innerHTML = data.map(item => {
    const label = String(item.display_name || search);
    return `<button type="button" class="btn btn-secondary" data-lat="${escapeAttr(item.lat)}" data-lng="${escapeAttr(item.lon)}" data-label="${escapeAttr(label)}">${escapeHtml(label)}</button>`;
   }).join('');
   box.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', () => {
     const lat = Number(btn.getAttribute('data-lat'));
     const lng = Number(btn.getAttribute('data-lng'));
     const label = btn.getAttribute('data-label') || '';
     setLeafletPickedPointV7(lat, lng, label);
     applyCoordsToPendingV7();
    });
   });
  }catch(e){
   window.showNotification?.('error', 'Search failed', e.message);
  }
 }
"""
        content = insert_before_once(content, " function parseCoords(str){", helper_block, "leaflet helper block")

    old_apply = """ function applyCoordsToPendingV7(){
 const type = document.getElementById('distancePinTypeV7')?.value || 'school';
 const coords = parseCoords(document.getElementById('distanceCoordsV7')?.value || '');
 const label = document.getElementById('distancePlaceLabelV7')?.value?.trim() || '';
 if (!coords) {
 return window.showNotification?.('error', 'Bad coordinates', 'Use format: latitude,longitude');
 }
 if (!window.__SNIPER_RUNTIME__.selectedSchool) window.__SNIPER_RUNTIME__.selectedSchool = null;
 if (!window.__SNIPER_RUNTIME__.selectedUniversity) window.__SNIPER_RUNTIME__.selectedUniversity = null;
 if (type === 'school') {
 window.__SNIPER_RUNTIME__.selectedSchool = { ...coords, label };
 } else {
 window.__SNIPER_RUNTIME__.selectedUniversity = { ...coords, label };
 }
 refreshDistanceReviewV7();
 renderSavedAndPendingV7();
 }"""
    new_apply = """ function applyCoordsToPendingV7(){
 const type = document.getElementById('distancePinTypeV7')?.value || 'school';
 const lat = Number(document.getElementById('distanceLatV7')?.value || '');
 const lng = Number(document.getElementById('distanceLngV7')?.value || '');
 const coords = (Number.isFinite(lat) && Number.isFinite(lng)) ? { lat, lng } : null;
 const label = document.getElementById('distancePlaceLabelV7')?.value?.trim() || '';
 if (!coords) {
  return window.showNotification?.('error', 'Location needed', 'Search and select a place on the map first.');
 }
 if (!window.__SNIPER_RUNTIME__.selectedSchool) window.__SNIPER_RUNTIME__.selectedSchool = null;
 if (!window.__SNIPER_RUNTIME__.selectedUniversity) window.__SNIPER_RUNTIME__.selectedUniversity = null;
 if (type === 'school') {
  window.__SNIPER_RUNTIME__.selectedSchool = { ...coords, label };
 } else {
  window.__SNIPER_RUNTIME__.selectedUniversity = { ...coords, label };
 }
 refreshDistanceReviewV7();
 if (typeof renderSavedAndPendingV7 === 'function') {
  renderSavedAndPendingV7();
 } else if (typeof renderGlobeV7 === 'function') {
  loadClassPathsGlobeV7();
 }
 }"""
    content = replace_if_present(content, old_apply, new_apply)

    old_save = """ async function saveFuturePathV7(){
 const studentName = document.getElementById('distanceStudentNameV7')?.value?.trim();
 const schoolPoint = window.__SNIPER_RUNTIME__.selectedSchool || null;
 const universityPoint = window.__SNIPER_RUNTIME__.selectedUniversity || null;
 if (!studentName) return window.showNotification?.('error', 'Name needed', 'Enter your name first.');
 if (!schoolPoint && !universityPoint) return window.showNotification?.('error', 'No pin selected', 'Open Google Maps, then enter coordinates and confirm them here.');
 try{
 const res = await fetch(apiUrl('/api/destinations/pin-submit'), {
 method:'POST',
 headers:{'Content-Type':'application/json'},
 body:JSON.stringify({ studentName, schoolPoint, universityPoint })
 });
 const data = await res.json();
 if (!data.success) return window.showNotification?.('error', 'Could not save', data.error || 'Save failed.');
 window.showNotification?.('success', 'Saved', 'Your future path is now on the class globe.');
 loadClassPathsGlobeV7();
 }catch(e){
 window.showNotification?.('error', 'Could not save', e.message);
 }
 }"""
    new_save = """ async function saveFuturePathV7(){
 const pinType = document.getElementById('distancePinTypeV7')?.value || 'school';
 const lat = Number(document.getElementById('distanceLatV7')?.value || '');
 const lng = Number(document.getElementById('distanceLngV7')?.value || '');
 const label = document.getElementById('distancePlaceLabelV7')?.value?.trim() || '';
 const section = document.getElementById('distanceSectionV7')?.value?.trim() || '';
 const studentName = document.getElementById('distanceStudentNameV7')?.value?.trim();
 if (Number.isFinite(lat) && Number.isFinite(lng)) {
  if (pinType === 'school') {
   window.__SNIPER_RUNTIME__.selectedSchool = { lat, lng, label };
  } else {
   window.__SNIPER_RUNTIME__.selectedUniversity = { lat, lng, label };
  }
 }
 refreshDistanceReviewV7();
 const schoolPoint = window.__SNIPER_RUNTIME__.selectedSchool || null;
 const universityPoint = window.__SNIPER_RUNTIME__.selectedUniversity || null;
 if (!studentName) return window.showNotification?.('error', 'Name needed', 'Select your name first.');
 if (!section) return window.showNotification?.('error', 'Section needed', 'Select your section first.');
 if (!schoolPoint && !universityPoint) return window.showNotification?.('error', 'No pin selected', 'Search and select a place first.');
 try{
  const res = await fetch(apiUrl('/api/destinations/pin-submit'), {
   method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({ studentName, section, schoolPoint, universityPoint })
  });
  const data = await res.json();
  if (!data.success) return window.showNotification?.('error', 'Could not save', data.error || 'Save failed.');
  window.showNotification?.('success', 'Saved', 'Your future path is now on the class globe.');
  loadClassPathsGlobeV7();
 }catch(e){
  window.showNotification?.('error', 'Could not save', e.message);
 }
 }"""
    content = replace_if_present(content, old_save, new_save)

    write_text(path, content)


def patch_server_js(path: Path) -> None:
    content = read_text(path)

    content = replace_if_present(
        content,
        "const compilationsPath = path.join(databaseDir, 'compilations.json');",
        "const compilationsPath = path.join(databaseDir, 'compilations.json');\nconst studentDirectoryPath = path.join(databaseDir, 'student_directory.json');",
    )

    content = replace_if_present(
        content,
        """ if (!fs.existsSync(compilationsPath)) {
 fs.writeFileSync(compilationsPath, JSON.stringify({ compilations: [], nextId: 1 }, null, 2));
 console.log(' Created compilations database');
 }
}""",
        """ if (!fs.existsSync(compilationsPath)) {
 fs.writeFileSync(compilationsPath, JSON.stringify({ compilations: [], nextId: 1 }, null, 2));
 console.log(' Created compilations database');
 }
 if (!fs.existsSync(studentDirectoryPath)) {
 fs.writeFileSync(studentDirectoryPath, JSON.stringify({ students: [] }, null, 2));
 console.log(' Created student directory database');
 }
}""",
    )

    content = replace_if_present(
        content,
        """function writeCompilations(data) {
 safeWriteJson(compilationsPath, data);
}""",
        """function writeCompilations(data) {
 safeWriteJson(compilationsPath, data);
}
function readStudentDirectory() {
 return safeReadJson(studentDirectoryPath, { students: [] });
}
function writeStudentDirectory(data) {
 safeWriteJson(studentDirectoryPath, data);
}""",
    )

    if "function getClientIp(req)" not in content:
        content = replace_if_present(
            content,
            """function nowIso() {
 return new Date().toISOString();
}""",
            """function nowIso() {
 return new Date().toISOString();
}
function getClientIp(req) {
 return String(req.headers['x-forwarded-for'] || req.socket.remoteAddress || '').split(',')[0].trim();
}
function isRateLimited(items, key, limit, windowMs) {
 const cutoff = Date.now() - windowMs;
 let count = 0;
 for (const item of items) {
  const ts = new Date(item.createdAt || item.created_at || 0).getTime();
  if (!Number.isFinite(ts) || ts < cutoff) continue;
  if (String(item.ip || '') === key) count++;
 }
 return count >= limit;
}""",
        )

    student_dir_block = """
app.get('/api/student-directory', (req, res) => {
 try {
  const db = readStudentDirectory();
  res.json({ success: true, students: db.students || [] });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.post('/api/admin/student-directory', (req, res) => {
 try {
  const auth = requireAdmin(req, res);
  if (!auth) return;
  if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });
  const students = Array.isArray(req.body?.students) ? req.body.students : [];
  const cleaned = students.map(s => ({
   name: String(s?.name || '').trim().substring(0, 80),
   section: String(s?.section || '').trim().substring(0, 20)
  })).filter(s => s.name && s.section);
  writeStudentDirectory({ students: cleaned });
  audit(auth.user.id, 'save-student-directory', { count: cleaned.length });
  res.json({ success: true, count: cleaned.length });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
"""
    content = insert_before_once(content, "// Settings save", student_dir_block, "student directory endpoints")

    content = replace_if_present(
        content,
        """ app.post('/api/paper-notes', (req, res) => {
 try {
 const text = String(req.body?.text || '').trim().substring(0, 400);
 if (!text) return res.status(400).json({ success: false, error: 'text required' });
 const db = readPaperNotes();
 const note = {
 id: db.nextId++,
 text,
 ip: req.headers['x-forwarded-for'] || req.socket.remoteAddress || '',
 createdAt: nowIso()
 };
 db.notes.push(note);
 if (db.notes.length > 3000) db.notes = db.notes.slice(-3000);
 writePaperNotes(db);
 sendWs('paper:note', { id: note.id });
 res.json({ success: true, noteId: note.id });
 } catch (e) {
 res.status(500).json({ success: false, error: e.message });
 }
 });""",
        """ app.post('/api/paper-notes', (req, res) => {
 try {
 const text = String(req.body?.text || '').trim().substring(0, 400);
 if (!text) return res.status(400).json({ success: false, error: 'text required' });
 if (containsProfanity(text)) return res.status(400).json({ success: false, error: 'Memory note rejected by profanity filter.' });
 const db = readPaperNotes();
 const ip = getClientIp(req);
 if (isRateLimited(db.notes || [], ip, 5, 60 * 1000)) {
  return res.status(429).json({ success: false, error: 'Rate limit exceeded. Maximum 5 notes per minute.' });
 }
 const note = {
  id: db.nextId++,
  text,
  ip,
  createdAt: nowIso()
 };
 db.notes.push(note);
 if (db.notes.length > 3000) db.notes = db.notes.slice(-3000);
 writePaperNotes(db);
 sendWs('paper:note', { id: note.id });
 res.json({ success: true, noteId: note.id });
 } catch (e) {
 res.status(500).json({ success: false, error: e.message });
 }
 });""",
    )

    content = replace_if_present(
        content,
        """ app.post('/api/paper-notes/from-memory', (req, res) => {
 try {
 const memoryId = Number(req.body?.memoryId);
 const dbMem = readDB();
 const memory = dbMem.memories.find(m => m.id === memoryId && m.approved === 1 && !m.deletedAt && !m.purgedAt);
 if (!memory) return res.status(404).json({ success: false, error: 'Memory not found' });
 const db = readPaperNotes();
 const ip = getClientIp(req);
 if (isRateLimited(db.notes || [], ip, 5, 60 * 1000)) {
 return res.status(429).json({ success: false, error: 'Rate limit exceeded. Maximum 5 notes per minute.' });
 }
 const note = {
 id: db.nextId++,
 memoryId,
 caption: String(memory.caption || '').substring(0, 400),
 text: String(memory.caption || '').substring(0, 400),
 ip,
 createdAt: nowIso()
 };
 db.notes.push(note);
 if (db.notes.length > 3000) db.notes = db.notes.slice(-3000);
 writePaperNotes(db);
 sendWs('paper:note', { note });
 res.json({ success: true, note });
 } catch (e) {
 res.status(500).json({ success: false, error: e.message });
 }
 });""",
        """ app.post('/api/paper-notes/from-memory', (req, res) => {
 try {
 const memoryId = Number(req.body?.memoryId);
 const dbMem = readDB();
 const memory = dbMem.memories.find(m => m.id === memoryId && m.approved === 1 && !m.deletedAt && !m.purgedAt);
 if (!memory) return res.status(404).json({ success: false, error: 'Memory not found' });
 const noteText = String(memory.caption || '').substring(0, 400);
 if (containsProfanity(noteText)) return res.status(400).json({ success: false, error: 'Memory note rejected by profanity filter.' });
 const db = readPaperNotes();
 const ip = getClientIp(req);
 if (isRateLimited(db.notes || [], ip, 5, 60 * 1000)) {
  return res.status(429).json({ success: false, error: 'Rate limit exceeded. Maximum 5 notes per minute.' });
 }
 const note = {
  id: db.nextId++,
  memoryId,
  caption: noteText,
  text: noteText,
  ip,
  createdAt: nowIso()
 };
 db.notes.push(note);
 if (db.notes.length > 3000) db.notes = db.notes.slice(-3000);
 writePaperNotes(db);
 sendWs('paper:note', { note });
 res.json({ success: true, note });
 } catch (e) {
 res.status(500).json({ success: false, error: e.message });
 }
 });""",
    )

    write_text(path, content)


def main() -> int:
    root = Path.cwd()
    index_path = root / INDEX_HTML
    server_path = root / SERVER_JS

    if not index_path.exists():
        raise FileNotFoundError(f"Missing {INDEX_HTML}")
    if not server_path.exists():
        raise FileNotFoundError(f"Missing {SERVER_JS}")

    patch_index_html(index_path)
    patch_server_js(server_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise