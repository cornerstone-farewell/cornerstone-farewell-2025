#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


INDEX_HTML = Path("index.html")
SERVER_JS = Path("server.js")


NEW_DISTANCE_SECTION = """<section id="distanceMapSection">
 <div class="container">
 <div class="section-header">
 <span class="section-badge">Erase the Distance</span>
 <h2 class="section-title">One <span class="highlight">Starting Point</span>, Many Destinations</h2>
 <p class="section-description">No matter where everyone goes next, it all began here.</p>
 </div>
 <div id="distanceControls" style="max-width: 1000px; margin: 0 auto; display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; align-items:end;">
 <div class="form-group" style="margin-bottom:0;">
 <label>Your Name</label>
 <input class="form-input" id="distanceStudentName" placeholder="Enter your name" maxlength="80" />
 </div>
 <div class="form-group" style="margin-bottom:0;">
 <label>Future place for 11th / 12th</label>
 <select class="form-select" id="destinationSelectSchool">
 <option value="">Choose a place</option>
 </select>
 </div>
 <div class="form-group" style="margin-bottom:0;">
 <label>Your university dream place</label>
 <select class="form-select" id="destinationSelectUniversity">
 <option value="">Choose a place</option>
 </select>
 </div>
 <div class="form-group" style="margin-bottom:0;">
 <label>Selected Coordinates</label>
 <input class="form-input" id="selectedCoords" placeholder="Will fill automatically after place selection" readonly />
 </div>
 <div style="grid-column: 1 / -1; display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin-top:4px;">
 <button class="btn btn-primary" type="button" id="destinationLaunchBtn">Select Place</button>
 <button class="btn btn-secondary" type="button" id="destinationSaveBtn">Save Future Path</button>
 </div>
 </div>
 <div id="distanceMapWrap" style="min-height: 120px; border-radius:24px; margin-top:20px; border:1px solid rgba(255,255,255,.08); background:rgba(255,255,255,.04); display:flex; align-items:center; justify-content:center; padding:24px;">
 <div id="distanceSelectionStatus" style="color: var(--text-muted); text-align:center;">
 Pick a place, open the selector, and the coordinates will fill in automatically.
 </div>
 </div>
 </div>
</section>"""

NEW_DISTANCE_SCRIPT = """
<script>
(function(){
 if (window.__DISTANCE_SELECTOR_PATCH__) return;
 window.__DISTANCE_SELECTOR_PATCH__ = true;

 let destinationCatalog = [];
 let selectedSchoolCoords = null;
 let selectedUniversityCoords = null;

 function getPlaceName(item) {
  return String(item?.place || item?.name || item || '').trim();
 }

 function getPlaceLat(item) {
  const value = item?.lat ?? item?.latitude;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
 }

 function getPlaceLng(item) {
  const value = item?.lng ?? item?.lon ?? item?.longitude;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
 }

 function setStatus(message) {
  const status = document.getElementById('distanceSelectionStatus');
  if (status) status.textContent = message;
 }

 function updateCoordsField() {
  const schoolVal = document.getElementById('destinationSelectSchool')?.value?.trim() || '';
  const uniVal = document.getElementById('destinationSelectUniversity')?.value?.trim() || '';
  const coordsInput = document.getElementById('selectedCoords');
  if (!coordsInput) return;
  const chunks = [];
  if (schoolVal && selectedSchoolCoords) {
   chunks.push(`11th/12th: ${selectedSchoolCoords.lat.toFixed(6)}, ${selectedSchoolCoords.lng.toFixed(6)}`);
  }
  if (uniVal && selectedUniversityCoords) {
   chunks.push(`University: ${selectedUniversityCoords.lat.toFixed(6)}, ${selectedUniversityCoords.lng.toFixed(6)}`);
  }
  coordsInput.value = chunks.join(' | ');
 }

 async function geocodePlace(placeName) {
  const url = 'https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=' + encodeURIComponent(placeName);
  const res = await fetch(url, {
   headers: {
    'Accept': 'application/json'
   }
  });
  const data = await res.json();
  if (!Array.isArray(data) || !data.length) {
   throw new Error('No coordinates found for ' + placeName);
  }
  const first = data[0];
  return {
   lat: Number(first.lat),
   lng: Number(first.lon),
   label: first.display_name || placeName
  };
 }

 function fillOptions(selectId, items) {
  const select = document.getElementById(selectId);
  if (!select) return;
  const options = ['<option value="">Choose a place</option>'];
  for (const item of items) {
   const name = getPlaceName(item);
   if (!name) continue;
   options.push(`<option value="${escapeAttr(name)}">${escapeHtml(name)}</option>`);
  }
  select.innerHTML = options.join('');
 }

 async function loadDestinationSelectors() {
  try {
   const res = await fetch(apiUrl('/api/destinations'));
   const data = await res.json();
   destinationCatalog = Array.isArray(data?.destinations) ? data.destinations : [];
   fillOptions('destinationSelectSchool', destinationCatalog);
   fillOptions('destinationSelectUniversity', destinationCatalog);
  } catch (e) {
   console.error('Failed to load destinations:', e);
  }
 }

 async function openPlaceSelector() {
  const schoolPlace = document.getElementById('destinationSelectSchool')?.value?.trim() || '';
  const uniPlace = document.getElementById('destinationSelectUniversity')?.value?.trim() || '';
  if (!schoolPlace && !uniPlace) {
   showNotification('error', 'Choose a place', 'Select at least one place first.');
   return;
  }

  try {
   if (schoolPlace) {
    const schoolItem = destinationCatalog.find(x => getPlaceName(x) === schoolPlace);
    const lat = getPlaceLat(schoolItem);
    const lng = getPlaceLng(schoolItem);
    selectedSchoolCoords = (lat !== null && lng !== null) ? { lat, lng, label: schoolPlace } : await geocodePlace(schoolPlace);
   }
   if (uniPlace) {
    const uniItem = destinationCatalog.find(x => getPlaceName(x) === uniPlace);
    const lat = getPlaceLat(uniItem);
    const lng = getPlaceLng(uniItem);
    selectedUniversityCoords = (lat !== null && lng !== null) ? { lat, lng, label: uniPlace } : await geocodePlace(uniPlace);
   }

   updateCoordsField();

   const target = selectedUniversityCoords || selectedSchoolCoords;
   if (target) {
    const mapsUrl = 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(target.lat + ',' + target.lng);
    window.open(mapsUrl, '_blank');
   }

   setStatus('Coordinates selected and filled automatically.');
   showNotification('success', 'Place selected', 'Coordinates filled automatically.');
  } catch (e) {
   console.error(e);
   showNotification('error', 'Place selection failed', e.message || 'Could not fetch coordinates.');
  }
 }

 async function saveFuturePath() {
  const studentName = document.getElementById('distanceStudentName')?.value?.trim() || '';
  const schoolPlace = document.getElementById('destinationSelectSchool')?.value?.trim() || '';
  const universityPlace = document.getElementById('destinationSelectUniversity')?.value?.trim() || '';

  if (!studentName) {
   showNotification('error', 'Name needed', 'Enter your name first.');
   return;
  }
  if (!schoolPlace && !universityPlace) {
   showNotification('error', 'Choose a place', 'Select at least one place.');
   return;
  }

  try {
   const payload = {
    studentName,
    schoolPlace,
    universityPlace
   };
   const res = await fetch(apiUrl('/api/destinations/submit-v2'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
   });
   const data = await res.json();
   if (!data.success) {
    showNotification('error', 'Could not save', data.error || 'Submission failed.');
    return;
   }
   setStatus('Future path saved successfully.');
   showNotification('success', 'Saved', 'Future path saved.');
  } catch (e) {
   console.error(e);
   showNotification('error', 'Could not save', e.message || 'Submission failed.');
  }
 }

 document.addEventListener('DOMContentLoaded', () => {
  loadDestinationSelectors();
  document.getElementById('destinationLaunchBtn')?.addEventListener('click', openPlaceSelector);
  document.getElementById('destinationSaveBtn')?.addEventListener('click', saveFuturePath);
 });
})();
</script>
"""


def normalize_garbage(text: str) -> str:
    return text.replace("\uFFFE", "").replace("￾", "")


def patch_index_html() -> None:
    if not INDEX_HTML.exists():
        raise FileNotFoundError("index.html not found")

    text = normalize_garbage(INDEX_HTML.read_text(encoding="utf-8", errors="ignore"))

    # Remove ghost / note buttons and modals.
    patterns_to_remove = [
        r'\s*<button class="btn btn-secondary" id="ghostCursorToggle" type="button">.*?</button>',
        r'\s*<button class="btn btn-primary" id="sendNoteBtn" type="button">.*?</button>',
        r'\s*<div id="ghostCursorPopup">.*?</div>\s*</div>',
        r'\s*<div id="ghostOffModal">.*?</div>\s*</div>',
        r'\s*<div id="paperTutorial">.*?</div>\s*</div>',
    ]
    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=re.DOTALL)

    # Remove whole sniper patch styles/scripts.
    text = re.sub(
        r'<style>\s*/\* === SNIPER_PATCH_V2_START === \*/.*?</style>\s*'
        r'<div id="sniperGlobalFx">.*?</div>\s*'
        r'<div id="leanBackOverlay">.*?</div>\s*'
        r'<div id="boomboxDock">.*?</div>',
        '',
        text,
        flags=re.DOTALL,
    )

    text = re.sub(
        r'<script>\s*/\* === SNIPER_PATCH_V2_START === \*/.*?</script>',
        '',
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'<style>\s*/\* === SNIPER_PATCH_V3_START === \*/.*?</style>',
        '',
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'<script>\s*/\* === SNIPER_PATCH_V3_START === \*/.*?</script>',
        '',
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'<style>\s*/\* === SNIPER_PATCH_V4_START === \*/.*?</style>',
        '',
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'<script>\s*/\* === SNIPER_PATCH_V4_START === \*/.*?</script>',
        '',
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'<style>\s*/\* === SNIPER_PATCH_V5_START === \*/.*?</style>\s*'
        r'<script src="https://unpkg.com/three@0\.160\.0/build/three\.min\.js"></script>\s*'
        r'<script src="https://unpkg.com/globe\.gl"></script>\s*'
        r'<script>\s*/\* === SNIPER_PATCH_V5_START === \*/.*?</script>',
        '',
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'<style>\s*/\* === SNIPER_PATCH_V6_START === \*/.*?</style>',
        '',
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'<script>\s*/\* === SNIPER_PATCH_V6_START === \*/.*?</script>',
        '',
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'<style>\s*/\* === SNIPER_PATCH_V7_START === \*/.*?</style>',
        '',
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'<script>\s*/\* === SNIPER_PATCH_V7_START === \*/.*?</script>',
        '',
        text,
        flags=re.DOTALL,
    )

    # Replace distance section.
    text = re.sub(
        r'<section id="distanceMapSection">.*?</section>',
        NEW_DISTANCE_SECTION,
        text,
        count=1,
        flags=re.DOTALL,
    )

    # Insert new distance script before </body>.
    if "__DISTANCE_SELECTOR_PATCH__" not in text:
        text = text.replace("</body>", NEW_DISTANCE_SCRIPT + "\n</body>")

    INDEX_HTML.write_text(text, encoding="utf-8")


def patch_server_js() -> None:
    if not SERVER_JS.exists():
        raise FileNotFoundError("server.js not found")

    text = normalize_garbage(SERVER_JS.read_text(encoding="utf-8", errors="ignore"))

    # Remove paper notes endpoints in v2.
    text = re.sub(
        r'// Paper notes.*?app\.get\(\'/api/paper-notes/random\'.*?\n \}\);\n',
        '',
        text,
        flags=re.DOTALL,
    )

    # Remove ghost websocket rebroadcast in v2.
    text = re.sub(
        r'// Extra WebSocket message handling for ghost cursors.*?console\.log\(\'SNIPER patch server extension loaded\.\'\);\n\}\)\(\);',
        "console.log('SNIPER patch server extension loaded.');\n})();",
        text,
        flags=re.DOTALL,
    )

    # Remove whole v3 sniper patch server block because it is only for memory notes/music helpers.
    text = re.sub(
        r'// === SNIPER_SERVER_PATCH_V3_START ===.*?console\.log\(\'SNIPER patch server v3 loaded\.\'\);\n\}\)\(\);',
        '',
        text,
        flags=re.DOTALL,
    )

    # Remove whole v5/v6/v7 sniper server patches for globe pin / ghost / paper-note broadcast extras.
    text = re.sub(
        r'// === SNIPER_SERVER_PATCH_V5_START ===.*?console\.log\(\'SNIPER patch server v5 loaded\.\'\);\n\}\)\(\);',
        '',
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'// === SNIPER_SERVER_PATCH_V6_START ===.*?console\.log\(\'SNIPER patch server v6 loaded\.\'\);\n\}\)\(\);',
        '',
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'// === SNIPER_SERVER_PATCH_V7_START ===.*?console\.log\(\'SNIPER patch server v7 loaded\.\'\);\n\}\)\(\);',
        '',
        text,
        flags=re.DOTALL,
    )

    SERVER_JS.write_text(text, encoding="utf-8")


def main() -> None:
    patch_index_html()
    patch_server_js()
    print("Patched index.html and server.js successfully.")


if __name__ == "__main__":
    main()