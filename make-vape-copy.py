#!/usr/bin/env python3
"""
Derive the vape's copy of the site from index.html.

Same content, minus anything the chip can't hold: the two photos and the
embedded resume PDF. Regenerate this whenever index.html changes so the two
copies don't drift.
"""
import re, gzip, sys, pathlib

SRC = pathlib.Path("index.html")
OUT = pathlib.Path("vape-index.html")
SITE = "https://jakackioscar.github.io"

html = SRC.read_text(encoding="utf-8")
before = len(html)

def drop(pattern, why, flags=re.S):
    global html
    html, n = re.subn(pattern, "", html, flags=flags)
    print(f"  removed {n:2d}  {why}")

# --- markup -------------------------------------------------------------
drop(r'\s*<img class="avatar".*?>', "avatar image")
drop(r'\s*<figure class="shot">.*?</figure>', "vape photo + caption")

# resume: no PDF on the chip, link to the full site instead
html, n = re.subn(
    r'<object class="pdf".*?</object>',
    f'<p class="note">There is no room for a PDF on 32 KB of flash. It is on\n'
    f'      the full site, at <a href="{SITE}/resume.pdf">{SITE.replace("https://","")}/resume.pdf</a>.</p>',
    html, flags=re.S)
print(f"  swapped {n:2d}  embedded PDF -> link")

# the local download link would 404 on the chip - point it at the full site
html, n = re.subn(
    r'<p><a href="resume\.pdf" download>Download PDF</a></p>\s*',
    "", html)
print(f"  removed {n:2d}  local PDF download link")

# .note isn't styled in the source, so define it
html = html.replace(
    "  .todo { color: var(--mark); border-bottom: 1px dashed currentColor; }",
    "  .note { color: var(--soft); font-size: 0.98rem; }\n"
    "  .todo { color: var(--mark); border-bottom: 1px dashed currentColor; }"
)

# --- javascript ---------------------------------------------------------
drop(r'\s*// Show a labelled placeholder.*?\}\)\(\);', "image fallback script")

# --- css that no longer applies ----------------------------------------
drop(r'\s*\.avatar, \.avatar-ph \{.*?\n  \}', "avatar sizing")
drop(r'\s*\.avatar \{[^}]*\}', "avatar border")
drop(r'\s*\.avatar-ph \{.*?\n  \}', "avatar placeholder")
drop(r'\s*@media \(max-width: 30rem\) \{.*?\n  \}', "avatar mobile rule")
drop(r'\s*figure\.shot[^{]*\{.*?\n  \}', "figure styles")
drop(r'\s*\.pdf \{.*?\n  \}', "pdf frame")

# --- a line owning up to which copy you're reading ---------------------
html = html.replace(
    '<p>Outside of work, I like to beekeep, bike, and hike in nature!</p>',
    '<p>Outside of work, I like to beekeep, bike, and hike in nature!</p>\n'
    '    <p class="note">You are reading this off the vape. The full site,\n'
    f'      with photos, is at <a href="{SITE}">{SITE.replace("https://","")}</a>.</p>'
)

# tidy the blank lines the deletions left behind
html = re.sub(r'\n{3,}', '\n\n', html)

OUT.write_text(html, encoding="utf-8")
gz = gzip.compress(html.encode("utf-8"), 9)

print()
print(f"  raw      {before:6d} -> {len(html):6d} bytes")
print(f"  gzipped         {len(gz):6d} bytes")
print(f"  budget   ~18000 bytes of flash for content")
print(f"  headroom {18000 - len(gz):6d} bytes")
if b"me.jpg" in html.encode() or b"vape.jpg" in html.encode():
    sys.exit("  ERROR: an image reference survived")
print("  no image references remain")
