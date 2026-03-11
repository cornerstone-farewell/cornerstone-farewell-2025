#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path.cwd()
INDEX = ROOT / "index.html"
SERVER = ROOT / "server.js"


def fail(message: str) -> None:
    print(json.dumps({"success": False, "error": message}), file=sys.stderr)
    sys.exit(1)


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        fail(f"Could not read {path.name}: {exc}")


def write(path: Path, content: str) -> None:
    try:
        path.write_text(content, encoding="utf-8", newline="\n")
    except Exception as exc:
        fail(f"Could not write {path.name}: {exc}")


def backup(path: Path) -> str:
    bak = path.with_suffix(path.suffix + ".advice_patch.bak")
    if not bak.exists():
        write(bak, read(path))
    return bak.name


def replace_function(text: str, name: str, replacement: str) -> str:
    pattern = re.compile(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", re.S)
    m = pattern.search(text)
    if not m:
        return text
    start = m.start()
    brace = text.find("{", m.start())
    depth = 0
    end = None
    for i in range(brace, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        return text
    return text[:start] + replacement + text[end:]


def ensure_after(text: str, anchor: str, block: str) -> str:
    if block.strip() in text:
        return text
    pos = text.find(anchor)
    if pos == -1:
        return text
    pos += len(anchor)
    return text[:pos] + block + text[pos:]


def patch_index(text: str) -> tuple[str, list[str]]:
    changes: list[str] = []
    out = text.replace("\r\n", "\n")

    if '<li><a href="#adviceWall">Senior Advice</a></li>' not in out:
        old = '<li><a href="#compilations">Compilations</a></li>\n <li><a href="#upload" class="nav-cta">Upload Memory</a></li>'
        new = '<li><a href="#compilations">Compilations</a></li>\n <li><a href="#adviceWall">Senior Advice</a></li>\n <li><a href="#upload" class="nav-cta">Upload Memory</a></li>'
        if old in out:
            out = out.replace(old, new, 1)
            changes.append("Added Senior Advice to navbar")

    if 'id="viewAllMemoriesBtn"' not in out:
        target = '<div class="load-more-wrap" id="loadMoreWrap" style="display:none;">'
        if target in out:
            out = out.replace(
                target,
                '<div class="memories-preview-actions"><button class="btn btn-secondary" id="viewAllMemoriesBtn" type="button">View All Memories</button></div>\n ' + target,
                1,
            )
            changes.append("Added View All Memories button")

    if 'id="memoriesPage"' not in out:
        marker = "</section>\n <!-- Teachers / Timeline / Quote / Footer kept from previous version (rendered from settings) -->"
        page_block = """</section>
<section id="memoriesPage" class="memories-page hidden">
 <div class="memories-page-header">
  <div>
   <span class="section-badge">Memory Archive</span>
   <h2 class="section-title">All <span class="highlight">Memories</span></h2>
   <p class="section-description" style="margin:0;">A dedicated page with only memories in a clean full view.</p>
  </div>
  <button class="btn btn-secondary" id="backToHomeFromMemoriesPage" type="button">Back to Home</button>
 </div>
 <div class="container">
  <div class="memory-grid" id="memoryGridPage"></div>
  <div class="load-more-wrap" id="loadMoreWrapPage" style="display:none;">
   <button class="btn btn-secondary load-more-btn" id="loadMoreBtnPage" type="button">Load More</button>
  </div>
 </div>
</section>
 <!-- Teachers / Timeline / Quote / Footer kept from previous version (rendered from settings) -->"""
        if marker in out:
            out = out.replace(marker, page_block, 1)
            changes.append("Added dedicated full memories page")

    if 'id="adviceWall"' not in out:
        advice_block = """
<section id="adviceWall" class="ff-section-hidden">
 <div class="container">
  <div class="section-header">
   <span class="section-badge">Wisdom Corner</span>
   <h2 class="section-title">Senior <span class="highlight">Advice</span> to Juniors</h2>
   <p class="section-description">Leave practical, heartfelt, or funny advice for the juniors who will follow after you.</p>
  </div>
  <div class="ff-form-box">
   <div class="ff-grid-2">
    <div><label class="ff-label">Your Name</label><input class="ff-input" id="adviceName" placeholder="Your name" maxlength="60"/></div>
    <div><label class="ff-label">For</label><input class="ff-input" id="adviceFor" placeholder="Juniors / 9th / 10th / everyone" maxlength="80"/></div>
   </div>
   <label class="ff-label">Advice</label>
   <textarea class="ff-input" id="adviceText" placeholder="What should juniors know, avoid, enjoy, or remember?" maxlength="700"></textarea>
   <button class="ff-submit-btn" type="button" onclick="submitSeniorAdvice()">Share Advice</button>
  </div>
  <div class="dedications-list" id="adviceList"><div class="ff-empty">No advice yet. Be the first senior voice here.</div></div>
 </div>
</section>
"""
        insert_after = "</section>\n<!-- MEMORY MOSAIC -->"
        if insert_after in out:
            out = out.replace(insert_after, advice_block + "\n<!-- MEMORY MOSAIC -->", 1)
            changes.append("Added Senior Advice section")

    if "const FF_DEFAULTS={gratitudeWall:true,superlatives:true,wishJar:true,songDedications:true,moodBoard:true,timeCapsule:true,memoryMosaic:false};" in out:
        out = out.replace(
            "const FF_DEFAULTS={gratitudeWall:true,superlatives:true,wishJar:true,songDedications:true,moodBoard:true,timeCapsule:true,memoryMosaic:false};",
            "const FF_DEFAULTS={gratitudeWall:true,superlatives:true,wishJar:true,songDedications:true,moodBoard:true,timeCapsule:true,seniorAdvice:true,memoryMosaic:false};",
            1,
        )
        changes.append("Enabled Senior Advice in fun feature defaults")

    if "seniorAdvice:'adviceWall'" not in out and "const map={gratitudeWall:'gratitudeWall'" in out:
        out = out.replace(
            "const map={gratitudeWall:'gratitudeWall',superlatives:'superlativesSection',wishJar:'wishJarSection',songDedications:'songDedicationsSection',moodBoard:'moodBoardSection',timeCapsule:'timeCapsuleSection',memoryMosaic:'memoryMosaicSection'};",
            "const map={gratitudeWall:'gratitudeWall',superlatives:'superlativesSection',wishJar:'wishJarSection',songDedications:'songDedicationsSection',moodBoard:'moodBoardSection',timeCapsule:'timeCapsuleSection',seniorAdvice:'adviceWall',memoryMosaic:'memoryMosaicSection'};",
            1,
        )

    if "function loadSeniorAdvice()" not in out and "function loadMemoryMosaic()" in out:
        inject = """
 async function loadSeniorAdvice(){
  const list=document.getElementById('adviceList');if(!list)return;
  try{
   const d=await ffGet('/api/fun/advice');
   const entries=d.entries||d.advice||[];
   if(entries.length){
    list.innerHTML=entries.map(a=>`<div class="dedication-card"><div class="dedication-content"><div class="dedication-song">${ffEsc(a.name||'Anonymous')}</div><div class="dedication-msg">${ffEsc(a.text||a.advice||'')}</div><div class="dedication-meta">For <strong>${ffEsc(a.for||a.target||'Everyone')}</strong> · ${ffAgo(a.createdAt||a.created_at)}</div></div></div>`).join('');
   }else{
    list.innerHTML='<div class="ff-empty">No advice yet. Be the first senior voice here.</div>';
   }
  }catch(_){
   list.innerHTML='<div class="ff-empty">Could not load advice right now.</div>';
  }
 }
 window.submitSeniorAdvice=async function(){
  const name=document.getElementById('adviceName')?.value?.trim();
  const target=document.getElementById('adviceFor')?.value?.trim()||'Everyone';
  const text=document.getElementById('adviceText')?.value?.trim();
  if(!name)return ffNotify('error','Missing','Enter your name.');
  if(!text)return ffNotify('error','Missing','Write some advice first.');
  try{
   const d=await ffPost('/api/fun/advice',{name,for:target,text});
   if(d.success){
    document.getElementById('adviceName').value='';
    document.getElementById('adviceFor').value='';
    document.getElementById('adviceText').value='';
    ffNotify('success','Shared','Your advice is now visible to juniors.');
    loadSeniorAdvice();
   }else ffNotify('error','Failed',d.error||'Could not save advice.');
  }catch(e){ffNotify('error','Error',e.message)}
 };
"""
        out = out.replace(" function loadMemoryMosaic(){", inject + "\n function loadMemoryMosaic(){", 1)
        changes.append("Added Senior Advice frontend logic")

    if "loadGratitudeNotes();loadSuperlatives();loadWishes();loadDedications();loadMoodBoard();loadTimeCapsules();" in out:
        out = out.replace(
            "loadGratitudeNotes();loadSuperlatives();loadWishes();loadDedications();loadMoodBoard();loadTimeCapsules();",
            "loadGratitudeNotes();loadSuperlatives();loadWishes();loadDedications();loadMoodBoard();loadTimeCapsules();loadSeniorAdvice();",
            1,
        )

    if "name:' Senior Advice'" not in out and "const features=[{key:'gratitudeWall'" in out:
        out = out.replace(
            "const features=[{key:'gratitudeWall',name:' Gratitude Wall',desc:'Students post sticky note thank-you messages'},{key:'superlatives',name:' Class Superlatives',desc:'Students nominate and vote for classmates'},{key:'wishJar',name:' Wish Jar',desc:'Students drop dreams, hopes and advice'},{key:'songDedications',name:' Song Dedications',desc:'Students dedicate songs to friends'},{key:'moodBoard',name:' Mood Board',desc:'Students vote on how they feel about Farewell'},{key:'timeCapsule',name:' Time Capsule',desc:'Students write sealed letters to their future selves'},{key:'memoryMosaic',name:' Memory Mosaic',desc:'Auto leaderboard of top memory contributors'}];",
            "const features=[{key:'gratitudeWall',name:' Gratitude Wall',desc:'Students post sticky note thank-you messages'},{key:'superlatives',name:' Class Superlatives',desc:'Students nominate and vote for classmates'},{key:'wishJar',name:' Wish Jar',desc:'Students drop dreams, hopes and advice'},{key:'songDedications',name:' Song Dedications',desc:'Students dedicate songs to friends'},{key:'moodBoard',name:' Mood Board',desc:'Students vote on how they feel about Farewell'},{key:'timeCapsule',name:' Time Capsule',desc:'Students write sealed letters to their future selves'},{key:'seniorAdvice',name:' Senior Advice',desc:'Seniors leave meaningful advice for juniors'},{key:'memoryMosaic',name:' Memory Mosaic',desc:'Auto leaderboard of top memory contributors'}];",
            1,
        )

    out = out.replace(
        "window.enableAllFunFeatures=function(){['gratitudeWall','superlatives','wishJar','songDedications','moodBoard','timeCapsule','memoryMosaic'].forEach(k=>{const el=document.getElementById(`ffToggle_${k}`);if(el)el.checked=(k!=='memoryMosaic');window.previewFunFeatureToggle(k,k!=='memoryMosaic')})};",
        "window.enableAllFunFeatures=function(){['gratitudeWall','superlatives','wishJar','songDedications','moodBoard','timeCapsule','seniorAdvice','memoryMosaic'].forEach(k=>{const el=document.getElementById(`ffToggle_${k}`);if(el)el.checked=(k!=='memoryMosaic');window.previewFunFeatureToggle(k,k!=='memoryMosaic')})};",
    )
    out = out.replace(
        "window.disableAllFunFeatures=function(){['gratitudeWall','superlatives','wishJar','songDedications','moodBoard','timeCapsule','memoryMosaic'].forEach(k=>{const el=document.getElementById(`ffToggle_${k}`);if(el)el.checked=false;window.previewFunFeatureToggle(k,false)})};",
        "window.disableAllFunFeatures=function(){['gratitudeWall','superlatives','wishJar','songDedications','moodBoard','timeCapsule','seniorAdvice','memoryMosaic'].forEach(k=>{const el=document.getElementById(`ffToggle_${k}`);if(el)el.checked=false;window.previewFunFeatureToggle(k,false)})};",
    )

    if '<li><a href="#adviceWall">Senior Advice</a></li>' not in out and '<li><a href="#teachers">Teachers</a></li>' in out:
        out = out.replace(
            '<li><a href="#teachers">Teachers</a></li>',
            '<li><a href="#teachers">Teachers</a></li>\n <li><a href="#adviceWall">Senior Advice</a></li>',
            1,
        )

    if 'quoteText: "\\"Don\'t cry because it\'s over, smile because it happened.\\"",' in out:
        out = out.replace(
            'quoteText: "\\"Don\'t cry because it\'s over, smile because it happened.\\"",',
            'quoteText: "\\"Don\'t cry because it\'s over, smile because it happened.\\"",',
        )

    if 'id="setQuoteText" maxlength="500"' in out:
        out = out.replace('id="setQuoteText" maxlength="500"', 'id="setQuoteText" maxlength="7000"')
        changes.append("Expanded admin quote editor limit")

    return out, changes


def patch_server(text: str) -> tuple[str, list[str]]:
    changes: list[str] = []
    out = text.replace("\r\n", "\n")

    if "const advicePath = path.join(funDir, 'advice.json');" not in out and "const ffPaths = {" in out:
        out = out.replace(
            "const ffPaths = {\n gratitude: path.join(funDir, 'gratitude.json'),",
            "const ffPaths = {\n advice: path.join(funDir, 'advice.json'),\n gratitude: path.join(funDir, 'gratitude.json'),",
            1,
        )
        changes.append("Added Senior Advice storage path")

    if "advice: { entries: [], nextId: 1 }," not in out and "const ffDefaults = {" in out:
        out = out.replace(
            "const ffDefaults = {\n gratitude: { entries: [], nextId: 1 },",
            "const ffDefaults = {\n advice: { entries: [], nextId: 1 },\n gratitude: { entries: [], nextId: 1 },",
            1,
        )

    if "seniorAdvice:true" not in out and "settings: { enabled:" in out:
        out = out.replace(
            "settings: { enabled: { gratitude:true, superlatives:true, wishes:true, dedications:true, mood:true, capsules:true } },",
            "settings: { enabled: { gratitude:true, superlatives:true, wishes:true, dedications:true, mood:true, capsules:true, seniorAdvice:true } },",
            1,
        )

    if "app.get('/api/fun/advice'" not in out and "console.log(' Fun Features API loaded.');" in out:
        advice_routes = """
 app.get('/api/fun/advice', (req, res) => {
  res.json({ success: true, entries: ffRead('advice').entries });
 });
 app.post('/api/fun/advice', (req, res) => {
  const { name, text } = req.body || {};
  const target = req.body?.for || req.body?.target || 'Everyone';
  if (!name?.trim() || !text?.trim()) return res.status(400).json({ success: false, error: 'name and text required' });
  const db = ffRead('advice');
  const entry = { id: db.nextId++, name: name.trim().substring(0,60), for: String(target).trim().substring(0,80), text: text.trim().substring(0,700), createdAt: nowIso() };
  db.entries.push(entry);
  ffWrite('advice', db);
  broadcast('ff:advice:new', { id: entry.id });
  res.json({ success: true, entry });
 });
 app.delete('/api/fun/advice/:id', (req, res) => {
  const auth = requireAdmin(req, res); if (!auth) return;
  const db = ffRead('advice');
  const idx = db.entries.findIndex(e => e.id === Number(req.params.id));
  if (idx === -1) return res.status(404).json({ success: false, error: 'Not found' });
  db.entries.splice(idx, 1);
  ffWrite('advice', db);
  res.json({ success: true });
 });
"""
        out = out.replace(" console.log(' Fun Features API loaded.');", advice_routes + " console.log(' Fun Features API loaded.');", 1)
        changes.append("Added Senior Advice API routes")

    if "caption: caption.trim().substring(0, 500)," in out:
        out = out.replace("caption: caption.trim().substring(0, 500),", "caption: caption.trim().substring(0, 1000),")
        changes.append("Expanded memory caption limit to 1000")

    if "m.caption = caption.trim().substring(0, 500);" in out:
        out = out.replace("m.caption = caption.trim().substring(0, 500);", "m.caption = caption.trim().substring(0, 1000);")

    if "student_directory.json" not in out:
        pass

    return out, changes


def main() -> None:
    if not INDEX.exists():
        fail("index.html not found")
    if not SERVER.exists():
        fail("server.js not found")

    old_index = read(INDEX)
    old_server = read(SERVER)

    new_index, index_changes = patch_index(old_index)
    new_server, server_changes = patch_server(old_server)

    modified = []
    backups = []

    if new_index != old_index:
        backups.append(backup(INDEX))
        write(INDEX, new_index)
        modified.append("index.html")

    if new_server != old_server:
        backups.append(backup(SERVER))
        write(SERVER, new_server)
        modified.append("server.js")

    print(json.dumps({
        "success": True,
        "modified": modified,
        "backups": backups,
        "changes": index_changes + server_changes
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()