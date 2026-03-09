#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys


INDEX_HTML = Path("index.html")
SERVER_JS = Path("server.js")


NEW_NAV_LINKS = """<ul class="nav-links" id="navLinks">
 <li><a href="#home">Home</a></li>
 <li><a href="#countdown">Countdown</a></li>
 <li><a href="#memories">Memories</a></li>
 <li><a href="#teachers">Teachers</a></li>
 <li><a href="#timeline">Journey</a></li>
 <li><a href="#compilations">Compilations</a></li>
 <li><a href="#stereoDeckSection">StereoDeck</a></li>
 <li><a href="#distanceMapSection">Future Globe</a></li>
 <li><a href="#upload" class="nav-cta">Upload Memory</a></li>
 </ul>"""


STEREO_SECTION = """
<section id="stereoDeckSection" style="background: linear-gradient(180deg, var(--navy-medium) 0%, var(--navy-dark) 100%); padding: 80px 20px 40px;">
 <div class="container">
  <div class="section-header" style="margin-bottom: 30px;">
   <span class="section-badge">Music Controls</span>
   <h2 class="section-title">Cornerstone <span class="highlight">StereoDeck</span></h2>
   <p class="section-description">Pick a vibe and play it from the built-in deck.</p>
  </div>
  <div id="boomboxDock" style="display:flex; gap:16px; align-items:flex-end; justify-content:center; flex-wrap:wrap;">
   <div id="cassetteRack" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:10px; width:min(560px, 100%);"></div>
   <div id="boomboxUnit" style="width:min(400px,100%); background:linear-gradient(180deg,#4c4c54,#2a2a31); border:1px solid rgba(255,255,255,.18); border-radius:24px; box-shadow:0 20px 60px rgba(0,0,0,.45); padding:16px;">
    <div class="boombox-top" style="display:flex; gap:12px; align-items:center; justify-content:space-between; margin-bottom:12px;">
     <div class="boombox-brand" style="font-weight:700; color:var(--primary-gold);">Cornerstone StereoDeck</div>
     <button class="btn btn-secondary" type="button" id="ejectTapeBtn">Eject</button>
    </div>
    <div class="boombox-door" id="boomboxDoor" style="height:96px; border-radius:16px; border:2px solid rgba(255,255,255,.12); background:#111; display:flex; align-items:center; justify-content:center; color:#bbb; position:relative; overflow:hidden;">Choose a vibe</div>
    <div class="boombox-speakers" style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:12px;">
     <div class="boombox-speaker" style="aspect-ratio:1; border-radius:50%; background:radial-gradient(circle,#0d0d0f 0 20%,#2b2b33 21% 45%,#0c0c0f 46% 60%,#444 61% 100%); border:2px solid rgba(255,255,255,.08);"></div>
     <div class="boombox-speaker" style="aspect-ratio:1; border-radius:50%; background:radial-gradient(circle,#0d0d0f 0 20%,#2b2b33 21% 45%,#0c0c0f 46% 60%,#444 61% 100%); border:2px solid rgba(255,255,255,.08);"></div>
    </div>
   </div>
  </div>
  <div id="sniperMusicHint" style="text-align:center; color:var(--text-muted); font-size:.85rem; margin-top:8px;">Music controls</div>
 </div>
</section>
""".strip()


GLOBE_SECTION = """
<section id="distanceMapSection" style="background:
 radial-gradient(circle at 50% 0%, rgba(212,175,55,.14), transparent 30%),
 linear-gradient(180deg, #060a14 0%, #0d1730 60%, #081120 100%);
 padding: 90px 20px 70px;">
 <div class="container">
  <div class="section-header" style="margin-bottom: 26px;">
   <span class="section-badge">Erase the Distance</span>
   <h2 class="section-title">One <span class="highlight">Starting Point</span>, Many Destinations</h2>
   <p class="section-description">Select your future place in Google Maps, come back automatically, and watch it appear on the live 3D globe.</p>
  </div>

  <div style="max-width:1080px;margin:0 auto 18px;padding:18px 20px;border-radius:20px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.10);color:var(--text-muted);text-align:center;box-shadow:0 12px 34px rgba(0,0,0,.22);">
   <strong style="color:var(--text-light);">How it works:</strong>
   enter your name, choose whether you are saving your 11th / 12th place or your university place, open Google Maps, choose the place, and return. The coordinates will auto-fill and pins will appear on the globe.
  </div>

  <div id="distanceControls" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;align-items:end;max-width:1080px;margin:0 auto 18px;">
   <div class="form-group" style="margin-bottom:0;">
    <label>Your Name</label>
    <input class="form-input" id="distanceStudentName" placeholder="Enter your name" maxlength="80" />
   </div>
   <div class="form-group" style="margin-bottom:0;">
    <label>Section</label>
    <select class="form-select" id="distanceSection">
     <option value="10A">10A</option>
     <option value="10B">10B</option>
     <option value="10C">10C</option>
     <option value="10D">10D</option>
    </select>
   </div>
   <div class="form-group" style="margin-bottom:0;">
    <label>Place Type</label>
    <select class="form-select" id="distancePlaceType">
     <option value="school">11th / 12th place</option>
     <option value="university">University place</option>
    </select>
   </div>
   <div class="form-group" style="margin-bottom:0;">
    <label>Place Name</label>
    <input class="form-input" id="distancePlaceName" placeholder="Will auto-fill after maps selection" />
   </div>
   <div class="form-group" style="margin-bottom:0;">
    <label>Coordinates</label>
    <input class="form-input" id="selectedCoords" placeholder="Will auto-fill after maps selection" readonly />
   </div>
   <div class="form-group" style="margin-bottom:0;">
    <label>Class Ranking</label>
    <input class="form-input" id="distanceClassRanking" placeholder="Optional ranking/note from teachers" maxlength="120" />
   </div>
   <div style="grid-column:1 / -1;display:flex;gap:10px;justify-content:center;flex-wrap:wrap;">
    <button class="btn btn-primary" type="button" id="destinationLaunchBtn">Open Google Maps Selector</button>
    <button class="btn btn-secondary" type="button" id="destinationSaveBtn">Save On Globe</button>
    <button class="btn btn-secondary" type="button" id="distanceRefreshBtn">Refresh Globe</button>
   </div>
  </div>

  <div id="distanceGlobeUi" style="position:relative;display:grid;grid-template-columns:minmax(280px, 430px) minmax(260px, 1fr);gap:12px;max-width:1200px;margin:0 auto 14px;">
   <div style="background:rgba(0,0,0,.45);border:1px solid rgba(255,255,255,.12);border-radius:18px;backdrop-filter:blur(10px);color:#fff;padding:12px 14px;">
    <h4 style="margin:0 0 8px;font-family:var(--font-display);color:var(--primary-gold);">Live Globe Details</h4>
    <p style="margin:0 0 10px;color:rgba(255,255,255,.82);font-size:.92rem;line-height:1.6;">
     Gold is the school origin. Blue marks 11th / 12th places. Rose marks university places. The latest Google Maps selection fills below automatically.
    </p>
    <div id="distanceSelectedInfo" style="display:grid;gap:8px;">
     <div style="font-size:.88rem;color:rgba(255,255,255,.88);"><strong style="color:var(--primary-gold-light);">11th / 12th:</strong> <span id="distanceSchoolSelectedText">Not placed yet</span></div>
     <div style="font-size:.88rem;color:rgba(255,255,255,.88);"><strong style="color:var(--primary-gold-light);">University:</strong> <span id="distanceUniversitySelectedText">Not placed yet</span></div>
    </div>
   </div>
   <div style="background:rgba(0,0,0,.45);border:1px solid rgba(255,255,255,.12);border-radius:18px;backdrop-filter:blur(10px);color:#fff;padding:12px 14px;">
    <div id="distanceOverlayStats" style="display:flex;gap:8px;flex-wrap:wrap;"></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:10px;">
     <div style="border-radius:999px;padding:7px 10px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);font-size:.8rem;">Gold = School origin</div>
     <div style="border-radius:999px;padding:7px 10px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);font-size:.8rem;">Blue = 11th / 12th</div>
     <div style="border-radius:999px;padding:7px 10px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);font-size:.8rem;">Rose = University</div>
     <div style="border-radius:999px;padding:7px 10px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);font-size:.8rem;">Sections = 10A / 10B / 10C / 10D</div>
    </div>
   </div>
  </div>

  <div id="distanceMapWrap" style="min-height:760px;height:760px;position:relative;max-width:1200px;margin:0 auto;overflow:hidden;border-radius:24px;border:1px solid rgba(255,255,255,.10);background:
   radial-gradient(circle at 50% 30%, rgba(43,76,140,.35), rgba(3,7,15,.95) 60%),
   linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,0));box-shadow:0 24px 80px rgba(0,0,0,.35);">
   <div id="distanceGlobeCanvas" style="position:absolute;inset:0;width:100%;height:100%;"></div>
   <div id="distanceSelectionStatus" style="position:absolute;left:50%;bottom:22px;transform:translateX(-50%);z-index:3;padding:10px 16px;border-radius:999px;background:rgba(0,0,0,.55);border:1px solid rgba(255,255,255,.14);color:#fff;backdrop-filter:blur(10px);max-width:92%;text-align:center;">
    Open Google Maps, pick a place, return here, and save it on the globe.
   </div>
  </div>
 </div>
</section>
""".strip()


GLOBE_DEPENDENCIES = """
<script src="https://unpkg.com/three@0.160.0/build/three.min.js"></script>
<script src="https://unpkg.com/globe.gl"></script>
""".strip()


PRODUCTION_SCRIPT = r"""
<script>
(function () {
 if (window.__PRODUCTION_GLOBE_AND_STEREO_PATCH__) return;
 window.__PRODUCTION_GLOBE_AND_STEREO_PATCH__ = true;

 const SCHOOL_ORIGIN = {
  lat: 12.9716,
  lng: 77.5946,
  label: 'Cornerstone International School'
 };

 const SECTION_COLORS = {
  '10A': '#55b9ff',
  '10B': '#74d680',
  '10C': '#ff9f55',
  '10D': '#ff7aa8'
 };

 const statePatch = {
  activeBoomboxAudio: null,
  globe: null,
  globeReady: false,
  lastStatsRows: [],
  pendingSchoolPoint: null,
  pendingUniversityPoint: null
 };

 function ensureFooterAtBottom() {
  const footer = document.querySelector('footer');
  if (!footer) return;
  const quote = document.getElementById('quote');
  if (quote && footer.previousElementSibling !== quote) {
   footer.parentNode.appendChild(footer);
  }
 }

 function patchTopNavigation() {
  const navLinks = document.getElementById('navLinks');
  if (!navLinks) return;

  const ensureLink = (href, label, className='') => {
   if (navLinks.querySelector('a[href="' + href + '"]')) return;
   const li = document.createElement('li');
   li.innerHTML = '<a href="' + href + '"' + (className ? ' class="' + className + '"' : '') + '>' + label + '</a>';
   navLinks.appendChild(li);
  };

  ensureLink('#stereoDeckSection', 'StereoDeck');
  ensureLink('#distanceMapSection', 'Future Globe');
 }

 function getMusicSettings() {
  const settings = (window.state && window.state.settings) ? window.state.settings : {};
  return Object.assign({
   boomboxGraduationVibes: '',
   boomboxSadBoiHours: '',
   boomboxHype: ''
  }, settings.music || {});
 }

 function resolveMusicPath(value) {
  if (!value) return '';
  if (/^https?:\/\//i.test(String(value)) || String(value).startsWith('/')) return String(value);
  return '/music/' + String(value).replace(/^\/+/, '');
 }

 function stopBoombox() {
  if (statePatch.activeBoomboxAudio) {
   try { statePatch.activeBoomboxAudio.pause(); } catch (error) {}
   statePatch.activeBoomboxAudio = null;
  }
  const door = document.getElementById('boomboxDoor');
  if (door) {
   door.classList.remove('has-tape');
   door.textContent = 'Choose a vibe';
  }
 }

 function playBoombox(label, key) {
  const music = getMusicSettings();
  const src = resolveMusicPath(music[key]);
  if (!src) {
   showNotification('info', 'Music missing', label + ' has not been configured yet.');
   return;
  }
  stopBoombox();
  try {
   const audio = new Audio(src);
   audio.loop = true;
   audio.volume = 0.32;
   audio.play().catch(() => {});
   statePatch.activeBoomboxAudio = audio;
   const door = document.getElementById('boomboxDoor');
   if (door) {
    door.classList.add('has-tape');
    door.innerHTML = '<div style="text-align:center;"><div style="font-weight:700;color:var(--primary-gold);">' + label + '</div><div style="opacity:.7;font-size:.82rem;">Now playing</div></div>';
   }
  } catch (error) {
   console.error(error);
   showNotification('error', 'Playback failed', 'Could not play ' + label + '.');
  }
 }

 function buildStereoDeck() {
  const rack = document.getElementById('cassetteRack');
  if (!rack) return;
  rack.innerHTML = '';

  const tracks = [
   { label: 'Graduation Vibes', key: 'boomboxGraduationVibes' },
   { label: 'Sad Boi Hours', key: 'boomboxSadBoiHours' },
   { label: 'Hype', key: 'boomboxHype' }
  ];

  tracks.forEach(track => {
   const btn = document.createElement('button');
   btn.type = 'button';
   btn.className = 'cassette btn btn-secondary';
   btn.style.width = '100%';
   btn.style.justifyContent = 'center';
   btn.textContent = track.label;
   btn.addEventListener('click', () => playBoombox(track.label, track.key));
   rack.appendChild(btn);
  });

  const eject = document.getElementById('ejectTapeBtn');
  if (eject && !eject.dataset.bound) {
   eject.dataset.bound = '1';
   eject.addEventListener('click', stopBoombox);
  }
 }

 function updateSelectionTexts() {
  const schoolText = document.getElementById('distanceSchoolSelectedText');
  const uniText = document.getElementById('distanceUniversitySelectedText');

  if (schoolText) {
   schoolText.textContent = statePatch.pendingSchoolPoint
    ? statePatch.pendingSchoolPoint.label + ' (' + statePatch.pendingSchoolPoint.lat.toFixed(4) + ', ' + statePatch.pendingSchoolPoint.lng.toFixed(4) + ')'
    : 'Not placed yet';
  }

  if (uniText) {
   uniText.textContent = statePatch.pendingUniversityPoint
    ? statePatch.pendingUniversityPoint.label + ' (' + statePatch.pendingUniversityPoint.lat.toFixed(4) + ', ' + statePatch.pendingUniversityPoint.lng.toFixed(4) + ')'
    : 'Not placed yet';
  }
 }

 function updateCoordsFieldFromPending() {
  const input = document.getElementById('selectedCoords');
  if (!input) return;
  const parts = [];
  if (statePatch.pendingSchoolPoint) {
   parts.push('11th/12th: ' + statePatch.pendingSchoolPoint.lat.toFixed(6) + ',' + statePatch.pendingSchoolPoint.lng.toFixed(6));
  }
  if (statePatch.pendingUniversityPoint) {
   parts.push('University: ' + statePatch.pendingUniversityPoint.lat.toFixed(6) + ',' + statePatch.pendingUniversityPoint.lng.toFixed(6));
  }
  input.value = parts.join(' | ');
 }

 function setGlobeStatus(message) {
  const el = document.getElementById('distanceSelectionStatus');
  if (el) el.textContent = message;
 }

 function getHashParams() {
  const hash = window.location.hash || '';
  const idx = hash.indexOf('?');
  if (idx === -1) return new URLSearchParams();
  return new URLSearchParams(hash.slice(idx + 1));
 }

 function buildMapsReturnUrl() {
  return window.location.origin + window.location.pathname + '#distanceMapSection';
 }

 function openGoogleMapsSelector() {
  const studentName = String(document.getElementById('distanceStudentName')?.value || '').trim();
  const placeType = String(document.getElementById('distancePlaceType')?.value || 'school').trim();
  const section = String(document.getElementById('distanceSection')?.value || '10A').trim();
  const placeName = String(document.getElementById('distancePlaceName')?.value || '').trim();
  const ranking = String(document.getElementById('distanceClassRanking')?.value || '').trim();

  if (!studentName) {
   showNotification('error', 'Name needed', 'Enter your name first.');
   return;
  }

  const returnUrl = buildMapsReturnUrl();
  const query = placeName || 'future place';
  const mapsUrl =
   'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(query) +
   '&travelmode=driving';

  const payload = {
   studentName,
   placeType,
   section,
   ranking,
   returnUrl
  };

  sessionStorage.setItem('cornerstone_globe_pending', JSON.stringify(payload));
  window.open(mapsUrl, '_blank');
  setGlobeStatus('Google Maps opened. After selecting a place, come back here and paste or trigger the final coordinates link.');
  showNotification('info', 'Google Maps opened', 'Select the place there, then return here.');
 }

 function extractCoordinatesFromText(value) {
  const m = String(value || '').match(/(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)/);
  if (!m) return null;
  const lat = Number(m[1]);
  const lng = Number(m[2]);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  return { lat, lng };
 }

 async function geocodePlaceName(placeName) {
  const url = 'https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=' + encodeURIComponent(placeName);
  const res = await fetch(url, {
   headers: { 'Accept': 'application/json' }
  });
  if (!res.ok) throw new Error('Could not resolve place');
  const data = await res.json();
  if (!Array.isArray(data) || !data.length) throw new Error('No coordinates found');
  return {
   lat: Number(data[0].lat),
   lng: Number(data[0].lon),
   label: data[0].display_name || placeName
  };
 }

 async function autoHandleReturnFromMaps() {
  const pendingRaw = sessionStorage.getItem('cornerstone_globe_pending');
  if (!pendingRaw) return;

  let pending = null;
  try {
   pending = JSON.parse(pendingRaw);
  } catch (error) {
   sessionStorage.removeItem('cornerstone_globe_pending');
   return;
  }

  const coordsField = document.getElementById('selectedCoords');
  const placeField = document.getElementById('distancePlaceName');
  const studentField = document.getElementById('distanceStudentName');
  const typeField = document.getElementById('distancePlaceType');
  const sectionField = document.getElementById('distanceSection');
  const rankingField = document.getElementById('distanceClassRanking');

  if (studentField && pending.studentName) studentField.value = pending.studentName;
  if (typeField && pending.placeType) typeField.value = pending.placeType;
  if (sectionField && pending.section) sectionField.value = pending.section;
  if (rankingField && pending.ranking) rankingField.value = pending.ranking;

  const hashParams = getHashParams();
  const textCandidates = [
   hashParams.get('coords'),
   hashParams.get('q'),
   hashParams.get('query'),
   hashParams.get('place'),
   placeField ? placeField.value : ''
  ].filter(Boolean);

  let resolved = null;
  for (const candidate of textCandidates) {
   const coords = extractCoordinatesFromText(candidate);
   if (coords) {
    resolved = {
     lat: coords.lat,
     lng: coords.lng,
     label: candidate
    };
    break;
   }
  }

  if (!resolved && placeField && placeField.value.trim()) {
   try {
    resolved = await geocodePlaceName(placeField.value.trim());
   } catch (error) {}
  }

  if (!resolved && pending.lastPlaceName) {
   try {
    resolved = await geocodePlaceName(String(pending.lastPlaceName));
   } catch (error) {}
  }

  if (!resolved) return;

  const prettyLabel = placeField && placeField.value.trim() ? placeField.value.trim() : resolved.label;
  if (placeField) placeField.value = prettyLabel;
  if (coordsField) coordsField.value = resolved.lat.toFixed(6) + ',' + resolved.lng.toFixed(6);

  if (String(pending.placeType) === 'university') {
   statePatch.pendingUniversityPoint = {
    lat: resolved.lat,
    lng: resolved.lng,
    label: prettyLabel,
    section: pending.section || '10A',
    ranking: pending.ranking || '',
    studentName: pending.studentName || ''
   };
  } else {
   statePatch.pendingSchoolPoint = {
    lat: resolved.lat,
    lng: resolved.lng,
    label: prettyLabel,
    section: pending.section || '10A',
    ranking: pending.ranking || '',
    studentName: pending.studentName || ''
   };
  }

  updateSelectionTexts();
  updateCoordsFieldFromPending();
  renderSavedGlobe();
  setGlobeStatus('Coordinates auto-filled after return.');
  showNotification('success', 'Coordinates filled', 'The place was loaded back into the globe form.');
 }

 function initGlobe() {
  const el = document.getElementById('distanceGlobeCanvas');
  if (!el || statePatch.globe || typeof Globe !== 'function') return;

  const globe = Globe()
   .globeImageUrl('https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg')
   .bumpImageUrl('https://unpkg.com/three-globe/example/img/earth-topology.png')
   .backgroundImageUrl('https://unpkg.com/three-globe/example/img/night-sky.png')
   .atmosphereColor('#9cc8ff')
   .atmosphereAltitude(0.22)
   .arcColor(d => d.color)
   .arcStroke(0.9)
   .arcDashLength(0.35)
   .arcDashGap(0.18)
   .arcDashAnimateTime(2400)
   .pointAltitude(d => d.alt || 0.03)
   .pointRadius(d => d.radius || 0.28)
   .pointColor(d => d.color)
   .labelText(d => d.label)
   .labelLat(d => d.lat)
   .labelLng(d => d.lng)
   .labelSize(1.3)
   .labelDotRadius(0.35)
   .labelColor(() => '#ffffff');

  globe(el);
  globe.pointOfView({ lat: 18, lng: 20, altitude: 2.05 }, 0);
  globe.controls().autoRotate = true;
  globe.controls().autoRotateSpeed = 0.55;

  statePatch.globe = globe;
  statePatch.globeReady = true;
 }

 function getSectionColor(section) {
  return SECTION_COLORS[String(section || '').toUpperCase()] || '#55b9ff';
 }

 function renderStats(rows) {
  const box = document.getElementById('distanceOverlayStats');
  if (!box) return;

  const totalStudents = rows.length;
  const schoolCount = rows.filter(r => r.schoolPoint).length;
  const uniCount = rows.filter(r => r.universityPoint).length;

  const sections = { '10A': 0, '10B': 0, '10C': 0, '10D': 0 };
  rows.forEach(row => {
   const s = String(row.section || '').toUpperCase();
   if (sections[s] !== undefined) sections[s] += 1;
  });

  box.innerHTML = [
   '<div style="background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);padding:8px 12px;border-radius:999px;font-size:.82rem;">' + totalStudents + ' students plotted</div>',
   '<div style="background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);padding:8px 12px;border-radius:999px;font-size:.82rem;">' + schoolCount + ' school paths</div>',
   '<div style="background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);padding:8px 12px;border-radius:999px;font-size:.82rem;">' + uniCount + ' university dreams</div>',
   '<div style="background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);padding:8px 12px;border-radius:999px;font-size:.82rem;">10A: ' + sections['10A'] + '</div>',
   '<div style="background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);padding:8px 12px;border-radius:999px;font-size:.82rem;">10B: ' + sections['10B'] + '</div>',
   '<div style="background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);padding:8px 12px;border-radius:999px;font-size:.82rem;">10C: ' + sections['10C'] + '</div>',
   '<div style="background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);padding:8px 12px;border-radius:999px;font-size:.82rem;">10D: ' + sections['10D'] + '</div>'
  ].join('');
 }

 function renderSavedGlobe() {
  if (!statePatch.globeReady || !statePatch.globe) return;

  const rows = statePatch.lastStatsRows || [];
  const points = [
   { lat: SCHOOL_ORIGIN.lat, lng: SCHOOL_ORIGIN.lng, color: '#ffd84d', radius: 0.42, alt: 0.065, label: SCHOOL_ORIGIN.label }
  ];
  const arcs = [];

  rows.forEach(row => {
   const section = String(row.section || '10A').toUpperCase();
   const sectionColor = getSectionColor(section);

   if (row.schoolPoint && Number.isFinite(row.schoolPoint.lat) && Number.isFinite(row.schoolPoint.lng)) {
    points.push({
     lat: row.schoolPoint.lat,
     lng: row.schoolPoint.lng,
     color: sectionColor,
     radius: 0.28,
     alt: 0.05,
     label: (row.studentName || 'Student') + ' • ' + section + ' • 11th / 12th' + (row.ranking ? ' • ' + row.ranking : '')
    });
    arcs.push({
     startLat: SCHOOL_ORIGIN.lat,
     startLng: SCHOOL_ORIGIN.lng,
     endLat: row.schoolPoint.lat,
     endLng: row.schoolPoint.lng,
     color: [sectionColor]
    });
   }

   if (row.universityPoint && Number.isFinite(row.universityPoint.lat) && Number.isFinite(row.universityPoint.lng)) {
    points.push({
     lat: row.universityPoint.lat,
     lng: row.universityPoint.lng,
     color: '#ff7aa8',
     radius: 0.28,
     alt: 0.05,
     label: (row.studentName || 'Student') + ' • ' + section + ' • University' + (row.ranking ? ' • ' + row.ranking : '')
    });
    arcs.push({
     startLat: SCHOOL_ORIGIN.lat,
     startLng: SCHOOL_ORIGIN.lng,
     endLat: row.universityPoint.lat,
     endLng: row.universityPoint.lng,
     color: ['#ff7aa8']
    });
   }
  });

  if (statePatch.pendingSchoolPoint) {
   points.push({
    lat: statePatch.pendingSchoolPoint.lat,
    lng: statePatch.pendingSchoolPoint.lng,
    color: getSectionColor(statePatch.pendingSchoolPoint.section),
    radius: 0.33,
    alt: 0.055,
    label: 'Pending school place • ' + statePatch.pendingSchoolPoint.label
   });
  }

  if (statePatch.pendingUniversityPoint) {
    points.push({
     lat: statePatch.pendingUniversityPoint.lat,
     lng: statePatch.pendingUniversityPoint.lng,
     color: '#ff9ebd',
     radius: 0.33,
     alt: 0.055,
     label: 'Pending university place • ' + statePatch.pendingUniversityPoint.label
    });
  }

  statePatch.globe.pointsData(points);
  statePatch.globe.arcsData(arcs);
 }

 async function loadSavedPins() {
  try {
   const res = await fetch(apiUrl('/api/destinations/pin-submissions'));
   const data = await res.json();
   if (data.success && Array.isArray(data.submissions)) {
    statePatch.lastStatsRows = data.submissions;
    renderStats(statePatch.lastStatsRows);
    renderSavedGlobe();
    return;
   }
  } catch (error) {
   console.error('Pin submissions endpoint failed', error);
  }

  try {
   const res = await fetch(apiUrl('/api/destinations/submissions'));
   const data = await res.json();
   if (data.success && Array.isArray(data.submissions)) {
    statePatch.lastStatsRows = data.submissions.map(row => ({
     studentName: row.studentName,
     section: row.section || '10A',
     ranking: row.ranking || '',
     schoolPoint: null,
     universityPoint: null,
     schoolPlace: row.schoolPlace,
     universityPlace: row.universityPlace
    }));
    renderStats(statePatch.lastStatsRows);
    renderSavedGlobe();
   }
  } catch (error) {
   console.error('Submissions fallback failed', error);
  }
 }

 async function saveToGlobe() {
  const studentName = String(document.getElementById('distanceStudentName')?.value || '').trim();
  const section = String(document.getElementById('distanceSection')?.value || '10A').trim();
  const ranking = String(document.getElementById('distanceClassRanking')?.value || '').trim();
  const placeName = String(document.getElementById('distancePlaceName')?.value || '').trim();
  const coords = String(document.getElementById('selectedCoords')?.value || '').trim();

  if (!studentName) {
   showNotification('error', 'Name needed', 'Enter your name first.');
   return;
  }

  let schoolPoint = statePatch.pendingSchoolPoint ? {
   lat: statePatch.pendingSchoolPoint.lat,
   lng: statePatch.pendingSchoolPoint.lng
  } : null;

  let universityPoint = statePatch.pendingUniversityPoint ? {
   lat: statePatch.pendingUniversityPoint.lat,
   lng: statePatch.pendingUniversityPoint.lng
  } : null;

  if (!schoolPoint && !universityPoint && coords) {
   const direct = extractCoordinatesFromText(coords);
   if (direct) {
    const type = String(document.getElementById('distancePlaceType')?.value || 'school').trim();
    if (type === 'university') {
     universityPoint = { lat: direct.lat, lng: direct.lng };
     statePatch.pendingUniversityPoint = {
      lat: direct.lat,
      lng: direct.lng,
      label: placeName || 'Selected place',
      studentName,
      section,
      ranking
     };
    } else {
     schoolPoint = { lat: direct.lat, lng: direct.lng };
     statePatch.pendingSchoolPoint = {
      lat: direct.lat,
      lng: direct.lng,
      label: placeName || 'Selected place',
      studentName,
      section,
      ranking
     };
    }
   }
  }

  if (!schoolPoint && !universityPoint) {
   showNotification('error', 'No coordinates', 'Open Google Maps first so the coordinates can be filled.');
   return;
  }

  try {
   const res = await fetch(apiUrl('/api/destinations/pin-submit'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
     studentName,
     section,
     ranking,
     schoolPoint,
     universityPoint,
     schoolPlaceName: statePatch.pendingSchoolPoint?.label || '',
     universityPlaceName: statePatch.pendingUniversityPoint?.label || ''
    })
   });
   const data = await res.json();
   if (!data.success) {
    showNotification('error', 'Could not save', data.error || 'Save failed.');
    return;
   }
   setGlobeStatus('Saved on the globe successfully.');
   showNotification('success', 'Saved', 'Your future path is now on the globe.');
   await loadSavedPins();
  } catch (error) {
   console.error(error);
   showNotification('error', 'Could not save', error.message || 'Save failed.');
  }
 }

 function patchAdminSettingsForPlacesAndMusic() {
  const oldRender = window.renderSettingsPanelHtml;
  if (typeof oldRender !== 'function' || oldRender.__globeAdminPatched) return;

  window.renderSettingsPanelHtml = function () {
   let html = oldRender.apply(this, arguments);

   if (!html.includes('id="distanceDestinationsAdvancedAdmin"')) {
    const placesInject = `
<div id="distanceDestinationsAdvancedAdmin" style="margin-top:16px; border:1px solid var(--glass-border); border-radius:16px; padding:14px; background:rgba(255,255,255,0.03);">
 <h4 style="font-family:var(--font-display); color:var(--primary-gold); margin-bottom:10px;">Future Globe Places</h4>
 <p class="mini-pill" style="margin-bottom:10px;">One place per line. You can write only the place name, or use <strong>Place Name|lat|lng</strong> for perfect coordinates.</p>
 <textarea class="form-textarea" id="destinationsAdminTextAdvanced" style="min-height:160px;" placeholder="Bangalore|12.9716|77.5946&#10;Delhi|28.6139|77.2090&#10;London|51.5072|-0.1276"></textarea>
 <div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:10px;">
  <button class="admin-btn admin-btn-primary" type="button" onclick="saveAdvancedDestinationsAdmin()">Save Places</button>
  <button class="admin-btn admin-btn-secondary" type="button" onclick="loadAdvancedDestinationSubmissionsAdmin()">View Globe Entries</button>
 </div>
 <div id="advancedDestinationSubmissionsAdmin" style="margin-top:12px;"></div>
</div>`;
    html = html.replace('</div></div></div>', placesInject + '</div></div></div>');
   }

   if (!html.includes('id="sniperMusicUploadPanelAdvanced"')) {
    const musicInject = `
<div id="sniperMusicUploadPanelAdvanced" style="margin-top:16px; border:1px solid var(--glass-border); border-radius:16px; padding:14px; background:rgba(255,255,255,0.03);">
 <h4 style="font-family:var(--font-display); color:var(--primary-gold); margin-bottom:10px;">Music Upload and Set</h4>
 <p class="mini-pill" style="margin-bottom:10px;">Upload songs directly just like videos, then save the returned file names into the music fields.</p>
 <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; align-items:end;">
  <div class="form-group">
   <label>Upload Song File</label>
   <input type="file" class="form-input" id="adminMusicUploadFile" accept="audio/*" style="padding:6px;" />
  </div>
  <div class="form-group">
   <label>Music Slot</label>
   <select class="form-select" id="adminMusicUploadSlot">
    <option value="boomboxGraduationVibes">Boombox - Graduation Vibes</option>
    <option value="boomboxSadBoiHours">Boombox - Sad Boi Hours</option>
    <option value="boomboxHype">Boombox - Hype</option>
   </select>
  </div>
 </div>
 <button class="admin-btn admin-btn-primary" style="margin-top:10px;" type="button" onclick="uploadAndAssignMusicFile()">Upload and Set Music</button>
 <div class="mini-pill" id="adminMusicUploadStatus" style="margin-top:10px;">No upload yet.</div>
</div>`;
    html = html.replace('</div></div></div>', musicInject + '</div></div></div>');
   }

   return html;
  };

  window.renderSettingsPanelHtml.__globeAdminPatched = true;

  const oldSync = window.syncSettingsEditor;
  if (typeof oldSync === 'function' && !oldSync.__globeAdminPatched) {
   window.syncSettingsEditor = function () {
    oldSync.apply(this, arguments);
    loadAdvancedDestinationsIntoEditor();
   };
   window.syncSettingsEditor.__globeAdminPatched = true;
  }

  window.saveAdvancedDestinationsAdmin = async function () {
   const textarea = document.getElementById('destinationsAdminTextAdvanced');
   const raw = String(textarea?.value || '');
   const lines = raw.split(/\r?\n/).map(line => line.trim()).filter(Boolean);

   const places = lines.map(line => {
    const parts = line.split('|').map(x => x.trim());
    if (parts.length >= 3) {
     return {
      place: parts[0],
      lat: Number(parts[1]),
      lng: Number(parts[2])
     };
    }
    return { place: parts[0] };
   });

   try {
    const res = await fetch(apiUrl('/api/admin/destinations-v2'), {
     method: 'POST',
     headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + (window.state?.adminToken || '')
     },
     body: JSON.stringify({ places })
    });
    const data = await res.json();
    if (!data.success) {
     showNotification('error', 'Save failed', data.error || 'Could not save places.');
     return;
    }
    showNotification('success', 'Saved', 'Advanced globe places updated.');
   } catch (error) {
    showNotification('error', 'Save failed', error.message || 'Could not save places.');
   }
  };

  window.loadAdvancedDestinationSubmissionsAdmin = async function () {
   const box = document.getElementById('advancedDestinationSubmissionsAdmin');
   if (!box) return;
   box.innerHTML = '<div class="mini-pill">Loading globe entries...</div>';

   try {
    const res = await fetch(apiUrl('/api/destinations/pin-submissions'));
    const data = await res.json();
    if (!data.success || !Array.isArray(data.submissions) || !data.submissions.length) {
     box.innerHTML = '<div class="mini-pill">No globe entries yet.</div>';
     return;
    }

    box.innerHTML = data.submissions.slice().reverse().map(row => `
<div class="admin-memory-card" style="padding:12px; margin-bottom:10px;">
 <div style="font-weight:800;">${escapeHtml(row.studentName || 'Student')} <span class="mini-pill" style="margin-left:8px;">${escapeHtml(row.section || '10A')}</span></div>
 <div style="color:var(--text-muted); font-size:.9rem; margin-top:6px;">11th / 12th: <strong style="color:var(--text-light);">${escapeHtml(row.schoolPlaceName || (row.schoolPoint ? row.schoolPoint.lat + ',' + row.schoolPoint.lng : '—'))}</strong></div>
 <div style="color:var(--text-muted); font-size:.9rem; margin-top:4px;">University: <strong style="color:var(--text-light);">${escapeHtml(row.universityPlaceName || (row.universityPoint ? row.universityPoint.lat + ',' + row.universityPoint.lng : '—'))}</strong></div>
 <div style="color:var(--text-muted); font-size:.9rem; margin-top:4px;">Ranking: <strong style="color:var(--text-light);">${escapeHtml(row.ranking || '—')}</strong></div>
</div>`).join('');
   } catch (error) {
    box.innerHTML = '<div class="mini-pill">Error loading globe entries.</div>';
   }
  };

  async function loadAdvancedDestinationsIntoEditor() {
   const textarea = document.getElementById('destinationsAdminTextAdvanced');
   if (!textarea) return;

   try {
    const res = await fetch(apiUrl('/api/destinations'));
    const data = await res.json();
    const rows = Array.isArray(data?.destinations) ? data.destinations : [];
    textarea.value = rows.map(item => {
     const place = String(item.place || item.name || '').trim();
     const lat = Number(item.lat);
     const lng = Number(item.lng);
     if (Number.isFinite(lat) && Number.isFinite(lng)) {
      return place + '|' + lat + '|' + lng;
     }
     return place;
    }).filter(Boolean).join('\n');
   } catch (error) {}
  }

  window.uploadAndAssignMusicFile = async function () {
   const file = document.getElementById('adminMusicUploadFile')?.files?.[0];
   const slot = document.getElementById('adminMusicUploadSlot')?.value;
   const status = document.getElementById('adminMusicUploadStatus');

   if (!file || !slot) {
    showNotification('error', 'Missing fields', 'Choose a music file and slot.');
    return;
   }

   try {
    const fd = new FormData();
    fd.append('audio', file);
    fd.append('teacherName', '__music__' + slot);

    const res = await fetch(apiUrl('/api/admin/teacher-audio'), {
     method: 'POST',
     headers: {
      'Authorization': 'Bearer ' + (window.state?.adminToken || '')
     },
     body: fd
    });
    const data = await res.json();
    if (!data.success) {
     showNotification('error', 'Upload failed', data.error || 'Could not upload music.');
     if (status) status.textContent = 'Upload failed.';
     return;
    }

    const savedPath = data.item?.audioPath || data.item?.path || '';
    if (!savedPath) {
      showNotification('error', 'Upload failed', 'No saved file path returned.');
      return;
    }

    if (!window.state.settings.music) window.state.settings.music = {};
    window.state.settings.music[slot] = savedPath;

    const settingsPayload = structuredClone(window.state.settings);
    const saveRes = await fetch(apiUrl('/api/admin/settings'), {
     method: 'POST',
     headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + (window.state?.adminToken || '')
     },
     body: JSON.stringify({ settings: settingsPayload })
    });
    const saveData = await saveRes.json();
    if (!saveData.success) {
     showNotification('error', 'Save failed', saveData.error || 'Music uploaded but settings could not be saved.');
     return;
    }

    if (status) status.textContent = 'Uploaded and set: ' + savedPath;
    showNotification('success', 'Uploaded', 'Music file uploaded and assigned.');
   } catch (error) {
    showNotification('error', 'Upload failed', error.message || 'Could not upload music.');
   }
  };
 }

 function patchReadSettingsToKeepMusic() {
  const oldRead = window.readSettingsFromEditor;
  if (typeof oldRead !== 'function' || oldRead.__musicPreservedPatched) return;

  window.readSettingsFromEditor = function () {
   const settings = oldRead.apply(this, arguments);
   settings.music = structuredClone((window.state && window.state.settings && window.state.settings.music) ? window.state.settings.music : {});
   return settings;
  };
  window.readSettingsFromEditor.__musicPreservedPatched = true;
 }

 function boot() {
  ensureFooterAtBottom();
  patchTopNavigation();
  buildStereoDeck();
  initGlobe();
  updateSelectionTexts();
  updateCoordsFieldFromPending();
  autoHandleReturnFromMaps();
  loadSavedPins();
  patchAdminSettingsForPlacesAndMusic();
  patchReadSettingsToKeepMusic();

  document.getElementById('destinationLaunchBtn')?.addEventListener('click', openGoogleMapsSelector);
  document.getElementById('destinationSaveBtn')?.addEventListener('click', saveToGlobe);
  document.getElementById('distanceRefreshBtn')?.addEventListener('click', loadSavedPins);
 }

 document.addEventListener('DOMContentLoaded', boot);
})();
</script>
""".strip()


def clean_text(text: str) -> str:
    return text.replace("￾", "").replace("\uFFFE", "")


def replace_first(pattern: str, repl: str, text: str, flags: int = re.DOTALL) -> str:
    return re.sub(pattern, repl, text, count=1, flags=flags)


def patch_html() -> None:
    text = clean_text(INDEX_HTML.read_text(encoding="utf-8", errors="ignore"))

    text = replace_first(
        r'<ul class="nav-links" id="navLinks">.*?</ul>',
        NEW_NAV_LINKS,
        text,
    )

    text = replace_first(
        r'<section id="stereoDeckSection".*?</section>',
        STEREO_SECTION,
        text,
    )

    text = replace_first(
        r'<section id="distanceMapSection".*?</section>',
        GLOBE_SECTION,
        text,
    )

    text = re.sub(
        r'<script>\s*\(function\s*\(\)\s*\{\s*if \(window\.__TOP_NAV_PATCH__\).*?</script>',
        '',
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'<script>\s*\(function\s*\(\)\s*\{\s*if \(window\.__PRODUCTION_STEREODECK_PATCH__\).*?</script>',
        '',
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'<script>\s*\(function\s*\(\)\s*\{\s*if \(window\.__DISTANCE_SELECTOR_PRODUCTION_PATCH__\).*?</script>',
        '',
        text,
        flags=re.DOTALL,
    )

    if "https://unpkg.com/globe.gl" not in text:
        text = text.replace("</body>", GLOBE_DEPENDENCIES + "\n" + PRODUCTION_SCRIPT + "\n</body>")
    else:
        text = text.replace("</body>", PRODUCTION_SCRIPT + "\n</body>")

    # Keep footer at bottom by making sure it remains after all main sections.
    footer_match = re.search(r'<footer>.*?</footer>', text, flags=re.DOTALL)
    if footer_match:
        footer_html = footer_match.group(0)
        text = re.sub(r'<footer>.*?</footer>', '', text, flags=re.DOTALL)
        text = text.replace("</body>", footer_html + "\n</body>")

    INDEX_HTML.write_text(text, encoding="utf-8")


SERVER_APPEND = r"""
// === PRODUCTION_GLOBE_AND_MUSIC_PATCH_START ===
(() => {
 if (global.__PRODUCTION_GLOBE_AND_MUSIC_PATCH__) return;
 global.__PRODUCTION_GLOBE_AND_MUSIC_PATCH__ = true;

 const musicDir = path.join(__dirname, 'music');
 if (!fs.existsSync(musicDir)) {
  fs.mkdirSync(musicDir, { recursive: true });
 }
 app.use('/music', express.static(musicDir));

 const destinationsPathAdvanced = path.join(databaseDir, 'destinations.json');

 function readDestinationsAdvanced() {
  return safeReadJson(destinationsPathAdvanced, { destinations: [], submissions: [], nextId: 1 });
 }

 function writeDestinationsAdvanced(data) {
  safeWriteJson(destinationsPathAdvanced, data);
 }

 app.post('/api/admin/destinations-v2', (req, res) => {
  try {
   const auth = requireAdmin(req, res);
   if (!auth) return;
   if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });

   const places = Array.isArray(req.body?.places) ? req.body.places : [];
   const cleaned = places.map(item => {
    if (typeof item === 'string') {
     return { place: item.trim() };
    }
    return {
     place: String(item?.place || item?.name || '').trim(),
     lat: Number(item?.lat),
     lng: Number(item?.lng)
    };
   }).filter(item => item.place).slice(0, 1000);

   const db = readDestinationsAdvanced();
   db.destinations = cleaned;
   writeDestinationsAdvanced(db);
   audit(auth.user.id, 'save-destinations-v2-advanced', { count: cleaned.length });
   res.json({ success: true, count: cleaned.length });
  } catch (e) {
   res.status(500).json({ success: false, error: e.message });
  }
 });

 app.get('/api/destinations', (req, res) => {
  try {
   const db = readDestinationsAdvanced();
   const items = (db.destinations || []).map(item => ({
    place: String(item.place || item.name || '').trim(),
    name: String(item.place || item.name || '').trim(),
    lat: Number.isFinite(Number(item.lat)) ? Number(item.lat) : undefined,
    lng: Number.isFinite(Number(item.lng)) ? Number(item.lng) : undefined
   })).filter(item => item.place);
   res.json({ success: true, destinations: items });
  } catch (e) {
   res.status(500).json({ success: false, error: e.message });
  }
 });

 app.post('/api/destinations/pin-submit', (req, res) => {
  try {
   const studentName = String(req.body?.studentName || '').trim().substring(0, 80);
   const section = String(req.body?.section || '10A').trim().substring(0, 10);
   const ranking = String(req.body?.ranking || '').trim().substring(0, 120);
   const schoolPlaceName = String(req.body?.schoolPlaceName || '').trim().substring(0, 160);
   const universityPlaceName = String(req.body?.universityPlaceName || '').trim().substring(0, 160);
   const schoolPoint = req.body?.schoolPoint || null;
   const universityPoint = req.body?.universityPoint || null;

   if (!studentName) {
    return res.status(400).json({ success: false, error: 'studentName required' });
   }

   const validPoint = p => p && Number.isFinite(Number(p.lat)) && Number.isFinite(Number(p.lng));
   if (!validPoint(schoolPoint) && !validPoint(universityPoint)) {
    return res.status(400).json({ success: false, error: 'At least one valid point is required' });
   }

   const db = readDestinationsAdvanced();
   let existing = (db.submissions || []).find(x => String(x.studentName || '').trim().toLowerCase() === studentName.toLowerCase());

   const payload = {
    studentName,
    section,
    ranking,
    schoolPlaceName,
    universityPlaceName,
    schoolPoint: validPoint(schoolPoint) ? { lat: Number(schoolPoint.lat), lng: Number(schoolPoint.lng) } : null,
    universityPoint: validPoint(universityPoint) ? { lat: Number(universityPoint.lat), lng: Number(universityPoint.lng) } : null,
    updatedAt: nowIso()
   };

   if (existing) {
    Object.assign(existing, payload);
   } else {
    db.submissions.push({
     id: db.nextId++,
     createdAt: nowIso(),
     ...payload
    });
   }

   if (db.submissions.length > 5000) {
    db.submissions = db.submissions.slice(-5000);
   }

   writeDestinationsAdvanced(db);
   broadcast('destinations:pin-update', { studentName, section });
   res.json({ success: true });
  } catch (e) {
   res.status(500).json({ success: false, error: e.message });
  }
 });

 app.get('/api/destinations/pin-submissions', (req, res) => {
  try {
   const db = readDestinationsAdvanced();
   res.json({ success: true, submissions: db.submissions || [] });
  } catch (e) {
   res.status(500).json({ success: false, error: e.message });
  }
 });

 console.log('Production globe and music patch loaded.');
})();
// === PRODUCTION_GLOBE_AND_MUSIC_PATCH_END ===
""".strip()


def patch_server() -> None:
    text = clean_text(SERVER_JS.read_text(encoding="utf-8", errors="ignore"))

    if "PRODUCTION_GLOBE_AND_MUSIC_PATCH_START" not in text:
        text = text.replace("server.listen(PORT, '0.0.0.0', () => {", SERVER_APPEND + "\nserver.listen(PORT, '0.0.0.0', () => {")

    SERVER_JS.write_text(text, encoding="utf-8")


def main() -> None:
    if not INDEX_HTML.exists():
        raise FileNotFoundError("index.html not found")
    if not SERVER_JS.exists():
        raise FileNotFoundError("server.js not found")

    patch_html()
    patch_server()
    sys.stdout.write("Production-grade globe, footer order, stereo deck, admin place editing, and music upload patch applied successfully.\n")


if __name__ == "__main__":
    main()