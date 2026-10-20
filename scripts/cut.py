"""Cut clips from a plan with ffmpeg stream copy. Usage: cut.py SRC PLAN.json OUTDIR
Plan: {"pad": 0.3, "clips": [{"name": "...", "start": 12.5, "end": 40.0, "topic": "..."}]}
Stream copy is fast and lossless but cuts land on MP3 frame boundaries (about 26 ms), so padding guards the edges.
Non-MP3 sources are converted to MP3 once first (64 kbps mono, 44.1 kHz)."""
import json, pathlib, subprocess, sys

def run(*args): subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)
def duration(path: str) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout.strip())
def codec(path: str) -> str:
    return subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout.strip()

src, plan_path, out = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
plan = json.loads(pathlib.Path(plan_path).read_text(encoding="utf-8"))
pad = float(plan.get("pad", 0.3))
if codec(src) != "mp3":
    converted = str(out / "source.mp3")
    run("-i", src, "-vn", "-ac", "1", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "64k", converted)
    src = converted
total = duration(src)
manifest = []
for c in plan["clips"]:
    start = max(0.0, float(c["start"]) - pad)
    end = min(total, float(c["end"]) + pad)
    dest = out / f"{c['name']}.mp3"
    run("-ss", f"{start:.3f}", "-i", src, "-t", f"{end - start:.3f}", "-c", "copy", str(dest))
    manifest.append({"name": c["name"], "topic": c.get("topic", ""), "start": round(start, 3), "end": round(end, 3), "duration": round(duration(str(dest)), 3), "file": dest.name})
(out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"clips: {len(manifest)}")
