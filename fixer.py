#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime
import shutil

ENC = "utf-8"


def read_text(p: Path) -> str:
    return p.read_text(encoding=ENC, errors="replace")


def write_text(p: Path, s: str) -> None:
    p.write_text(s, encoding=ENC, newline="\n")


def backup_file(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = p.parent / "_backups"
    bdir.mkdir(parents=True, exist_ok=True)
    bp = bdir / f"{p.stem}.backup_{ts}{p.suffix}"
    shutil.copy2(p, bp)
    return bp


FUN_FEATURES_BLOCK = r"""
// ═══════════════════════════════════════════════════════════════════════════════
// FUN FEATURES API
// ═══════════════════════════════════════════════════════════════════════════════
(() => {
  if (global.__FUN_FEATURES_PATCH__) return;
  global.__FUN_FEATURES_PATCH__ = true;

  const funDir = path.join(databaseDir, 'fun');
  if (!fs.existsSync(funDir)) fs.mkdirSync(funDir, { recursive: true });

  const ffPaths = {
    gratitude:    path.join(funDir, 'gratitude.json'),
    superlatives: path.join(funDir, 'superlatives.json'),
    wishes:       path.join(funDir, 'wishes.json'),
    dedications:  path.join(funDir, 'dedications.json'),
    mood:         path.join(funDir, 'mood.json'),
    capsules:     path.join(funDir, 'capsules.json'),
    settings:     path.join(funDir, 'ff_settings.json'),
  };

  const ffDefaults = {
    gratitude:    { entries: [], nextId: 1 },
    superlatives: { categories: [], nextId: 1 },
    wishes:       { entries: [], nextId: 1 },
    dedications:  { entries: [], nextId: 1 },
    mood:         { votes: [], options: ['Excited','Happy','Nostalgic','Bittersweet','Emotional'] },
    capsules:     { entries: [], nextId: 1 },
    settings:     { enabled: { gratitude:true, superlatives:true, wishes:true, dedications:true, mood:true, capsules:true } },
  };

  Object.entries(ffPaths).forEach(([k, p]) => {
    if (!fs.existsSync(p)) safeWriteJson(p, ffDefaults[k]);
  });

  function ffRead(key) { return safeReadJson(ffPaths[key], ffDefaults[key]); }
  function ffWrite(key, d) { safeWriteJson(ffPaths[key], d); }

  // Settings
  app.get('/api/fun/settings', (req, res) => {
    res.json({ success: true, settings: ffRead('settings') });
  });

  app.post('/api/fun/settings', (req, res) => {
    const auth = requireAdmin(req, res); if (!auth) return;
    const s = ffRead('settings');
    if (req.body?.enabled && typeof req.body.enabled === 'object') {
      s.enabled = { ...s.enabled, ...req.body.enabled };
    }
    ffWrite('settings', s);
    broadcast('ff:settings', s.enabled);
    res.json({ success: true, settings: s });
  });

  // Gratitude
  app.get('/api/fun/gratitude', (req, res) => {
    const db = ffRead('gratitude');
    res.json({ success: true, entries: db.entries });
  });

  app.post('/api/fun/gratitude', (req, res) => {
    const { from, to, message } = req.body || {};
    if (!from?.trim() || !to?.trim() || !message?.trim()) {
      return res.status(400).json({ success: false, error: 'from, to, and message are required' });
    }
    const db = ffRead('gratitude');
    const entry = {
      id: db.nextId++,
      from: from.trim().substring(0,60),
      to: to.trim().substring(0,60),
      message: message.trim().substring(0,400),
      createdAt: nowIso()
    };
    db.entries.push(entry);
    ffWrite('gratitude', db);
    broadcast('ff:gratitude:new', { id: entry.id });
    res.json({ success: true, entry });
  });

  app.delete('/api/fun/gratitude/:id', (req, res) => {
    const auth = requireAdmin(req, res); if (!auth) return;
    const db = ffRead('gratitude');
    const idx = db.entries.findIndex(e => e.id === Number(req.params.id));
    if (idx === -1) return res.status(404).json({ success: false, error: 'Not found' });
    db.entries.splice(idx, 1);
    ffWrite('gratitude', db);
    res.json({ success: true });
  });

  // Superlatives
  app.get('/api/fun/superlatives', (req, res) => {
    res.json({ success: true, categories: ffRead('superlatives').categories });
  });

  app.post('/api/fun/superlatives', (req, res) => {
    const auth = requireAdmin(req, res); if (!auth) return;
    const { categories } = req.body || {};
    if (!Array.isArray(categories)) {
      return res.status(400).json({ success: false, error: 'categories array required' });
    }
    const db = ffRead('superlatives');
    db.categories = categories.map(c => ({
      id: c.id || db.nextId++,
      title: String(c.title || '').trim().substring(0,100),
      nominees: Array.isArray(c.nominees)
        ? c.nominees.map(n => ({
            name: String(n.name || '').trim().substring(0,60),
            votes: Number(n.votes) || 0,
            imageUrl: n.imageUrl || null
          }))
        : [],
      imageUrl: c.imageUrl || null
    }));
    ffWrite('superlatives', db);
    res.json({ success: true, categories: db.categories });
  });

  app.post('/api/fun/superlatives/nominee', (req, res) => {
    const { categoryId, name } = req.body || {};
    if (!name?.trim()) return res.status(400).json({ success: false, error: 'name required' });
    const db = ffRead('superlatives');
    const cat = db.categories.find(c => c.id === Number(categoryId));
    if (!cat) return res.status(404).json({ success: false, error: 'Category not found' });

    if (!cat.nominees.find(n => n.name.toLowerCase() === name.trim().toLowerCase())) {
      cat.nominees.push({ name: name.trim().substring(0,60), votes: 0, imageUrl: null });
      ffWrite('superlatives', db);
    }
    res.json({ success: true, categories: db.categories });
  });

  app.post('/api/fun/superlatives/vote', (req, res) => {
    const { categoryId, nomineeName } = req.body || {};
    const db = ffRead('superlatives');
    const cat = db.categories.find(c => c.id === Number(categoryId));
    if (!cat) return res.status(404).json({ success: false, error: 'Category not found' });
    const nom = cat.nominees.find(n => n.name === nomineeName);
    if (!nom) return res.status(404).json({ success: false, error: 'Nominee not found' });

    nom.votes++;
    ffWrite('superlatives', db);
    broadcast('ff:superlatives:vote', { categoryId, nomineeName });
    res.json({ success: true });
  });

  app.post('/api/fun/superlatives/upload-image', upload.single('image'), (req, res) => {
    try {
      const auth = requireAdmin(req, res); if (!auth) return;
      const file = req.file;
      if (!file) return res.status(400).json({ success: false, error: 'No image file' });

      const { categoryId, nomineeName } = req.body || {};
      const db = ffRead('superlatives');
      const cat = db.categories.find(c => c.id === Number(categoryId));
      if (!cat) return res.status(404).json({ success: false, error: 'Category not found' });

      const imageUrl = `/uploads/${file.filename}`;
      if (nomineeName) {
        const nom = cat.nominees.find(n => n.name === nomineeName);
        if (nom) nom.imageUrl = imageUrl;
      } else {
        cat.imageUrl = imageUrl;
      }

      ffWrite('superlatives', db);
      res.json({ success: true, imageUrl });
    } catch (e) {
      res.status(500).json({ success: false, error: e.message });
    }
  });

  // Wishes
  app.get('/api/fun/wishes', (req, res) => {
    res.json({ success: true, entries: ffRead('wishes').entries });
  });

  app.post('/api/fun/wishes', (req, res) => {
    const { name, category, text } = req.body || {};
    if (!name?.trim() || !text?.trim()) {
      return res.status(400).json({ success: false, error: 'name and text required' });
    }
    const db = ffRead('wishes');
    const entry = {
      id: db.nextId++,
      name: name.trim().substring(0,60),
      category: String(category || 'General').trim().substring(0,40),
      text: text.trim().substring(0,500),
      createdAt: nowIso()
    };
    db.entries.push(entry);
    ffWrite('wishes', db);
    broadcast('ff:wish:new', { id: entry.id });
    res.json({ success: true, entry });
  });

  app.delete('/api/fun/wishes/:id', (req, res) => {
    const auth = requireAdmin(req, res); if (!auth) return;
    const db = ffRead('wishes');
    const idx = db.entries.findIndex(e => e.id === Number(req.params.id));
    if (idx === -1) return res.status(404).json({ success: false, error: 'Not found' });
    db.entries.splice(idx, 1);
    ffWrite('wishes', db);
    res.json({ success: true });
  });

  // Dedications
  app.get('/api/fun/dedications', (req, res) => {
    res.json({ success: true, entries: ffRead('dedications').entries });
  });

  app.post('/api/fun/dedications', (req, res) => {
    const { from, to, song, message } = req.body || {};
    if (!from?.trim() || !to?.trim() || !song?.trim()) {
      return res.status(400).json({ success: false, error: 'from, to, and song required' });
    }
    const db = ffRead('dedications');
    const entry = {
      id: db.nextId++,
      from: from.trim().substring(0,60),
      to: to.trim().substring(0,60),
      song: song.trim().substring(0,100),
      message: (message || '').trim().substring(0,400),
      createdAt: nowIso()
    };
    db.entries.push(entry);
    ffWrite('dedications', db);
    broadcast('ff:dedication:new', { id: entry.id });
    res.json({ success: true, entry });
  });

  app.delete('/api/fun/dedications/:id', (req, res) => {
    const auth = requireAdmin(req, res); if (!auth) return;
    const db = ffRead('dedications');
    const idx = db.entries.findIndex(e => e.id === Number(req.params.id));
    if (idx === -1) return res.status(404).json({ success: false, error: 'Not found' });
    db.entries.splice(idx, 1);
    ffWrite('dedications', db);
    res.json({ success: true });
  });

  // Mood
  app.get('/api/fun/mood', (req, res) => {
    const db = ffRead('mood');
    const counts = {};
    (db.options || []).forEach(o => counts[o] = 0);
    (db.votes || []).forEach(v => {
      if (counts[v.mood] !== undefined) counts[v.mood]++;
    });
    res.json({ success: true, votes: db.votes, options: db.options, counts });
  });

  app.post('/api/fun/mood', (req, res) => {
    const { name, mood } = req.body || {};
    if (!mood?.trim()) return res.status(400).json({ success: false, error: 'mood required' });

    const db = ffRead('mood');
    db.votes.push({
      name: (name || 'Anonymous').trim().substring(0,60),
      mood: mood.trim().substring(0,40),
      createdAt: nowIso()
    });
    if (db.votes.length > 5000) db.votes = db.votes.slice(-5000);
    ffWrite('mood', db);
    broadcast('ff:mood:new', {});
    res.json({ success: true });
  });

  app.delete('/api/fun/mood/:idx', (req, res) => {
    const auth = requireAdmin(req, res); if (!auth) return;
    const db = ffRead('mood');
    const idx = Number(req.params.idx);
    if (idx < 0 || idx >= db.votes.length) return res.status(404).json({ success: false, error: 'Not found' });
    db.votes.splice(idx, 1);
    ffWrite('mood', db);
    res.json({ success: true });
  });

  // Capsules
  app.get('/api/fun/capsules', (req, res) => {
    const db = ffRead('capsules');
    const now = new Date();
    const safe = db.entries.map(e => ({
      id: e.id,
      name: e.name,
      revealDate: e.revealDate,
      createdAt: e.createdAt,
      revealed: new Date(e.revealDate) <= now,
      letter: new Date(e.revealDate) <= now ? e.letter : null
    }));
    res.json({ success: true, entries: safe });
  });

  app.post('/api/fun/capsules', (req, res) => {
    const { name, revealDate, letter } = req.body || {};
    if (!name?.trim() || !letter?.trim() || !revealDate) {
      return res.status(400).json({ success: false, error: 'name, revealDate, and letter required' });
    }
    const db = ffRead('capsules');
    const entry = {
      id: db.nextId++,
      name: name.trim().substring(0,60),
      revealDate,
      letter: letter.trim().substring(0,2000),
      createdAt: nowIso()
    };
    db.entries.push(entry);
    ffWrite('capsules', db);
    res.json({
      success: true,
      entry: {
        id: entry.id,
        name: entry.name,
        revealDate: entry.revealDate,
        createdAt: entry.createdAt
      }
    });
  });

  app.delete('/api/fun/capsules/:id', (req, res) => {
    const auth = requireAdmin(req, res); if (!auth) return;
    const db = ffRead('capsules');
    const idx = db.entries.findIndex(e => e.id === Number(req.params.id));
    if (idx === -1) return res.status(404).json({ success: false, error: 'Not found' });
    db.entries.splice(idx, 1);
    ffWrite('capsules', db);
    res.json({ success: true });
  });

  // Admin export
  app.get('/api/admin/fun/export/:feature', (req, res) => {
    const auth = requireAdmin(req, res); if (!auth) return;
    if (!hasPerm(auth.user, 'export')) return res.status(403).json({ success: false, error: 'Forbidden' });

    const feature = req.params.feature;
    if (!['gratitude', 'wishes', 'dedications', 'capsules', 'mood'].includes(feature)) {
      return res.status(400).json({ success: false, error: 'Invalid feature' });
    }

    const db = ffRead(feature);
    const items = db.entries || db.votes || [];

    if (!items.length) {
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', `attachment; filename="${feature}-export.csv"`);
      return res.send('No data\n');
    }

    const header = Object.keys(items[0]);
    const lines = [
      header.join(','),
      ...items.map(r => header.map(h => `"${sanitizeCsvCell(r[h])}"`).join(','))
    ];

    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', `attachment; filename="${feature}-export-${new Date().toISOString().slice(0,10)}.csv"`);
    res.send(lines.join('\n'));
  });

  console.log('✅ Fun Features API loaded.');
})();
"""

SERVER_END_BLOCK = r"""
server.listen(PORT, '0.0.0.0', () => {
  console.log('');
  console.log('═══════════════════════════════════════════════════════════════════');
  console.log('🎓 CORNERSTONE INTERNATIONAL SCHOOL - FAREWELL 2025');
  console.log('═══════════════════════════════════════════════════════════════════');
  console.log(`🚀 Server running on: http://localhost:${PORT}`);
  console.log(`🌐 Network access: http://0.0.0.0:${PORT}`);
  console.log(`📁 Uploads folder: ${uploadsDir}`);
  console.log(`💾 Memories DB: ${dbPath}`);
  console.log(`⚙️ Settings DB: ${settingsPath}`);
  console.log(`🔐 Admin DB: ${adminPath}`);
  console.log(`💬 Comments DB: ${commentsPath}`);
  console.log(`😊 Reactions DB: ${reactionsPath}`);
  console.log(`🧾 Audit DB: ${auditPath}`);
  console.log(`📊 Max upload size: ${MAX_TOTAL_SIZE / 1024 / 1024}MB total`);
  console.log('═══════════════════════════════════════════════════════════════════');
  console.log('');
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('🛑 SIGTERM received. Closing server...');
  process.exit(0);
});
process.on('SIGINT', () => {
  console.log('🛑 SIGINT received. Closing server...');
  process.exit(0);
});
"""


def remove_broken_tail(text: str) -> str:
    marker = "// ═══════════════════════════════════════════════════════════════════════════════\n// FUN FEATURES API"
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError("Could not find broken tail marker for FUN FEATURES API.")
    return text[:idx].rstrip() + "\n\n"


def patch_text(text: str) -> str:
    # remove everything from broken fun-features tail onward
    head = remove_broken_tail(text)
    return head + FUN_FEATURES_BLOCK + "\n\n" + SERVER_END_BLOCK


def main():
    ap = argparse.ArgumentParser(description="Perfect sniper repair for broken server.js")
    ap.add_argument("--input", type=Path, required=True, help="Broken current server.js")
    ap.add_argument("--output", type=Path, help="Write repaired output here")
    ap.add_argument("--in-place", action="store_true", help="Patch file in place")
    args = ap.parse_args()

    if args.output and args.in_place:
        raise SystemExit("Use either --output or --in-place, not both.")
    if not args.output and not args.in_place:
        raise SystemExit("Use --output or --in-place.")

    src = args.input
    raw = read_text(src)
    repaired = patch_text(raw)

    if args.in_place:
        bp = backup_file(src)
        print(f"[backup] {src} -> {bp}")
        write_text(src, repaired)
        print(f"[done] repaired in-place: {src}")
    else:
        write_text(args.output, repaired)
        print(f"[done] wrote repaired file: {args.output}")


if __name__ == "__main__":
    main()