#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional

import tinycss2
from bs4 import BeautifulSoup
from bs4.element import Tag, Comment, NavigableString

ENC = "utf-8"
INCLUDE_RE = re.compile(r"<!--\s*@include:\s*([^\s]+)\s*-->", re.IGNORECASE)

# ---------------------------
# Output files
# ---------------------------
FRAG = {
    "navbar": "fragments/navbar.html",
    "hero": "fragments/hero.html",
    "countdown": "fragments/countdown.html",
    "upload": "fragments/upload_ur_memories.html",
    "memories": "fragments/our_memories.html",
    "compilations": "fragments/memory_compilations.html",
    "teachers": "fragments/our_beloved_teachers.html",
    "advicewall": "fragments/advicewall.html",
    "timeline": "fragments/through_the_years.html",
    "quote": "fragments/quote.html",
    "gratitude": "fragments/gratitudewall.html",
    "superlatives": "fragments/class_superlatives.html",
    "wishjar": "fragments/wishjar.html",
    "dedications": "fragments/songdedications.html",
    "mood": "fragments/howwefeel.html",
    "capsule": "fragments/timecapsule.html",
    "stereodeck": "fragments/cornerstonestereodeck.html",
    "globe": "fragments/globe.html",
    "footer": "fragments/footer.html",

    # admin
    "admin_nav_top": "fragments/admin/admin_navbar_top.html",
    "admin_moderation": "fragments/admin/moderation.html",
    "admin_sitesettings": "fragments/admin/sitesettings.html",
    "admin_theme": "fragments/admin/theme.html",
    "admin_users": "fragments/admin/users.html",
    "admin_compilations": "fragments/admin/compilations.html",
    "admin_funfeatures": "fragments/admin/funfeatures.html",
    "admin_destinations": "fragments/admin/destinations.html",
    "admin_advice": "fragments/admin/advice.html",
    "admin_papernotes": "fragments/admin/papernotes.html",
    "admin_teachers": "fragments/admin/teachers.html",
    "admin_students": "fragments/admin/students.html",
    "admin_security": "fragments/admin/security.html",
}

ORDER = [
    "navbar",
    "hero",
    "countdown",
    "upload",
    "memories",
    "compilations",
    "teachers",
    "advicewall",
    "timeline",
    "quote",
    "gratitude",
    "superlatives",
    "wishjar",
    "dedications",
    "mood",
    "capsule",
    "stereodeck",
    "globe",
    "footer",

    "admin_nav_top",
    "admin_moderation",
    "admin_sitesettings",
    "admin_theme",
    "admin_users",
    "admin_compilations",
    "admin_funfeatures",
    "admin_destinations",
    "admin_advice",
    "admin_papernotes",
    "admin_teachers",
    "admin_students",
    "admin_security",
]

# ---------------------------
# Routing keywords
# ---------------------------
CSS_KEYS: Dict[str, List[str]] = {
    "navbar": ["#navbar", ".navbar", ".nav-links", ".mobile-menu-btn", ".nav-cta", ".logo"],
    "hero": ["#home", ".hero", ".hero-bg", ".hero-content", ".intro-video", ".intro-video-overlay", ".skip-intro-btn"],
    "countdown": ["#countdown", ".countdown", ".countdown-item", "#days", "#hours", "#minutes", "#seconds"],
    "upload": ["#upload", ".upload", ".dropzone", "#file-input", ".file-preview", ".upload-progress", ".upload-card"],
    "memories": ["#memories", ".memory-", ".lightbox", "#lightbox", ".comments-", "#comment", "#commentList"],
    "compilations": ["#compilations", ".compilation-", "#compilation", ".compilations-grid", "Compilation Creator"],
    "teachers": ["#teachers", ".teacher-", ".teachers-grid"],
    "advicewall": ["#adviceWall", ".advice-", ".advice-card", ".advice-grid", ".advice-form", "#adviceForm", "#adviceGrid"],
    "timeline": ["#timeline", ".timeline", ".timeline-item", ".timeline-dot"],
    "quote": ["#quote", ".quote-"],
    "gratitude": ["#gratitudeWall", ".gratitude-", ".sticky-note", "#gwFrom", "#gwMsg"],
    "superlatives": ["#superlativesSection", ".superlative-", ".nominee-"],
    "wishjar": ["#wishJarSection", ".wish-", ".jar-", "#wishText"],
    "dedications": ["#songDedicationsSection", ".dedication-", "#dedSong"],
    "mood": ["#moodBoardSection", ".mood-", "#moodOptions", "#moodBars"],
    "capsule": ["#timeCapsuleSection", ".capsule-", "#capsuleLetter"],
    "stereodeck": ["#boomboxDock", ".boombox", ".cassette", "#ghostCursorToggle", ".ghost-cursor", "#paperAirplaneLayer", "StereoDeck"],
    "globe": ["#distanceMapSection", "distance", "globe", "leaflet", "three", "Globe()", "destination"],
    "footer": ["footer", ".footer-", ".footer-content", ".footer-links"],

    "admin_nav_top": ["#adminOverlay", "#adminDashboard", ".admin-", "Admin Dashboard", "admin-tab", "admin-panel"],
    "admin_funfeatures": [".ff-admin-", ".ff-toggle", "Fun Features Manager", "ffGratitudeList", "ffWishesList", "ffDedicationsList", "ffMoodList", "ffCapsulesList", "ffSuperlativesList"],
    "admin_destinations": ["Destinations Manager", "destPendingList", "destApprovedList", "approveAllDestinations", "approveDestination", "deleteDestination"],
    "admin_advice": ["Senior Advice Wall", "adviceList", "toggleAdviceFeature", "deleteAdvice", "adviceFeaturedCount"],
    "admin_papernotes": ["Paper Notes", "/api/paper-notes", "initPapernotesPanelContent"],
    "admin_teachers": ["Teacher Messages", "teacherAudioList", "teacherAudioFile", "uploadTeacherAudio", "teacherName"],
    "admin_students": ["Student Directory", "studentDirectoryEditor", "saveStudentDirectory", "addStudentRow"],
}

CSS_BASE_HINTS = [":root", "html", "body", "* {", "@keyframes", ".btn", ".container", "section {", "::-webkit-scrollbar"]

JS_KEYS: Dict[str, List[str]] = {
    "navbar": ["initNavbar", "mobileMenuBtn", "navLinks", "navbar.classList", "scrolled"],
    "hero": ["initIntroVideo", "introVideoOverlay", "skipIntro", "forceUnmute", "introVideo"],
    "countdown": ["initCountdown", "updateCountdown", "daysEl", "hoursEl", "minutesEl", "secondsEl", "farewellIST"],
    "upload": ["initUpload", "dropzone", "file-input", "submitUpload", "handleFiles", "updateFilePreview", "resetUploadForm"],
    "memories": ["initMemoryWall", "loadMemories", "renderMemories", "openLightbox", "closeLightbox", "loadComments", "postComment", "react(", "likeMemory"],
    "compilations": ["loadPublicCompilations", "playCompilation", "Compilation", "openCompilationCreator", "saveCompilation", "compSelectedSlides"],
    "teachers": ["renderTeachers", "teachersGrid"],
    "advicewall": ["submitAdvice", "loadAdvice", "toggleAdviceLike", "shareAdvice", "adviceGrid", "adviceForm", "initAdviceWall", "loadMoreAdvice"],
    "timeline": ["renderTimeline", "timelineList"],
    "gratitude": ["submitGratitudeNote", "loadGratitudeNotes", "gratitudeGrid", "gwFrom", "gwMsg"],
    "superlatives": ["loadSuperlatives", "voteSuperlative", "addSuperlativeNominee", "superlativesGrid"],
    "wishjar": ["submitWish", "loadWishes", "wishesScroll", "wishText"],
    "dedications": ["submitDedication", "loadDedications", "dedicationsList", "dedSong"],
    "mood": ["loadMoodBoard", "voteMood", "moodOptions", "moodBars"],
    "capsule": ["loadTimeCapsules", "submitTimeCapsule", "capsuleSealedList", "capsuleLetter"],
    "stereodeck": ["boombox", "cassette", "ghost", "paper", "sendNoteBtn", "StereoDeck", "leanBack", "sniper"],
    "globe": ["distance", "destination", "globe", "leaflet", "Globe()", "distanceMapSection"],

    "admin_nav_top": ["adminLogin", "openAdminDashboard", "switchAdminTab", "requireAdmin", "adminToken"],
    "admin_moderation": ["approveMemory", "trashMemory", "restoreMemory", "purgeMemory", "bulkAction", "renderAdminGrid", "updateAdminStats"],
    "admin_sitesettings": ["renderSettingsPanelHtml", "wireSettingsPanel", "syncSettingsEditor", "saveSettingsFromEditor", "reloadSettingsAdmin", "uploadIntroVideoFile", "removeIntroVideo"],
    "admin_theme": ["renderThemePanelHtml", "wireThemePanel", "syncThemeEditor", "readThemeFromEditor", "saveTheme", "resetThemeDefaults"],
    "admin_users": ["renderUsersPanelHtml", "loadUsers", "createUser", "updateUser", "renderUsersList"],
    "admin_compilations": ["renderCompilationsPanelHtml", "loadCompilationsAdmin", "editCompilationAdmin", "deleteCompilationAdmin"],
    "admin_funfeatures": ["initFunfeaturesPanelContent", "loadFunFeaturesData", "saveFunFeatureSettings", "openSuperlativesEditor", "deleteFunFeatureItem", "deleteFunFeatureMoodVote"],
    "admin_destinations": ["initDestinationsPanelContent", "loadDestinationsData", "approveDestination", "approveAllDestinations", "deleteDestination"],
    "admin_advice": ["initAdvicePanelContent", "loadAdviceData", "toggleAdviceFeature", "deleteAdvice"],
    "admin_papernotes": ["initPapernotesPanelContent", "renderPapernotesPanelHtml"],
    "admin_teachers": ["initTeachersPanelContent", "loadTeacherAudioData", "uploadTeacherAudio", "deleteTeacherAudio"],
    "admin_students": ["initStudentsPanelContent", "loadStudentDirectoryData", "saveStudentDirectory", "addStudentRow"],
    "admin_security": ["initSecurityPanelContent", "secChangePassword", "secResetHashes", "secToggleMaintenance", "secWipeAllMemories"],
}

JS_BASE_HINTS = [
    "const CONFIG",
    "function apiUrl",
    "DEFAULT_SETTINGS",
    "let state =",
    "function escapeHtml",
    "function showNotification",
    "function triggerConfetti"
]

# ---------------------------
# DOM selectors
# ---------------------------
SELECTORS: Dict[str, List[str]] = {
    "navbar": ["nav#navbar"],
    "hero": ["div#introVideoOverlay", "div#particles-container", "section#home"],
    "countdown": ["section#countdown"],
    "upload": ["section#upload"],
    "memories": ["section#memories", "div#lightbox"],
    "compilations": ["section#compilations", "div#compilationCreatorModal", "div#compilationPlayer"],
    "teachers": ["section#teachers"],
    "advicewall": ["section#adviceWall"],
    "timeline": ["section#timeline"],
    "quote": ["section#quote"],
    "gratitude": ["section#gratitudeWall"],
    "superlatives": ["section#superlativesSection"],
    "wishjar": ["section#wishJarSection"],
    "dedications": ["section#songDedicationsSection"],
    "mood": ["section#moodBoardSection"],
    "capsule": ["section#timeCapsuleSection"],
    "stereodeck": [
        "div#sniperGlobalFx",
        "div#leanBackOverlay",
        "div#boomboxDock",
        "button#ghostCursorToggle",
        "button#sendNoteBtn",
        "div#ghostCursorPopup",
        "div#ghostOffModal",
        "div#paperTutorial",
        "div#paperAirplaneLayer",
        "div#emojiPhysicsLayer",
    ],
    "globe": ["section#distanceMapSection"],
    "footer": ["footer", "div#notification", "div#confettiContainer", "div#batchUploadModal"],
    "admin_nav_top": ["div#adminOverlay", "div#adminDashboard"],
}

# ---------------------------
# IO helpers
# ---------------------------
def read_text(p: Path) -> str:
    return p.read_text(encoding=ENC, errors="replace")

def write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding=ENC, newline="\n")

def backup(p: Path) -> Path:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = p.parent / "_backups"
    bdir.mkdir(parents=True, exist_ok=True)
    bp = bdir / f"{p.stem}.backup_{ts}{p.suffix}"
    shutil.copy2(p, bp)
    return bp

def extract_doctype(raw: str) -> str:
    m = re.search(r"(?is)<!doctype[^>]*>", raw)
    return m.group(0).strip() if m else "<!DOCTYPE html>"

def truncate_to_html_only(raw: str) -> str:
    m = re.search(r"(?is)</html\s*>", raw)
    return raw[: m.end()] if m else raw

def outer_html(node) -> str:
    if isinstance(node, Comment):
        return f"<!-- {str(node).strip()} -->\n"
    return str(node).rstrip() + "\n"

def detach(node) -> None:
    try:
        node.extract()
    except Exception:
        pass

# ---------------------------
# Routing helpers
# ---------------------------
def score_text(text: str, needles: List[str]) -> int:
    t = (text or "").lower()
    score = 0
    for n in needles:
        if not n:
            continue
        nn = n.lower()
        if nn in t:
            score += 2 if nn.startswith("#") or nn.startswith(".") else 1
    return score

def route_css_rule(rule_text: str) -> str:
    best_key = "base"
    best = 0
    for k, needles in CSS_KEYS.items():
        s = score_text(rule_text, needles)
        if s > best:
            best = s
            best_key = k
    base_score = score_text(rule_text, CSS_BASE_HINTS)
    if base_score >= 2 and best < 4:
        return "base"
    return best_key if best_key != "base" else "base"

def split_css_to_buckets(css_text: str) -> Dict[str, str]:
    buckets: Dict[str, List[str]] = {}
    rules = tinycss2.parse_stylesheet(css_text, skip_comments=False, skip_whitespace=True)

    def add(k: str, s: str):
        if not s.strip():
            return
        buckets.setdefault(k, []).append(s)

    for r in rules:
        if r.type == "comment":
            txt = tinycss2.serialize([r])
            k = route_css_rule(txt)
            add(k, txt)
            continue

        if r.type == "at-rule":
            name = (r.lower_at_keyword or "").lower()
            txt = tinycss2.serialize([r])

            if name in ("keyframes", "-webkit-keyframes", "font-face"):
                add("base", txt)
                continue

            if name == "media" and r.content:
                inner = tinycss2.parse_rule_list(r.content, skip_whitespace=True, skip_comments=False)
                per_target: Dict[str, List[str]] = {}
                for ir in inner:
                    itxt = tinycss2.serialize([ir])
                    k = route_css_rule(itxt)
                    per_target.setdefault(k, []).append(itxt)

                prelude = tinycss2.serialize(r.prelude).strip()
                for k, items in per_target.items():
                    add(k, f"@media {prelude} {{\n" + "\n".join(items) + "\n}\n")
                continue

            k = route_css_rule(txt)
            add(k, txt)
            continue

        if r.type == "qualified-rule":
            txt = tinycss2.serialize([r])
            k = route_css_rule(txt)
            add(k, txt)
            continue

        txt = tinycss2.serialize([r])
        add("base", txt)

    return {k: "".join(v).strip() + "\n" for k, v in buckets.items()}

def split_js_by_headers(js: str) -> List[str]:
    lines = js.splitlines()
    cut = []
    buf = []
    header_re = re.compile(
        r"^\s*//\s*(=+|─+|═+|INTRO VIDEO|COMPILATION|BATCH UPLOAD|INLINE EDITING|PUBLIC COMPILATIONS|FAVICON|SNIPER|DESTINATIONS|ADMIN|ADVICE|FUN FEATURES|PAPER NOTES|TEACHER|STUDENT)\b",
        re.I
    )

    for ln in lines:
        if header_re.search(ln) and buf:
            cut.append("\n".join(buf).strip())
            buf = [ln]
        else:
            buf.append(ln)

    if buf:
        cut.append("\n".join(buf).strip())

    out = []
    for c in cut:
        if len(c.strip()) < 40:
            if out:
                out[-1] += "\n" + c
            else:
                out.append(c)
        else:
            out.append(c)
    return [x for x in out if x.strip()]

def route_js_chunk(chunk: str) -> str:
    best_key = "base"
    best = 0
    for k, needles in JS_KEYS.items():
        s = score_text(chunk, needles)
        if s > best:
            best = s
            best_key = k

    base_score = score_text(chunk, JS_BASE_HINTS)
    if base_score >= 3 and best < 4:
        return "base"
    return best_key if best_key != "base" else "base"

# ---------------------------
# Template building
# ---------------------------
def build_index_template(doctype: str, html_attrs: Dict, head_common_html: str, base_css: str, base_js: str) -> str:
    def attrs_to_str(attrs: Dict) -> str:
        parts = []
        for k, v in (attrs or {}).items():
            if v is None:
                continue
            if isinstance(v, list):
                v = " ".join(map(str, v))
            parts.append(f'{k}="{v}"')
        return (" " + " ".join(parts)) if parts else ""

    out = []
    out.append(doctype)
    out.append(f"<html{attrs_to_str(html_attrs)}>")
    out.append("<head>")
    out.append(head_common_html.strip() + "\n")

    if base_css.strip():
        out.append('<style id="base_styles">')
        out.append(base_css.rstrip())
        out.append("</style>")

    out.append("</head>")
    out.append("<body>")

    if base_js.strip():
        out.append('<script id="base_script">')
        out.append(base_js.rstrip())
        out.append("</script>")

    for k in ORDER:
        out.append(f"<!-- @include: {FRAG[k]} -->")

    out.append("</body>")
    out.append("</html>")
    return "\n".join(out) + "\n"

def expand_includes(text: str, base_dir: Path, max_depth: int = 60) -> str:
    out = text
    for _ in range(max_depth):
        matches = list(INCLUDE_RE.finditer(out))
        if not matches:
            return out

        new_out = out
        for m in reversed(matches):
            rel = m.group(1).strip()
            p = base_dir / rel
            if not p.exists():
                raise FileNotFoundError(f"Missing include: {rel}")

            inc = read_text(p)
            line_start = new_out.rfind("\n", 0, m.start()) + 1
            indent = re.match(r"[ \t]*", new_out[line_start:m.start()]).group(0)
            inc = "\n".join((indent + ln if ln.strip() else ln) for ln in inc.splitlines()) + "\n"
            new_out = new_out[:m.start()] + inc + new_out[m.end():]

        out = new_out

    raise RuntimeError("Too deep include expansion (circular includes?)")

# ---------------------------
# Main extraction
# ---------------------------
def extract_strict(input_html: Path, out_root: Path) -> None:
    raw = truncate_to_html_only(read_text(input_html))
    doctype = extract_doctype(raw)

    soup = BeautifulSoup(raw, "lxml")
    html = soup.find("html")
    head = soup.find("head")
    body = soup.find("body")

    if not html or not head or not body:
        raise RuntimeError("Missing <html>/<head>/<body>")

    (out_root / "fragments").mkdir(parents=True, exist_ok=True)
    (out_root / "fragments/admin").mkdir(parents=True, exist_ok=True)

    head_common: List[Tag] = []
    for ch in list(head.contents):
        if isinstance(ch, NavigableString) and not str(ch).strip():
            continue
        if isinstance(ch, Tag):
            if ch.name in ("meta", "title"):
                head_common.append(ch)
                detach(ch)
            elif ch.name == "link":
                head_common.append(ch)
                detach(ch)

    head_common_html = "".join(outer_html(x) for x in head_common).strip() + "\n"

    css_buckets: Dict[str, str] = {}
    base_css_parts: List[str] = []

    all_styles = soup.find_all("style")
    for st in list(all_styles):
        css_text = st.get_text("\n", strip=False) or ""
        detach(st)
        buckets = split_css_to_buckets(css_text)
        for k, css in buckets.items():
            if k == "base":
                base_css_parts.append(css)
            else:
                css_buckets[k] = (css_buckets.get(k, "") + "\n" + css).strip() + "\n"

    base_css = "\n".join(base_css_parts).strip() + "\n"

    js_buckets: Dict[str, List[str]] = {}
    base_js_parts: List[str] = []
    external_script_tags_by_key: Dict[str, List[str]] = {}

    all_scripts = soup.find_all("script")
    for sc in list(all_scripts):
        if sc.get("src"):
            src = sc.get("src")
            tag_html = outer_html(sc)
            detach(sc)
            key = "globe" if any(x in (src or "").lower() for x in ["leaflet", "three", "globe.gl"]) else "footer"
            external_script_tags_by_key.setdefault(key, []).append(tag_html)
            continue

        js = sc.get_text("\n", strip=False) or ""
        detach(sc)
        chunks = split_js_by_headers(js)
        for c in chunks:
            rkey = route_js_chunk(c)
            if rkey == "base":
                base_js_parts.append(c.strip() + "\n")
            else:
                js_buckets.setdefault(rkey, []).append(c.strip() + "\n")

    base_js = "\n".join(base_js_parts).strip() + "\n"

    markup_buckets: Dict[str, List[str]] = {k: [] for k in FRAG.keys()}

    def grab(selector: str) -> Optional[Tag]:
        return soup.select_one(selector)

    for key, selectors in SELECTORS.items():
        for sel in selectors:
            node = grab(sel)
            if node:
                markup_buckets[key].append(outer_html(node))
                detach(node)

    leftovers = []
    for ch in list(body.contents):
        if isinstance(ch, NavigableString) and not str(ch).strip():
            continue
        leftovers.append(ch)

    for node in leftovers:
        markup_buckets["footer"].append(outer_html(node))
        detach(node)

    manifest = {"created": {}, "notes": []}

    def emit_fragment(key: str) -> str:
        parts = [f"<!-- FRAGMENT: {key} -->\n"]

        css = css_buckets.get(key, "")
        if css.strip():
            parts.append(f'<style data-fragment-style="{key}">\n{css.rstrip()}\n</style>\n')

        for t in external_script_tags_by_key.get(key, []):
            parts.append(t)

        for m in markup_buckets.get(key, []):
            parts.append(m)

        for c in js_buckets.get(key, []):
            parts.append(f'<script data-fragment-script="{key}">\n{c.rstrip()}\n</script>\n')

        return "".join(parts).rstrip() + "\n"

    for key, rel in FRAG.items():
        content = emit_fragment(key)
        write_text(out_root / rel, content)
        manifest["created"][key] = rel

    tpl = build_index_template(
        doctype=doctype,
        html_attrs=dict(html.attrs or {}),
        head_common_html=head_common_html,
        base_css=base_css,
        base_js=base_js,
    )

    write_text(out_root / "index.template.html", tpl)
    write_text(out_root / "fragments_manifest.json", json.dumps(manifest, indent=2) + "\n")

    print("[strict] wrote fragments/ and fragments/admin/")
    print("[strict] wrote index.template.html (buildable)")
    print("[strict] wrote fragments_manifest.json")

def build_from_template(template_path: Path, out_index: Path, do_backup: bool = True) -> None:
    if do_backup and out_index.exists():
        bp = backup(out_index)
        print(f"[build] backup: {out_index} -> {bp}")

    built = expand_includes(read_text(template_path), template_path.parent)
    write_text(out_index, built)
    print(f"[build] wrote: {out_index} ({len(built.splitlines())} lines)")

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    ex = sub.add_parser("extract")
    ex.add_argument("--input", type=Path, default=Path("index.html"))
    ex.add_argument("--out", type=Path, default=Path("."))

    b = sub.add_parser("build")
    b.add_argument("--template", type=Path, default=Path("index.template.html"))
    b.add_argument("--out", type=Path, default=Path("index.html"))
    b.add_argument("--no-backup", action="store_true")

    args = ap.parse_args()

    if args.cmd == "extract":
        extract_strict(args.input, args.out)
    else:
        build_from_template(args.template, args.out, do_backup=(not args.no_backup))

if __name__ == "__main__":
    main()