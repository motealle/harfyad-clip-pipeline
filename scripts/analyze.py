"""Decide whether a clip needs treatment, from five 3-second samples (start, first third, middle, last third, end).
Usage: analyze.py SRC OUTDIR
Per sample: peak, noise floor (10th percentile of 50 ms frame levels), speech level (90th), SNR, 45-65 Hz hum share,
and spectral flatness of quiet frames (near 1 = hiss/fan/white noise). Each metric becomes a 0..1 deviation from
a good target. Mean deviation <= 0.20 means tolerate (only normalize). Above that, pick effects per failing metric."""
import json, pathlib, subprocess, sys
import numpy as np

SR, WIN, FRAME = 16000, 3.0, 0.05
TARGET_PEAK_DB = -1.94          # 80 % of full scale
TOLERANCE = 0.20

def ffprobe_duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout)

def read_window(path, start):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{WIN}", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0

def full_peak_db(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    for line in err.splitlines():
        if "max_volume" in line:
            return float(line.split(":")[1].split("dB")[0])
    raise RuntimeError("volumedetect gave no max_volume")

def clamp(x): return float(min(1.0, max(0.0, x)))

def analyse_window(x):
    peak_db = 20 * np.log10(np.max(np.abs(x)) + 1e-12)
    n = len(x) // int(SR * FRAME) * int(SR * FRAME)
    frames = x[:n].reshape(-1, int(SR * FRAME))
    frame_db = 20 * np.log10(np.sqrt(np.mean(frames ** 2, axis=1)) + 1e-9)
    noise_db = float(np.percentile(frame_db, 10))
    speech_db = float(np.percentile(frame_db, 90))
    snr = speech_db - noise_db
    spec = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    hum = float(spec[(freqs >= 45) & (freqs <= 65)].sum() / (spec.sum() + 1e-12))
    quiet = frames[frame_db <= noise_db + 3]
    flat = []
    for f in quiet:
        p = np.abs(np.fft.rfft(f * np.hanning(len(f)))) ** 2 + 1e-12
        flat.append(np.exp(np.mean(np.log(p))) / np.mean(p))
    flatness = float(np.median(flat)) if flat else 1.0
    dev = {
        "noise_floor": clamp((noise_db + 55) / 20),      # good <= -55 dBFS, bad >= -35
        "snr": clamp((25 - snr) / 15),                   # good >= 25 dB, bad <= 10
        "hum": clamp((hum - 0.002) / 0.018),             # good <= 0.2 %, bad >= 2 % of energy at 45-65 Hz
        # hiss only matters when it is audible; inaudible floors do not count
        "flatness": clamp((flatness - 0.2) / 0.4) if noise_db > -60 else 0.0,  # good <= 0.2 (tonal), bad >= 0.6
    }
    return {"peak_db": round(peak_db, 2), "noise_floor_db": round(noise_db, 2), "speech_db": round(speech_db, 2),
            "snr_db": round(snr, 2), "hum_share": round(hum, 4), "flatness": round(flatness, 3), "deviation": {k: round(v, 3) for k, v in dev.items()}}

def sample_starts(D):
    last = max(0.0, D - WIN)
    pts = {"beginning": D * 0.05, "first_third": D / 6 - WIN / 2, "middle": D / 2 - WIN / 2,
           "last_third": 5 * D / 6 - WIN / 2, "end": D - WIN - D * 0.05}
    return {k: min(max(0.0, v), last) for k, v in pts.items()}

def main(src, out_dir):
    D = ffprobe_duration(src)
    windows = {}
    for name, start in sample_starts(D).items():
        r = analyse_window(read_window(src, start))
        r["start_s"] = round(start, 2)
        windows[name] = r
    keys = ["noise_floor", "snr", "hum", "flatness"]
    per_window = {k: float(np.mean([w["deviation"][k] for w in windows.values()])) for k in keys}
    overall = float(np.mean(list(per_window.values())))
    worst = max(windows, key=lambda n: np.mean(list(windows[n]["deviation"].values())))
    filters = []
    if per_window["noise_floor"] > TOLERANCE or per_window["flatness"] > TOLERANCE:
        filters.append("afftdn=nf=-25:nt=w")                  # FFT denoiser for hiss, fan and room tone
    if per_window["hum"] > TOLERANCE:
        filters.append("highpass=f=70,bandreject=f=50:width_type=h:w=5,bandreject=f=100:width_type=h:w=5")  # 50 Hz mains hum and its 2nd harmonic
    if per_window["snr"] > TOLERANCE and per_window["noise_floor"] <= TOLERANCE:
        filters.append("equalizer=f=2500:t=q:w=1.2:g=3")      # presence boost for distant speech
    verdict = "treat" if overall > TOLERANCE else "tolerate"
    peak = full_peak_db(src)
    report = {"duration_s": round(D, 2), "windows": windows, "per_metric": {k: round(v, 3) for k, v in per_window.items()},
              "overall_deviation": round(overall, 3), "worst_window": worst, "verdict": verdict,
              "filters": filters if verdict == "treat" else [], "gain_db": round(TARGET_PEAK_DB - peak, 2),
              "trim_silence": {"over_s": 3.0, "keep_s": 1.0}}
    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "analysis.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"verdict={verdict} overall={overall:.3f} worst={worst} gain_db={report['gain_db']} filters={report['filters']}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
