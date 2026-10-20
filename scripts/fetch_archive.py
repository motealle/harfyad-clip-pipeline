"""Inspect or download MP3s from an archive.org item.
Usage: fetch_archive.py SPEC OUTDIR   SPEC = IDENTIFIER or IDENTIFIER::NAME_SUBSTRING (case-insensitive).
With no substring, lists the MP3 files and the license, downloads nothing."""
import json, pathlib, re, sys, urllib.parse, urllib.request

spec, out = sys.argv[1], pathlib.Path(sys.argv[2])
ident, _, sub = spec.partition("::")
meta = json.load(urllib.request.urlopen(f"https://archive.org/metadata/{ident}", timeout=60))
m = meta.get("metadata", {})
print("title:", m.get("title"), "| licenseurl:", m.get("licenseurl"), "| rights:", m.get("rights"))
mp3 = [f for f in meta.get("files", []) if f["name"].lower().endswith(".mp3")]
print("mp3 count:", len(mp3))
if not sub:
    for f in mp3[:60]:
        print(f["name"], f.get("size"))
    sys.exit(0)
pick = [f for f in mp3 if sub.lower() in f["name"].lower()]
if not pick:
    sys.exit("no match")
f = min(pick, key=lambda f: int(f.get("size", 0) or 0))
out.mkdir(parents=True, exist_ok=True)
dest = out / f"archive-{re.sub(r'[^A-Za-z0-9]+', '-', ident)[:40]}-{re.sub(r'[^A-Za-z0-9]+', '-', f['name'])[:60]}"
url = f"https://archive.org/download/{ident}/{urllib.parse.quote(f['name'])}"
with urllib.request.urlopen(url, timeout=300) as r, open(dest, "wb") as fh:
    while chunk := r.read(1 << 16):
        fh.write(chunk)
print("saved", dest.name, dest.stat().st_size)
