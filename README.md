# harfyad-clip-pipeline

پایپ‌لاین قطعه‌چینی صوت برای حرف‌یاد. فقط کد و فایل‌های تست؛ صدای بدون مجوز اینجا نمی‌آید.

1. **transcribe:** متن‌گردانی با faster-whisper و خروجی `segments.json` و `transcript.srt` با تایم‌کد (artifact).
2. **plan:** بر اساس متن، فایل `plans/*.json` با بازه‌ها و موضوع‌ها ساخته می‌شود.
3. **cut:** برش با ffmpeg به روش کپی (`-c copy`) با پد ۰٫۳ ثانیه دو طرف؛ خروجی MP3 و `manifest.json`.

اجرا: Actions → clips → Run workflow. مجوز هر منبع در `PERMISSIONS.md` ثبت شود.
ریپو عمومی است؛ artifactها و لاگ‌ها برای همه قابل دیدن‌اند.
