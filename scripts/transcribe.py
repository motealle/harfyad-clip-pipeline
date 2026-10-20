"""Transcribe audio to timecoded segments (segments.json + transcript.srt). Usage: transcribe.py SRC OUTDIR [MODEL]"""
import json, pathlib, sys
from faster_whisper import WhisperModel

def ts(sec: float) -> str:
    ms = int(round(sec * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

src, out = sys.argv[1], pathlib.Path(sys.argv[2])
model_name = sys.argv[3] if len(sys.argv) > 3 else "small"
out.mkdir(parents=True, exist_ok=True)
model = WhisperModel(model_name, device="cpu", compute_type="int8")
PROMPT = "متن فارسی درباره‌ی اخلاق، با گفتار یک استاد؛ نشانه‌گذاری کامل."
segs, info = model.transcribe(src, language="fa", vad_filter=True, beam_size=5, initial_prompt=PROMPT, condition_on_previous_text=False, temperature=0.0)
rows = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs]
(out / "segments.json").write_text(json.dumps({"language": info.language, "duration": round(info.duration, 2), "model": model_name, "segments": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
with open(out / "transcript.srt", "w", encoding="utf-8") as f:
    for i, r in enumerate(rows, 1):
        f.write(f"{i}\n{ts(r['start'])} --> {ts(r['end'])}\n{r['text']}\n\n")
print(f"segments: {len(rows)}, duration: {info.duration:.1f}s")
