"""Download one MP3 from an archive.org item (public-domain LibriVox readings etc.). Usage: fetch_archive.py IDENTIFIER OUTDIR
Picks a 64 kb MP3 if the item has one, otherwise the smallest MP3 above 300 KB."""
import json, pathlib, sys, urllib.parse, urllib.request

ident, out = sys.argv[1], pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
meta = json.load(urllib.request.urlopen(f"https://archive.org/metadata/{ident}", timeout=60))
mp3 = [f for f in meta.get("files", []) if f["name"].lower().endswith(".mp3")]
sized = lambda f: int(f.get("size", 0) or 0)
pool = [f for f in mp3 if "64kb" in f["name"]] or mp3
pool.sort(key=sized)
pick = next((f for f in pool if sized(f) > 300_000), pool[0])
url = f"https://archive.org/download/{ident}/{urllib.parse.quote(pick['name'])}"
dest = out / f"archive-{ident[:40]}.mp3"
with urllib.request.urlopen(url, timeout=300) as r, open(dest, "wb") as f:
    while chunk := r.read(1 << 16):
        f.write(chunk)
print(f"{pick['name']} -> {dest.name} ({dest.stat().st_size} bytes)")
