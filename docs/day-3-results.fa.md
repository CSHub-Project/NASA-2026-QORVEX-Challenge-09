# نتایج روز سوم

## نتیجه اصلی روی test دست‌نخورده اکتبر تا دسامبر ۲۰۱۹

شبکه اصلی: ۱۰ کیلومتر. تعداد test cell-pass: ۳۱٬۷۰۲.

| هدف | روش | MAE | WAPE | Median AE | Bias | Spearman |
|---|---|---:|---:|---:|---:|---:|
| Count | Fixed ratio | 0.596 | 1.548 | 0.313 | +0.007 | -0.159 |
| Count | Guarded model | 0.385 | 1.002 | 0.182 | +0.032 | +0.572 |
| FRP | Fixed ratio | 27.205 | 1.578 | 8.100 | +4.760 | -0.126 |
| FRP | Guarded model | 23.273 | 1.350 | 5.635 | +5.895 | +0.477 |

### Count

- MAE برابر **۳۵٫۳٪** کاهش یافت.
- ارتباط رتبه‌ای از منفی به `0.572` رسید.
- bootstrap تاریخ‌محور ۵۰۰باره برای `model MAE − baseline MAE` بازه `[-0.227, -0.193]` داد؛ تمام بازنمونه‌ها به نفع مدل بودند.
- مدل count در هر شش subgroup منطقه × روز/شب، MAE را کاهش و Spearman را افزایش داد.

نتیجه: count model یک **candidate پذیرفته‌شده برای ادامه پژوهش** است، نه هنوز مدل production جهانی.

### FRP

نتیجه کلی بهتر است و bootstrap کلی نیز بهبود MAE را نشان می‌دهد، اما نتیجه subgroupها پایدار نیست. برای نمونه در شب کالیفرنیای شمالی، تغییر توزیع زمانی باعث شد مدل validation-selected در test از baseline بدتر شود. در شبکه ۲۵ کیلومتری نیز WAPE مدل اندکی بدتر از baseline شد.

نتیجه: FRP فعلاً **experimental / not for operational use** است. نمایش آن بدون این هشدار یا ادعای harmonization کامل علمی نیست.

## sensitivity شبکه

| Grid | Count WAPE baseline | Count WAPE model | بهبود Count | FRP WAPE baseline | FRP WAPE model |
|---:|---:|---:|---:|---:|---:|
| 5 km | 1.627 | 0.940 | 42.2% | 1.650 | 1.333 |
| 10 km | 1.548 | 1.002 | 35.3% | 1.578 | 1.350 |
| 25 km | 1.409 | 1.022 | 27.5% | 1.446 | 1.457 |

Count در هر سه مقیاس baseline را شکست می‌دهد. اندازه ۱۰ کیلومتر برای MVP حفظ می‌شود چون با واحد پیشنهادی تقویم سازگار است؛ انتخاب نهایی grid باید با چند سال و مناطق بیشتر دوباره ارزیابی شود.

## محدودیت‌هایی که قبل از ارائه نهایی باید حل شوند

1. فقط سال ۲۰۱۹ استفاده شده؛ تعمیم بین‌سالی هنوز اثبات نشده است.
2. سه منطقه نماینده همه biomeها نیستند.
3. FIRMS point export، cloud mask، granule polygon و view zenith angle کامل را ندارد.
4. pass matching حداکثر ۶۰ دقیقه است؛ آتش‌های کوتاه‌مدت می‌توانند در این فاصله تغییر کنند.
5. zero detection به معنی zero fire قطعی نیست.
6. count برابر burned area یا تعداد event مستقل نیست.

## تصمیم اجرایی

- Count candidate وارد مرحله چندساله و anomaly calendar می‌شود.
- FRP در UI آینده با برچسب experimental باقی می‌ماند و مبنای هشدار نیست.
- گام بعد: دریافت چند سال overlap، spatial/year holdout، bootstrap مکانی–زمانی و event clustering.
