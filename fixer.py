#!/usr/bin/env python3
"""
Farewell website patcher (frontend hotfix pack)

This script patches the attached codebase in-place to address the reported issues:
- Admin compilations broken due to global scoping mismatches
- Fun Features admin settings not loading (schema mismatch) + mood counts missing
- Destinations admin approvals complaining "no admin token found"
- "Watch as Movie" says no approved images (window.state not set + no public memory cache)
- Upload drag/drop 400: adds multi-field fallback upload attempts
- Tutorial button missing + auto tutorial on first visit
- Navbar missing routes (adds Destinations + Fun Features)
- Timeline shows old data (re-renders from state.settings.timeline on settingsUpdated)
- Removes the stray "Get professional email..." garbage snippet accidentally embedded in HTML
- Hardens localStorage arrays to prevent "cannot read properties of null reading push" issues

Safe to run multiple times (idempotent).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


PATCH_MARKER_START = "<!-- FAREWELL_PATCH_V1_START -->"
PATCH_MARKER_END = "<!-- FAREWELL_PATCH_V1_END -->"


PATCH_JS = r"""
<!-- FAREWELL_PATCH_V1_START -->
<script id="farewellPatchV1">
(function () {
  'use strict';
  if (window.__farewellPatchV1Applied) return;
  window.__farewellPatchV1Applied = true;

  // ---------- Helpers ----------
  function escHtml(s){
    try { if (typeof escapeHtml === 'function') return escapeHtml(s); } catch (_) {}
    const d = document.createElement('div'); d.textContent = String(s ?? ''); return d.innerHTML;
  }
  function getAdminTokenSafe(){
    try {
      return (typeof state !== 'undefined' && state && state.adminToken) || localStorage.getItem('adminToken') || '';
    } catch (_) { return ''; }
  }
  window.getAdminToken = getAdminTokenSafe;

  function ensureArrayKey(key){
    try {
      const raw = localStorage.getItem(key);
      if (!raw) { localStorage.setItem(key, '[]'); return; }
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) localStorage.setItem(key, '[]');
    } catch (_) {
      try { localStorage.setItem(key, '[]'); } catch (_) {}
    }
  }

  // Prevent "cannot read properties of null ... push/includes" from bad localStorage values
  ['likedMemories', 'adviceLiked'].forEach(ensureArrayKey);

  // Make the lexical `state` accessible as `window.state` (many fragments use window.state?.*)
  try {
    if (typeof state !== 'undefined' && state && !window.state) window.state = state;
  } catch (_) {}

  // Ensure state.adminToken is hydrated from localStorage as a fallback
  try {
    if (typeof state !== 'undefined' && state && !state.adminToken) {
      const t = localStorage.getItem('adminToken');
      if (t) state.adminToken = t;
    }
  } catch (_) {}

  // ---------- Patch: dispatch settingsUpdated after loadSettings ----------
  (function patchLoadSettings(){
    if (typeof window.loadSettings !== 'function') return;
    if (window.__farewellPatchedLoadSettings) return;
    window.__farewellPatchedLoadSettings = true;

    const _orig = window.loadSettings;
    window.loadSettings = async function(){
      const out = await _orig.apply(this, arguments);
      try { if (typeof state !== 'undefined' && state) window.state = state; } catch (_) {}
      try { window.dispatchEvent(new Event('settingsUpdated')); } catch (_) {}
      try { if (typeof window.updateUploadStatusCallout === 'function') window.updateUploadStatusCallout(); } catch (_) {}
      return out;
    };
  })();

  // ---------- Patch: Tutorial FAB + auto-run first visit ----------
  function ensureTutorialFab(){
    if (document.getElementById('tutorialFab')) return;
    const btn = document.createElement('button');
    btn.id = 'tutorialFab';
    btn.className = 'feature-tour-fab';
    btn.textContent = 'Tutorial';
    // keep it above boombox dock (which sits bottom-right)
    btn.style.right = '18px';
    btn.style.bottom = '92px';
    btn.style.zIndex = '2601';
    btn.onclick = function(){
      if (typeof window.startTutorial === 'function') window.startTutorial();
      else if (typeof window.showNotification === 'function') window.showNotification('info','Tutorial','Tutorial system not available on this build.');
    };
    document.body.appendChild(btn);
  }

  function autoStartTutorialOnce(){
    const key = 'farewell_tutorial_seen_v1';
    try {
      if (localStorage.getItem(key)) return;
      if (typeof window.startTutorial !== 'function') return;
      localStorage.setItem(key, '1');
      // delay so layout + fonts settle
      setTimeout(() => { try { window.startTutorial(); } catch (_) {} }, 900);
    } catch (_) {}
  }

  // ---------- Patch: Navbar routes (add missing anchors) ----------
  function ensureNavLink(href, label){
    const nav = document.getElementById('navLinks');
    if (!nav) return;
    if (nav.querySelector(`a[href="${href}"]`)) return;
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = href;
    a.textContent = label;
    li.appendChild(a);
    const ctaLi = nav.querySelector('a.nav-cta')?.closest('li');
    if (ctaLi) nav.insertBefore(li, ctaLi);
    else nav.appendChild(li);
  }
  function ensureNavbarRoutes(){
    ensureNavLink('#distanceMapSection', 'Destinations');
    ensureNavLink('#gratitudeWall', 'Fun Features');
  }

  // ---------- Patch: Upload input visibility hack (Safari/iOS reliability) ----------
  function injectFileInputVisibilityHack(){
    if (document.getElementById('fileInputHackStyle')) return;
    const st = document.createElement('style');
    st.id = 'fileInputHackStyle';
    st.textContent = `
      /* Avoid display:none on file inputs (iOS Safari can block programmatic click) */
      #file-input, #batchFiles {
        position: absolute !important;
        left: -9999px !important;
        width: 1px !important;
        height: 1px !important;
        opacity: 0 !important;
        display: block !important;
      }
    `;
    document.head.appendChild(st);
  }

  // ---------- Patch: Ensure upload bindings (in case init order raced settings) ----------
  function ensureUploadBindings(){
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    if (!dropzone || !fileInput) return;

    // Keyboard accessibility + reliability
    dropzone.setAttribute('role', 'button');
    dropzone.setAttribute('tabindex', '0');

    if (!dropzone.dataset.farewellBound) {
      dropzone.dataset.farewellBound = '1';

      dropzone.addEventListener('click', (e) => {
        // only trigger if uploads are enabled (if admin disabled uploads, keep it blocked)
        try {
          if (typeof state !== 'undefined' && state?.settings && state.settings.uploadsEnabled === false) return;
        } catch (_) {}
        e.preventDefault();
        try { fileInput.click(); } catch (_) {}
      });

      dropzone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          try { fileInput.click(); } catch (_) {}
        }
      });
    }
  }

  // ---------- Public Memories Cache (for Watch as Movie + Compilations thumbnails) ----------
  const publicMemCache = {
    items: [],
    loaded: false,
    loadingPromise: null,
    lastLoadedAt: 0
  };

  async function loadPublicMemories(force){
    const now = Date.now();
    if (!force && publicMemCache.loaded && (now - publicMemCache.lastLoadedAt) < 60_000) {
      // keep reasonably fresh
      return publicMemCache.items;
    }
    if (publicMemCache.loadingPromise) return publicMemCache.loadingPromise;

    publicMemCache.loadingPromise = (async () => {
      let all = [];
      let page = 1;
      const limit = 200;
      let hasMore = true;

      while (hasMore) {
        const params = new URLSearchParams({ page: String(page), limit: String(limit) });
        const url = apiUrl(`/api/memories?${params.toString()}`);
        const res = await fetch(url, { cache: 'no-store' });
        const data = await res.json().catch(() => ({}));

        if (!data || !data.success) break;
        const batch = Array.isArray(data.memories) ? data.memories : [];
        // Normalize media URLs
        const normalized = batch.map(m => {
          const u = m?.file_url;
          return Object.assign({}, m, { file_url: (typeof mediaUrl === 'function' ? mediaUrl(u) : u) });
        });

        all = all.concat(normalized);

        const hm = (data.hasMore === true) || (batch.length === limit);
        hasMore = !!hm;
        page += 1;

        // Safety stop to avoid infinite loops on buggy APIs
        if (page > 200) break;
        if (!batch.length) break;
      }

      publicMemCache.items = all;
      publicMemCache.loaded = true;
      publicMemCache.lastLoadedAt = Date.now();
      publicMemCache.loadingPromise = null;

      // Update state caches for other fragments (compilations + boombox)
      try {
        if (typeof state !== 'undefined' && state) {
          state.memories = all;
          window.state = state;
        }
      } catch (_) {}

      return all;
    })();

    try { return await publicMemCache.loadingPromise; }
    finally { /* promise cleared in loader */ }
  }

  window.__farewellLoadPublicMemories = loadPublicMemories;

  // ---------- Patch: Watch as Movie ----------
  (function patchLeanBack(){
    if (typeof window.startLeanBackMode !== 'function') return;
    if (window.__farewellPatchedLeanBack) return;
    window.__farewellPatchedLeanBack = true;

    const _orig = window.startLeanBackMode;
    window.startLeanBackMode = async function(){
      try {
        await loadPublicMemories(false);
      } catch (e) {
        console.warn('[Patch] Failed to pre-load public memories for LeanBack:', e);
      }
      // Ensure window.state exists for the original function
      try { if (typeof state !== 'undefined' && state) window.state = state; } catch (_) {}
      return _orig.apply(this, arguments);
    };
  })();

  // ---------- Patch: Compilations playback (ensure memory cache is present) ----------
  (function patchPlayCompilation(){
    if (typeof window.playCompilation !== 'function') return;
    if (window.__farewellPatchedPlayCompilation) return;
    window.__farewellPatchedPlayCompilation = true;

    const _orig = window.playCompilation;
    window.playCompilation = async function(){
      try { await loadPublicMemories(false); } catch (_) {}
      try { if (typeof state !== 'undefined' && state) window.state = state; } catch (_) {}
      return _orig.apply(this, arguments);
    };
  })();

  // ---------- Patch: Compilations admin scoping (bridge lexical lets to window.*) ----------
  (function bridgeCompilationGlobals(){
    function bridge(name){
      try {
        // If lexical binding exists (declared with let in earlier script), expose via window getter/setter.
        // Accessing an undeclared identifier throws ReferenceError, so we use eval safely.
        const exists = (function(){ try { return typeof eval(name) !== 'undefined'; } catch(_) { return false; } })();
        if (!exists) return;
        if (Object.getOwnPropertyDescriptor(window, name)) return;

        Object.defineProperty(window, name, {
          configurable: true,
          enumerable: false,
          get: function(){ try { return eval(name); } catch(_) { return undefined; } },
          set: function(v){ try { eval(name + " = v"); } catch(_) {} }
        });
      } catch(_) {}
    }
    // Variables from the compilations fragment
    bridge('compSelectedSlides');
    bridge('compEditingId');
    bridge('compAvailableMemories');
  })();

  // ---------- Patch: Upload fallback (400) with alternate field names ----------
  (function patchUploadSubmit(){
    if (typeof window.submitUpload !== 'function') return;
    if (window.__farewellPatchedSubmitUpload) return;
    window.__farewellPatchedSubmitUpload = true;

    const _orig = window.submitUpload;

    function buildFD(mode, studentName, caption, memoryType){
      const fd = new FormData();

      // Always include multiple aliases for text fields (backends differ)
      fd.append('name', studentName);
      fd.append('studentName', studentName);
      fd.append('student_name', studentName);

      fd.append('caption', caption);

      fd.append('type', memoryType);
      fd.append('memoryType', memoryType);
      fd.append('memory_type', memoryType);

      // Files: try different conventions by attempt (avoid duplicates)
      if (mode === 'files') {
        selectedFiles.forEach(f => fd.append('files', f));
      } else if (mode === 'files[]') {
        selectedFiles.forEach(f => fd.append('files[]', f));
      } else { // 'file'
        // Some backends only support a single file field name but accept multiple occurrences.
        selectedFiles.forEach(f => fd.append('file', f));
      }
      return fd;
    }

    function xhrSend(fd, onProgress){
      return new Promise((resolve) => {
        const xhr = new XMLHttpRequest();
        xhr.upload.addEventListener('progress', (e) => {
          if (!onProgress) return;
          if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
        });
        xhr.addEventListener('load', () => {
          let json = null;
          try { json = JSON.parse(xhr.responseText); } catch (_) {}
          resolve({ status: xhr.status, json, text: xhr.responseText });
        });
        xhr.addEventListener('error', () => resolve({ status: 0, json: null, text: '' }));
        xhr.open('POST', apiUrl('/api/upload'), true);
        xhr.send(fd);
      });
    }

    window.submitUpload = async function(){
      try {
        // If upload module isn't present, fall back to original
        if (typeof selectedFiles === 'undefined' || !Array.isArray(selectedFiles)) {
          return _orig.apply(this, arguments);
        }

        const studentName = document.getElementById('studentName')?.value?.trim();
        const caption = document.getElementById('caption')?.value?.trim();
        const memoryType = document.getElementById('memoryType')?.value;

        if (!studentName) { showNotification('error','Name required','Please enter your name'); return; }
        if (!caption) { showNotification('error','Caption required','Please add a description'); return; }
        if (!memoryType) { showNotification('error','Category required','Please select a category'); return; }
        if (selectedFiles.length === 0) { showNotification('error','No files','Please select at least one file'); return; }

        // Respect upload window if configured
        try {
          const settings = (typeof state !== 'undefined' && state?.settings) ? state.settings : (window.state?.settings || {});
          if (settings?.uploadWindowEnabled && typeof parseISTLocalToDate === 'function') {
            const now = new Date();
            const start = parseISTLocalToDate(settings.uploadWindowStartIST);
            const end = parseISTLocalToDate(settings.uploadWindowEndIST);
            if (start && now < start) { showNotification('error','Too early','Upload window has not started yet'); return; }
            if (end && now > end) { showNotification('error','Too late','Upload window has closed'); return; }
          }
        } catch (_) {}

        // UI elements
        const uploadForm = document.getElementById('uploadForm');
        const uploadProgress = document.getElementById('uploadProgress');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');

        if (uploadForm) uploadForm.style.display = 'none';
        if (uploadProgress) uploadProgress.classList.add('active');

        const attempts = ['files', 'files[]', 'file'];
        let lastErr = null;

        for (let i = 0; i < attempts.length; i++) {
          const mode = attempts[i];
          if (progressText) progressText.textContent = `Uploading... (mode: ${mode}) 0%`;
          if (progressFill) progressFill.style.width = '0%';

          const fd = buildFD(mode, studentName, caption, memoryType);

          const resp = await xhrSend(fd, (pct) => {
            if (progressFill) progressFill.style.width = pct + '%';
            if (progressText) progressText.textContent = `Uploading... (mode: ${mode}) ${pct}%`;
          });

          const ok = resp.status === 200 && resp.json && resp.json.success;
          if (ok) {
            if (uploadProgress) uploadProgress.classList.remove('active');
            try { if (typeof showUploadSuccess === 'function') showUploadSuccess(); } catch (_) {}
            try { if (typeof triggerConfetti === 'function') triggerConfetti(); } catch (_) {}
            return;
          }

          // Retry only on 400/422-like "bad request" or empty response; otherwise stop
          const errMsg = resp.json?.error || (resp.status ? ('Server error: ' + resp.status) : 'Network error');
          lastErr = errMsg;

          const retryable = (resp.status === 400 || resp.status === 422 || resp.status === 0);
          if (!retryable) break;
        }

        if (uploadProgress) uploadProgress.classList.remove('active');
        if (uploadForm) uploadForm.style.display = 'block';
        showNotification('error','Upload failed', lastErr || 'Upload failed. Please try again.');
      } catch (e) {
        console.error('[Patch] submitUpload error:', e);
        try {
          document.getElementById('uploadProgress')?.classList.remove('active');
          document.getElementById('uploadForm') && (document.getElementById('uploadForm').style.display = 'block');
        } catch (_) {}
        showNotification('error','Upload failed', e.message || 'Unknown error');
      }
    };
  })();

  // ---------- Patch: Admin Fun Features settings schema + mood counts ----------
  (function patchAdminFunFeatures(){
    if (typeof window.initFunfeaturesPanelContent !== 'function') return;
    if (window.__farewellPatchedFunFeaturesAdmin) return;
    window.__farewellPatchedFunFeaturesAdmin = true;

    // Ensure ffSettings exists even if the original script isn't loaded yet
    try { if (typeof ffSettings === 'undefined') window.ffSettings = { enabled: {} }; } catch (_) {}

    const DEFAULTS = {
      gratitudeWall: true,
      superlatives: true,
      wishJar: true,
      songDedications: true,
      moodBoard: true,
      timeCapsule: true,
      seniorAdvice: true,
      memoryMosaic: false
    };

    // Override: loadFunFeatureSettings to support both {settings:{...}} and {settings:{enabled:{...}}} and old {enabled:{...}}
    window.loadFunFeatureSettings = async function(){
      try {
        const res = await fetch(apiUrl('/api/fun/settings'), { cache: 'no-store' });
        const data = await res.json().catch(() => ({}));

        let incoming = data?.settings ?? data?.enabled ?? {};
        if (incoming && typeof incoming === 'object' && incoming.enabled && typeof incoming.enabled === 'object') {
          incoming = incoming.enabled;
        }

        // ffSettings is a lexical global in the original admin funfeatures script; write to it if present.
        try {
          ffSettings.enabled = Object.assign({}, DEFAULTS, incoming || {});
        } catch (_) {
          window.ffSettings = window.ffSettings || {};
          window.ffSettings.enabled = Object.assign({}, DEFAULTS, incoming || {});
        }

        if (typeof window.renderFunFeatureToggles === 'function') window.renderFunFeatureToggles();
      } catch (e) {
        try {
          ffSettings.enabled = Object.assign({}, DEFAULTS);
        } catch (_) {
          window.ffSettings = window.ffSettings || {};
          window.ffSettings.enabled = Object.assign({}, DEFAULTS);
        }
        if (typeof window.renderFunFeatureToggles === 'function') window.renderFunFeatureToggles();
      }
    };

    // Override: renderFunFeatureToggles with correct keys used by the public site
    window.renderFunFeatureToggles = function(){
      const container = document.getElementById('ffTogglesContainer');
      if (!container) return;

      let enabledObj = {};
      try { enabledObj = ffSettings.enabled || {}; } catch (_) { enabledObj = (window.ffSettings?.enabled || {}); }

      const features = [
        { key: 'gratitudeWall', label: 'Gratitude Wall', desc: 'Students can post sticky notes of thanks' },
        { key: 'superlatives', label: 'Superlatives', desc: 'Nominate & vote for class awards' },
        { key: 'wishJar', label: 'Wish Jar', desc: 'Drop wishes, hopes, and advice' },
        { key: 'songDedications', label: 'Song Dedications', desc: 'Dedicate songs to friends/class' },
        { key: 'moodBoard', label: 'Mood Board', desc: 'Vibe check votes (editable by users)' },
        { key: 'timeCapsule', label: 'Time Capsule', desc: 'Letters to the future' },
        { key: 'seniorAdvice', label: 'Senior Advice', desc: 'Advice wall section' },
        { key: 'memoryMosaic', label: 'Memory Mosaic', desc: 'Contributor mosaic leaderboard' }
      ];

      container.innerHTML = features.map(f => {
        const on = enabledObj[f.key] !== false;
        return `
          <div class="ff-toggle-row">
            <div>
              <div class="ff-toggle-label">${escHtml(f.label)}</div>
              <div style="font-size:0.8rem; color:var(--text-muted);">${escHtml(f.desc)}</div>
            </div>
            <label class="ff-toggle">
              <input type="checkbox" id="ffToggle_${f.key}" ${on ? 'checked' : ''} onchange="onFunFeatureToggle('${f.key}', this.checked)">
              <span class="ff-toggle-slider"></span>
            </label>
          </div>
        `;
      }).join('');
    };

    window.onFunFeatureToggle = function(key, enabled){
      try {
        ffSettings.enabled = ffSettings.enabled || {};
        ffSettings.enabled[key] = !!enabled;
      } catch (_) {
        window.ffSettings = window.ffSettings || {};
        window.ffSettings.enabled = window.ffSettings.enabled || {};
        window.ffSettings.enabled[key] = !!enabled;
      }
    };

    // Override: saveFunFeatureSettings to send schema compatible with both variants
    window.saveFunFeatureSettings = async function(){
      const tok = getAdminTokenSafe();
      if (!tok) return showNotification('error','Login required','Admin token not found. Please log in again.');
      let enabledObj = {};
      try { enabledObj = ffSettings.enabled || {}; } catch (_) { enabledObj = (window.ffSettings?.enabled || {}); }

      try {
        const res = await fetch(apiUrl('/api/fun/settings'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + tok
          },
          body: JSON.stringify({ settings: enabledObj, enabled: enabledObj })
        });
        const data = await res.json().catch(() => ({}));
        if (data.success) {
          showNotification('success','Saved','Fun feature settings updated.');
          try { window.dispatchEvent(new Event('settingsUpdated')); } catch (_) {}
        } else {
          showNotification('error','Failed', data.error || 'Failed to save fun feature settings.');
        }
      } catch (e) {
        showNotification('error','Error', e.message || 'Network error');
      }
    };

    // Patch mood loader: if backend doesn't return counts, compute from votes
    if (typeof window.loadFunFeatureMood === 'function') {
      const _origMood = window.loadFunFeatureMood;
      window.loadFunFeatureMood = async function(){
        await _origMood.apply(this, arguments);
        try {
          // If counts missing, compute
          if (typeof ffData !== 'undefined' && ffData?.mood && Array.isArray(ffData.mood.votes)) {
            const counts = {};
            ffData.mood.votes.forEach(v => {
              const k = String(v.mood || '').trim();
              if (!k) return;
              counts[k] = (counts[k] || 0) + 1;
            });
            if (!ffData.mood.counts || !Object.keys(ffData.mood.counts).length) ffData.mood.counts = counts;
            if (typeof window.renderFunFeatureMood === 'function') window.renderFunFeatureMood();
          }
        } catch (_) {}
      };
    }

    // Patch gratitude/wishes/dedications renderers to handle alternate field names
    if (typeof window.renderFunFeatureGratitude === 'function') {
      window.renderFunFeatureGratitude = function(){
        const list = document.getElementById('ffGratitudeList');
        const count = document.getElementById('ffGratitudeCount');
        if (!list) return;
        const arr = (typeof ffData !== 'undefined' && Array.isArray(ffData.gratitude)) ? ffData.gratitude : [];
        if (count) count.textContent = arr.length;
        if (!arr.length) { list.innerHTML = '<div class="ff-empty">No gratitude notes yet.</div>'; return; }
        list.innerHTML = arr.map(e => {
          const from = e.from || e.from_name || e.fromName || 'Anonymous';
          const to = e.to || e.to_name || e.toName || 'Everyone';
          const msg = e.message || e.msg || e.text || '';
          return `
            <div class="ff-admin-item">
              <div class="ff-admin-item-content">
                <div><strong>${escHtml(from)}</strong> → <strong>${escHtml(to)}</strong></div>
                <div style="color:var(--text-light); margin-top:6px;">"${escHtml(msg)}"</div>
                <div class="ff-admin-item-meta">${typeof timeAgo==='function' ? timeAgo(e.createdAt) : ''}</div>
              </div>
              <div class="ff-admin-item-actions">
                <button class="admin-btn admin-btn-danger" style="padding:6px 12px; font-size:0.8rem;" onclick="deleteFunFeatureItem('gratitude', ${e.id})">Delete</button>
              </div>
            </div>
          `;
        }).join('');
      };
    }

    if (typeof window.renderFunFeatureWishes === 'function') {
      window.renderFunFeatureWishes = function(){
        const list = document.getElementById('ffWishesList');
        const count = document.getElementById('ffWishesCount');
        if (!list) return;
        const arr = (typeof ffData !== 'undefined' && Array.isArray(ffData.wishes)) ? ffData.wishes : [];
        if (count) count.textContent = arr.length;
        if (!arr.length) { list.innerHTML = '<div class="ff-empty">No wishes yet.</div>'; return; }
        list.innerHTML = arr.map(e => `
          <div class="ff-admin-item">
            <div class="ff-admin-item-content">
              <div><strong>${escHtml(e.name || 'Anonymous')}</strong> <span class="mini-pill" style="margin-left:8px;">${escHtml(e.category || 'General')}</span></div>
              <div style="color:var(--text-light); margin-top:6px;">"${escHtml(e.text || e.message || '')}"</div>
              <div class="ff-admin-item-meta">${typeof timeAgo==='function' ? timeAgo(e.createdAt) : ''}</div>
            </div>
            <div class="ff-admin-item-actions">
              <button class="admin-btn admin-btn-danger" style="padding:6px 12px; font-size:0.8rem;" onclick="deleteFunFeatureItem('wishes', ${e.id})">Delete</button>
            </div>
          </div>
        `).join('');
      };
    }

    if (typeof window.renderFunFeatureDedications === 'function') {
      window.renderFunFeatureDedications = function(){
        const list = document.getElementById('ffDedicationsList');
        const count = document.getElementById('ffDedicationsCount');
        if (!list) return;
        const arr = (typeof ffData !== 'undefined' && Array.isArray(ffData.dedications)) ? ffData.dedications : [];
        if (count) count.textContent = arr.length;
        if (!arr.length) { list.innerHTML = '<div class="ff-empty">No dedications yet.</div>'; return; }
        list.innerHTML = arr.map(e => `
          <div class="ff-admin-item">
            <div class="ff-admin-item-content">
              <div><strong>${escHtml(e.from || '')}</strong> → <strong>${escHtml(e.to || '')}</strong></div>
              <div style="color:var(--primary-gold); margin-top:6px;">${escHtml(e.song || '')}</div>
              ${(e.message ? `<div style="color:var(--text-muted); margin-top:4px; font-style:italic;">"${escHtml(e.message)}"</div>` : '')}
              <div class="ff-admin-item-meta">${typeof timeAgo==='function' ? timeAgo(e.createdAt) : ''}</div>
            </div>
            <div class="ff-admin-item-actions">
              <button class="admin-btn admin-btn-danger" style="padding:6px 12px; font-size:0.8rem;" onclick="deleteFunFeatureItem('dedications', ${e.id})">Delete</button>
            </div>
          </div>
        `).join('');
      };
    }
  })();

  // ---------- Patch: Admin Destinations token fallback + approved endpoint fallback ----------
  (function patchAdminDestinations(){
    if (typeof window.initDestinationsPanelContent !== 'function') return;
    if (window.__farewellPatchedDestinationsAdmin) return;
    window.__farewellPatchedDestinationsAdmin = true;

    // Wrap loader to try /api/destinations/list first, then fallback to /api/destinations
    if (typeof window.loadDestinationsData === 'function') {
      const _orig = window.loadDestinationsData;
      window.loadDestinationsData = async function(){
        try {
          // Try to force correct approved endpoint if existing code used wrong one
          if (typeof destData !== 'undefined') {
            // no-op, just ensure binding exists
          }
        } catch (_) {}

        // Attempt original; if it errors, try fallback strategy silently
        try {
          return await _orig.apply(this, arguments);
        } catch (e) {
          console.warn('[Patch] loadDestinationsData original failed, trying fallback:', e);
        }

        try {
          // Manual fallback
          const approvedTry = async (path) => {
            const r = await fetch(apiUrl(path), { cache: 'no-store' });
            const j = await r.json().catch(() => ({}));
            return j?.success ? (j.destinations || j.submissions || j.data || []) : [];
          };
          const pendingTry = async () => {
            const r = await fetch(apiUrl('/api/destinations/pin-submissions'), { cache: 'no-store' });
            const j = await r.json().catch(() => ({}));
            return j?.success ? (j.submissions || []) : [];
          };
          const approved = await approvedTry('/api/destinations/list');
          const pending = await pendingTry();
          try { destData.approved = approved; destData.pending = pending; } catch (_) {}
          if (typeof renderDestinations === 'function') renderDestinations();
        } catch (e2) {
          console.warn('[Patch] loadDestinationsData fallback failed:', e2);
        }
      };
    }

    // Override approve/delete to always use localStorage token as fallback
    async function postAdminDestAction(payload){
      const tok = getAdminTokenSafe();
      if (!tok) {
        showNotification('error','Not logged in','Admin token not found. Please log in again.');
        throw new Error('No admin token');
      }
      const res = await fetch(apiUrl('/api/admin/destinations'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + tok },
        body: JSON.stringify(payload)
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || ('HTTP ' + res.status));
      if (!data.success) throw new Error(data.error || 'Action failed');
      return data;
    }

    window.approveDestination = async function(id){
      try {
        await postAdminDestAction({ action: 'approve', id });
        showNotification('success','Approved','Destination approved.');
        if (typeof loadDestinationsData === 'function') loadDestinationsData();
      } catch (e) {
        showNotification('error','Error', e.message || 'Approve failed');
      }
    };

    window.approveAllDestinations = async function(){
      try {
        const pending = (typeof destData !== 'undefined' && Array.isArray(destData.pending)) ? destData.pending : [];
        if (!pending.length) return showNotification('info','Info','No pending destinations to approve.');
        if (!confirm(`Approve all ${pending.length} pending destinations?`)) return;
        const ids = pending.map(d => d.id);
        await postAdminDestAction({ action: 'approve', ids });
        showNotification('success','Approved',`Approved ${ids.length} destination(s).`);
        if (typeof loadDestinationsData === 'function') loadDestinationsData();
      } catch (e) {
        showNotification('error','Error', e.message || 'Approve all failed');
      }
    };

    window.deleteDestination = async function(id){
      try {
        if (!confirm('Delete this destination? This action cannot be undone.')) return;
        await postAdminDestAction({ action: 'delete', id });
        showNotification('success','Deleted','Destination removed.');
        if (typeof loadDestinationsData === 'function') loadDestinationsData();
      } catch (e) {
        showNotification('error','Error', e.message || 'Delete failed');
      }
    };
  })();

  // ---------- Patch: Timeline always render latest from state.settings.timeline ----------
  function renderTimelineFromState(){
    try {
      const container = document.getElementById('timelineList');
      if (!container) return;
      const timeline = (typeof state !== 'undefined' && state?.settings?.timeline) ? state.settings.timeline : (window.state?.settings?.timeline || []);
      if (!Array.isArray(timeline) || !timeline.length) return;

      const items = timeline
        .filter(x => x && (x.year || x.title || x.description))
        .map(x => ({ year: String(x.year || '').trim(), title: String(x.title || '').trim(), description: String(x.description || '').trim() }))
        .filter(x => x.year && x.title)
        .sort((a,b) => (parseInt(a.year,10) || 0) - (parseInt(b.year,10) || 0));

      if (!items.length) return;

      container.innerHTML = items.map((item, idx) => `
        <div class="timeline-item" style="animation: fadeInUp 0.6s ease ${idx * 0.07}s both;">
          <div class="timeline-content">
            <div class="timeline-year">${escHtml(item.year)}</div>
            <div class="timeline-title">${escHtml(item.title)}</div>
            <div class="timeline-description">${escHtml(item.description || '')}</div>
          </div>
          <div class="timeline-dot"></div>
        </div>
      `).join('');
    } catch (e) {
      console.warn('[Patch] renderTimelineFromState failed:', e);
    }
  }

  // ---------- Boot hooks ----------
  document.addEventListener('DOMContentLoaded', function(){
    injectFileInputVisibilityHack();
    ensureTutorialFab();
    autoStartTutorialOnce();
    ensureNavbarRoutes();
    ensureUploadBindings();
    setTimeout(() => { try { renderTimelineFromState(); } catch (_) {} }, 600);
  });

  window.addEventListener('settingsUpdated', function(){
    injectFileInputVisibilityHack();
    ensureTutorialFab();
    ensureNavbarRoutes();
    ensureUploadBindings();
    setTimeout(renderTimelineFromState, 80);
  });

})();
</script>
<!-- FAREWELL_PATCH_V1_END -->
""".strip("\n")


@dataclass
class PatchResult:
    path: Path
    changed: bool
    notes: List[str]


def _remove_mail_garbage(text: str) -> Tuple[str, bool]:
    """
    Removes the accidental Google Workspace marketing snippet found in the provided index.html.
    """
    patterns = [
        r"(?s)\nGet professional email like '@your-company\.com'\s*.*?\nDetails\s*\n",
        r"(?s)\nGet professional email like '@your-company\.com'\s*.*?Programme Policies\s*\n",
    ]
    orig = text
    for pat in patterns:
        text = re.sub(pat, "\n", text)
    return text, (text != orig)


def _insert_patch_script(text: str) -> Tuple[str, bool]:
    if PATCH_MARKER_START in text and PATCH_MARKER_END in text:
        return text, False

    # Insert before </body> (preferred). Fallback: before </html>.
    insert_at = text.rfind("</body>")
    if insert_at == -1:
        insert_at = text.rfind("</html>")
    if insert_at == -1:
        raise RuntimeError("Could not find </body> or </html> to insert patch script.")

    new_text = text[:insert_at] + "\n\n" + PATCH_JS + "\n\n" + text[insert_at:]
    return new_text, True


def patch_index_html(path: Path) -> PatchResult:
    notes: List[str] = []
    original = path.read_text(encoding="utf-8", errors="strict")
    text = original

    text, removed = _remove_mail_garbage(text)
    if removed:
        notes.append("Removed stray mail/Workspace garbage snippet.")

    text, inserted = _insert_patch_script(text)
    if inserted:
        notes.append("Inserted Farewell Patch V1 script (tutorial/nav/upload/admin fixes).")

    changed = (text != original)
    if changed:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)

    return PatchResult(path=path, changed=changed, notes=notes)


def find_candidate_index_html(repo_root: Path) -> List[Path]:
    # Prefer root index.html if present, otherwise patch all index.html occurrences.
    root_index = repo_root / "index.html"
    if root_index.exists():
        return [root_index]

    candidates = list(repo_root.rglob("index.html"))
    # Filter out common dependency folders if present
    filtered: List[Path] = []
    for p in candidates:
        parts = {x.lower() for x in p.parts}
        if "node_modules" in parts or ".git" in parts or "dist" in parts and "node_modules" in parts:
            continue
        filtered.append(p)

    return sorted(filtered)


def main() -> int:
    repo_root = Path.cwd()
    targets = find_candidate_index_html(repo_root)

    if not targets:
        print("ERROR: Could not find any index.html in the repository.", file=sys.stderr)
        return 2

    results: List[PatchResult] = []
    for t in targets:
        try:
            results.append(patch_index_html(t))
        except Exception as e:
            print(f"ERROR patching {t}: {e}", file=sys.stderr)
            return 3

    changed_files = [r for r in results if r.changed]
    print("Farewell patch applied.")
    print(f"Targets found: {len(results)}")
    print(f"Files changed: {len(changed_files)}")
    for r in results:
        status = "CHANGED" if r.changed else "OK"
        print(f"- {status}: {r.path}")
        for n in r.notes:
            print(f"    * {n}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())