#!/usr/bin/env python3
"""
patch_farewell_sniper_v7.py

Final cleanup sniper patch.

Purpose:
- Cleanly stabilize multiplayer layer
- Expose runtime state/config globally
- Force one reliable websocket path
- Install one clean ghost cursor sender/receiver
- Install one clean shared memory-note sender/receiver
- Prevent duplicate popup behavior
- Make popup appear only after intro is gone and user scrolls past countdown
- Return page to top after intro
- Replace direct globe pin flow with Google Maps confirmation flow
- Add comprehensive music settings block in admin
- Keep changes append-only and safe

Run:
    python patch_farewell_sniper_v7.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


HTML_MARKER = "/* === SNIPER_PATCH_V7_START === */"
SERVER_MARKER = "// === SNIPER_SERVER_PATCH_V7_START ==="


INDEX_APPEND = r"""
<style>
/* === SNIPER_PATCH_V7_START === */
#distanceMapsFlowCard{
  max-width:980px;
  margin:0 auto 16px;
  padding:16px 18px;
  border-radius:20px;
  border:1px solid rgba(255,255,255,.12);
  background:rgba(255,255,255,.05);
  color:var(--text-muted);
  text-align:center;
}
#distanceMapsFlowCard strong{
  color:var(--text-light);
}
#distanceConfirmPanel{
  max-width:980px;
  margin:0 auto 16px;
  padding:18px;
  border-radius:20px;
  border:1px solid rgba(255,255,255,.12);
  background:rgba(8,12,20,.78);
  display:none;
}
#distanceConfirmPanel.active{
  display:block;
  animation:fadeInUp .5s ease;
}
#distanceConfirmPanel .row{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:12px;
}
#distanceConfirmPanel .row + .row{
  margin-top:12px;
}
#distanceConfirmPanel .hint{
  margin-top:10px;
  color:var(--text-muted);
  font-size:.9rem;
  text-align:center;
}
#distanceSelectedReview{
  display:grid;
  gap:8px;
  margin-top:10px;
}
.distance-review-pill{
  padding:10px 12px;
  border-radius:14px;
  background:rgba(255,255,255,.05);
  border:1px solid rgba(255,255,255,.10);
  color:#fff;
}
#distanceGlobeCanvas{
  cursor:grab;
}
#distanceGlobeCanvas.sniper-pick-armed{
  outline:2px solid rgba(212,175,55,.38);
  outline-offset:-2px;
}
#wsStatusBadge{
  position:fixed;
  left:50%;
  top:16px;
  transform:translateX(-50%);
  z-index:3500;
  padding:8px 12px;
  border-radius:999px;
  font-size:.82rem;
  border:1px solid rgba(255,255,255,.12);
  background:rgba(0,0,0,.45);
  color:#fff;
  backdrop-filter:blur(10px);
}
#wsStatusBadge.good{
  background:rgba(76,175,80,.18);
  border-color:rgba(76,175,80,.36);
}
#wsStatusBadge.bad{
  background:rgba(244,67,54,.18);
  border-color:rgba(244,67,54,.36);
}
@media (max-width: 900px){
  #distanceConfirmPanel .row{
    grid-template-columns:1fr;
  }
}
/* === /SNIPER_PATCH_V7_START === */
</style>

<script>
/* === SNIPER_PATCH_V7_START === */
(function(){
  if (window.__SNIPER_PATCH_V7__) return;
  window.__SNIPER_PATCH_V7__ = true;

  const SNIPER = {
    popupShown: false,
    wsConnected: false,
    wsReconnectTimer: null,
    wsSendThrottle: 0,
    ghostId: 'ghost_' + Math.random().toString(36).slice(2),
    ghosts: new Map(),
    notePoller: null,
    pendingMapMode: null,
    selectedSchool: null,
    selectedUniversity: null,
    lastIncomingNoteId: null
  };

  function boot(){
    exposeGlobals();
    cleanupOldPopupBehavior();
    patchIntroFlow();
    installWsBadge();
    installCleanMultiplayer();
    upgradeDistanceFlowToMaps();
    installAdminMusicPanelV7();
  }

  function exposeGlobals(){
    try { if (typeof state !== 'undefined') window.state = state; } catch(_){}
    try { if (typeof CONFIG !== 'undefined') window.CONFIG = CONFIG; } catch(_){}
    window.__SNIPER_RUNTIME__ = SNIPER;
  }

  function introVisible(){
    const overlay = document.getElementById('introVideoOverlay');
    if (!overlay) return false;
    const cs = getComputedStyle(overlay);
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    if (overlay.classList.contains('hidden')) return false;
    return true;
  }

  function cleanupOldPopupBehavior(){
    document.getElementById('ghostCursorPopup')?.classList.remove('active');
    document.getElementById('paperTutorial')?.classList.remove('active');

    const oldInstall = window.installScrollTriggeredPopups;
    window.installScrollTriggeredPopups = function(){
      if (window.__sniperCleanPopupInstalled) return;
      window.__sniperCleanPopupInstalled = true;

      const showAfterScroll = () => {
        if (SNIPER.popupShown) return;
        if (introVisible()) return;
        const countdown = document.getElementById('countdown');
        if (!countdown) return;
        const rect = countdown.getBoundingClientRect();
        if (rect.bottom >= window.innerHeight * 0.35) return;

        SNIPER.popupShown = true;
        setTimeout(() => {
          if (!introVisible()) document.getElementById('ghostCursorPopup')?.classList.add('active');
        }, 500);
        setTimeout(() => {
          if (!introVisible()) document.getElementById('paperTutorial')?.classList.add('active');
        }, 1700);
        window.removeEventListener('scroll', showAfterScroll);
      };

      window.addEventListener('scroll', showAfterScroll, { passive: true });
    };
    window.installScrollTriggeredPopups.__sniperClean = true;

    if (typeof oldInstall === 'function') {
      try {} catch(_){}
    }
  }

  function patchIntroFlow(){
    const oldSkip = window.skipIntro;
    if (typeof oldSkip === 'function' && !oldSkip.__sniperV7Wrapped){
      window.skipIntro = function(){
        const out = oldSkip.apply(this, arguments);
        setTimeout(() => {
          try {
            window.scrollTo({ top: 0, behavior: 'auto' });
            const home = document.getElementById('home');
            home?.scrollIntoView({ behavior: 'auto', block: 'start' });
            history.replaceState(null, '', '#home');
          } catch(_){}
        }, 550);
        setTimeout(() => {
          try { window.installScrollTriggeredPopups?.(); } catch(_){}
        }, 1200);
        return out;
      };
      window.skipIntro.__sniperV7Wrapped = true;
    }

    const video = document.getElementById('introVideo');
    if (video && !video.dataset.sniperV7Bound){
      video.dataset.sniperV7Bound = '1';
      video.addEventListener('ended', () => {
        setTimeout(() => {
          try {
            window.scrollTo({ top: 0, behavior: 'auto' });
            document.getElementById('home')?.scrollIntoView({ behavior: 'auto', block: 'start' });
            history.replaceState(null, '', '#home');
          } catch(_){}
        }, 500);
      });
    }
  }

  function installWsBadge(){
    if (document.getElementById('wsStatusBadge')) return;
    const badge = document.createElement('div');
    badge.id = 'wsStatusBadge';
    badge.className = 'bad';
    badge.textContent = 'Multiplayer: connecting...';
    document.body.appendChild(badge);
  }

  function setWsBadge(ok, text){
    const el = document.getElementById('wsStatusBadge');
    if (!el) return;
    el.classList.toggle('good', !!ok);
    el.classList.toggle('bad', !ok);
    el.textContent = text;
  }

  function installCleanMultiplayer(){
    const base = (window.CONFIG && window.CONFIG.API_BASE) ? window.CONFIG.API_BASE : null;
    if (!base) {
      setWsBadge(false, 'Multiplayer: no backend URL');
      return;
    }

    connectMultiplayerWS();
    installGhostTracking();
    installSharedNotes();
  }

  function connectMultiplayerWS(){
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
  }

  function sendWS(payload){
    const ws = window.__SNIPER_WS__;
    if (!ws || ws.readyState !== 1) return false;
    try {
      ws.send(JSON.stringify(payload));
      return true;
    } catch(_) {
      return false;
    }
  }

  function installGhostTracking(){
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
  }

  function getInitialsForGhost(){
    const saved = localStorage.getItem('ghostInitials');
    if (saved && saved.trim()) return saved.trim().slice(0, 3).toUpperCase();
    const n = localStorage.getItem('guestName') || '';
    const parts = n.trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return 'GS';
    return parts.slice(0, 2).map(x => x[0]).join('').toUpperCase();
  }

  function handleGhostMove(p){
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
  }

  function installSharedNotes(){
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
  }

  function handleIncomingNote(note){
    launchSharedPlane(note);
  }

  function launchSharedPlane(note){
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
  }

  function upgradeDistanceFlowToMaps(){
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
  }

  function parseCoords(str){
    const m = String(str || '').trim().match(/^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/);
    if (!m) return null;
    const lat = Number(m[1]);
    const lng = Number(m[2]);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
    return { lat, lng };
  }

  function applyCoordsToPendingV7(){
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
  }

  function refreshDistanceReviewV7(){
    const box = document.getElementById('distanceSelectedReview');
    if (!box) return;
    const s = window.__SNIPER_RUNTIME__.selectedSchool;
    const u = window.__SNIPER_RUNTIME__.selectedUniversity;

    box.innerHTML = `
      <div class="distance-review-pill">11th / 12th: ${s ? `${s.label || 'Selected'} (${s.lat.toFixed(4)}, ${s.lng.toFixed(4)})` : 'Not selected yet'}</div>
      <div class="distance-review-pill">University: ${u ? `${u.label || 'Selected'} (${u.lat.toFixed(4)}, ${u.lng.toFixed(4)})` : 'Not selected yet'}</div>
    `;
  }

  async function saveFuturePathV7(){
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
  }

  async function loadClassPathsGlobeV7(){
    try{
      const res = await fetch(apiUrl('/api/destinations/pin-submissions'));
      const data = await res.json();
      if (!data.success) return;
      renderGlobeV7(data.submissions || []);
    }catch(_){}
  }

  function renderGlobeV7(rows){
    const globe = window.__SNIPER_PATCH_V5__ ? window.__SNIPER_RUNTIME__?.v5GlobeRef || null : null;
    const runtime = window.__SNIPER_RUNTIME__;
    const g = (window.__SNIPER_PATCH_V5__ && window.__SNIPER_RUNTIME__ && window.__SNIPER_RUNTIME__.globeRef) || window.__sniperGlobeRef || null;

    const activeGlobe = g || window.__SNIPER_GLOBE__ || null;
    const schoolOrigin = { lat: 12.9716, lng: 77.5946, label: 'Cornerstone International School' };

    const points = [
      { ...schoolOrigin, color:'#ffd84d', radius:0.42, alt:0.065, label:schoolOrigin.label }
    ];
    const arcs = [];

    rows.forEach(r => {
      if (r.schoolPoint) {
        points.push({
          lat: r.schoolPoint.lat,
          lng: r.schoolPoint.lng,
          color: '#55b9ff',
          radius: 0.28,
          alt: 0.05,
          label: `${r.studentName} • 11th / 12th`
        });
        arcs.push({
          startLat: schoolOrigin.lat,
          startLng: schoolOrigin.lng,
          endLat: r.schoolPoint.lat,
          endLng: r.schoolPoint.lng,
          color: ['#55b9ff']
        });
      }
      if (r.universityPoint) {
        points.push({
          lat: r.universityPoint.lat,
          lng: r.universityPoint.lng,
          color: '#ff7aa8',
          radius: 0.28,
          alt: 0.05,
          label: `${r.studentName} • University`
        });
        arcs.push({
          startLat: schoolOrigin.lat,
          startLng: schoolOrigin.lng,
          endLat: r.universityPoint.lat,
          endLng: r.universityPoint.lng,
          color: ['#ff7aa8']
        });
      }
    });

    const s = runtime.selectedSchool;
    const u = runtime.selectedUniversity;
    if (s) points.push({ lat:s.lat, lng:s.lng, color:'#8be1ff', radius:0.33, alt:0.055, label:'Unsaved school point' });
    if (u) points.push({ lat:u.lat, lng:u.lng, color:'#ff9ebd', radius:0.33, alt:0.055, label:'Unsaved university point' });

    if (activeGlobe) {
      try {
        activeGlobe.pointsData(points);
        activeGlobe.arcsData(arcs);
      } catch(_){}
    }

    const stats = document.getElementById('distanceOverlayStats');
    if (stats) {
      const students = rows.length;
      const schoolPins = rows.filter(r => r.schoolPoint).length;
      const uniPins = rows.filter(r => r.universityPoint).length;
      stats.innerHTML = `
        <div class="distance-stat-pill">${students} students plotted</div>
        <div class="distance-stat-pill">${schoolPins} school paths</div>
        <div class="distance-stat-pill">${uniPins} university dreams</div>
      `;
    }
  }

  function installAdminMusicPanelV7(){
    const old = window.renderSettingsPanelHtml;
    if (typeof old !== 'function' || old.__sniperV7Wrapped) return;

    window.renderSettingsPanelHtml = function(){
      let html = old.apply(this, arguments);
      if (html.includes('sniperMusicAdminPanelV7')) return html;

      const inject = `
      <div id="sniperMusicAdminPanelV7" style="margin-top:16px; border:1px solid var(--glass-border); border-radius:16px; padding:14px; background:rgba(255,255,255,0.03);">
        <h4 style="font-family:var(--font-display); color:var(--primary-gold); margin-bottom:10px;">Comprehensive Music Settings</h4>
        <p class="mini-pill" style="margin-bottom:10px;">Use file names from the root <strong>music</strong> folder. Example: <strong>ambient.mp3</strong>.</p>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
          <div class="form-group"><label>Site Ambient Music</label><input class="form-input" id="setMusicAmbientSiteMusicV7" placeholder="ambient.mp3" /></div>
          <div class="form-group"><label>Lean Back Music</label><input class="form-input" id="setMusicLeanBackMusicV7" placeholder="leanback.mp3" /></div>
          <div class="form-group"><label>Last Bell Music</label><input class="form-input" id="setMusicLastBellMusicV7" placeholder="lastbell.mp3" /></div>
          <div class="form-group"><label>Globe Music</label><input class="form-input" id="setMusicGlobeMusicV7" placeholder="globe.mp3" /></div>
          <div class="form-group"><label>Ghost Cursor Popup Music</label><input class="form-input" id="setMusicGhostPopupMusicV7" placeholder="ghost.mp3" /></div>
          <div class="form-group"><label>Notes Popup Music</label><input class="form-input" id="setMusicNotesPopupMusicV7" placeholder="notes.mp3" /></div>
          <div class="form-group"><label>Boombox Graduation Vibes</label><input class="form-input" id="setMusicBoomboxGraduationVibesV7" placeholder="graduation.mp3" /></div>
          <div class="form-group"><label>Boombox Sad Boi Hours</label><input class="form-input" id="setMusicBoomboxSadBoiHoursV7" placeholder="sadboi.mp3" /></div>
          <div class="form-group"><label>Boombox Hype</label><input class="form-input" id="setMusicBoomboxHypeV7" placeholder="hype.mp3" /></div>
          <div class="form-group"><label>Locker Slam Sound</label><input class="form-input" id="setMusicLockerBangV7" placeholder="lockerbang.mp3" /></div>
        </div>
      </div>`;

      return html.replace('</div></div></div>', inject + '</div></div></div>');
    };
    window.renderSettingsPanelHtml.__sniperV7Wrapped = true;

    const oldRead = window.readSettingsFromEditor;
    if (typeof oldRead === 'function' && !oldRead.__sniperV7Wrapped){
      window.readSettingsFromEditor = function(){
        const s = oldRead.apply(this, arguments);
        s.music = Object.assign({}, s.music || {}, {
          ambientSiteMusic: document.getElementById('setMusicAmbientSiteMusicV7')?.value?.trim() || '',
          leanBackMusic: document.getElementById('setMusicLeanBackMusicV7')?.value?.trim() || '',
          lastBellMusic: document.getElementById('setMusicLastBellMusicV7')?.value?.trim() || '',
          globeMusic: document.getElementById('setMusicGlobeMusicV7')?.value?.trim() || '',
          ghostPopupMusic: document.getElementById('setMusicGhostPopupMusicV7')?.value?.trim() || '',
          notesPopupMusic: document.getElementById('setMusicNotesPopupMusicV7')?.value?.trim() || '',
          boomboxGraduationVibes: document.getElementById('setMusicBoomboxGraduationVibesV7')?.value?.trim() || '',
          boomboxSadBoiHours: document.getElementById('setMusicBoomboxSadBoiHoursV7')?.value?.trim() || '',
          boomboxHype: document.getElementById('setMusicBoomboxHypeV7')?.value?.trim() || '',
          lockerBangSound: document.getElementById('setMusicLockerBangV7')?.value?.trim() || ''
        });
        return s;
      };
      window.readSettingsFromEditor.__sniperV7Wrapped = true;
    }

    const oldSync = window.syncSettingsEditor;
    if (typeof oldSync === 'function' && !oldSync.__sniperV7Wrapped){
      window.syncSettingsEditor = function(){
        oldSync.apply(this, arguments);
        const music = (window.state?.settings?.music) || {};
        const put = (id, val) => {
          const el = document.getElementById(id);
          if (el) el.value = val || '';
        };
        put('setMusicAmbientSiteMusicV7', music.ambientSiteMusic);
        put('setMusicLeanBackMusicV7', music.leanBackMusic);
        put('setMusicLastBellMusicV7', music.lastBellMusic);
        put('setMusicGlobeMusicV7', music.globeMusic);
        put('setMusicGhostPopupMusicV7', music.ghostPopupMusic);
        put('setMusicNotesPopupMusicV7', music.notesPopupMusic);
        put('setMusicBoomboxGraduationVibesV7', music.boomboxGraduationVibes);
        put('setMusicBoomboxSadBoiHoursV7', music.boomboxSadBoiHours);
        put('setMusicBoomboxHypeV7', music.boomboxHype);
        put('setMusicLockerBangV7', music.lockerBangSound);
      };
      window.syncSettingsEditor.__sniperV7Wrapped = true;
    }
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
</script>
"""

SERVER_APPEND = r"""

// === SNIPER_SERVER_PATCH_V7_START ===
(() => {
  if (global.__SNIPER_SERVER_PATCH_V7__) return;
  global.__SNIPER_SERVER_PATCH_V7__ = true;

  const destinationsPathV7 = path.join(databaseDir, 'destinations.json');
  const paperNotesPathV7 = path.join(databaseDir, 'paper_notes.json');

  function readDestinationsV7() {
    return safeReadJson(destinationsPathV7, { destinations: [], submissions: [], nextId: 1 });
  }
  function writeDestinationsV7(data) {
    safeWriteJson(destinationsPathV7, data);
  }
  function readPaperNotesV7() {
    return safeReadJson(paperNotesPathV7, { notes: [], nextId: 1 });
  }

  app.get('/api/sniper/runtime', (req, res) => {
    res.json({ success: true, ws: true, multiplayer: true });
  });

  app.get('/api/destinations/pin-submissions', (req, res) => {
    try {
      const db = readDestinationsV7();
      res.json({ success: true, submissions: db.submissions || [] });
    } catch (e) {
      res.status(500).json({ success: false, error: e.message });
    }
  });

  wss.on('connection', (ws) => {
    ws.on('message', raw => {
      let data = null;
      try { data = JSON.parse(String(raw)); } catch (_) { return; }
      if (!data || typeof data !== 'object') return;

      if (data.type === 'ghost:move') {
        broadcast('ghost:move', {
          id: String(data.id || '').slice(0, 64),
          x: Number(data.x || 0),
          y: Number(data.y || 0),
          initials: String(data.initials || 'GS').slice(0, 4)
        });
      }

      if (data.type === 'paper:note:broadcast' && data.note) {
        broadcast('paper:note', { note: data.note });
      }
    });
  });

  console.log('SNIPER patch server v7 loaded.');
})();
"""


def find_repo_root(start: Path) -> Path:
    for base in [start] + list(start.parents):
        if (base / "index.html").exists() and (base / "server.js").exists():
            return base
    return start


def backup(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".bak_sniper_v7")
    if not bak.exists():
        shutil.copy2(path, bak)


def patch_html(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    if HTML_MARKER in text:
        return False
    if "</body>" not in text:
        raise RuntimeError("index.html missing </body>")
    new_text = text.replace("</body>", INDEX_APPEND + "\n</body>")
    backup(path)
    path.write_text(new_text, encoding="utf-8", newline="\n")
    return True


def patch_server(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    if SERVER_MARKER in text:
        return False
    pos = text.rfind("server.listen(")
    if pos == -1:
        raise RuntimeError("server.js missing server.listen")
    new_text = text[:pos] + SERVER_APPEND + "\n\n" + text[pos:]
    backup(path)
    path.write_text(new_text, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    root = find_repo_root(Path.cwd())
    index_html = root / "index.html"
    server_js = root / "server.js"

    if not index_html.exists():
        print("ERROR: index.html not found", file=sys.stderr)
        return 1
    if not server_js.exists():
        print("ERROR: server.js not found", file=sys.stderr)
        return 1

    changed = []
    try:
        if patch_html(index_html):
            changed.append("index.html")
        if patch_server(server_js):
            changed.append("server.js")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if changed:
        print("Patched:", ", ".join(changed))
    else:
        print("Already patched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())