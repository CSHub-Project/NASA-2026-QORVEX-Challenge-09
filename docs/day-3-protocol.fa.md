# پروتکل علمی روز سوم

## سؤال آزمایش

آیا مدلی که هم‌زمانی عبور، همسایگی مکانی، هندسه footprint، فصل و تفاوت‌های منطقه/روز–شب را لحاظ می‌کند، می‌تواند fixed-ratio baseline را روی آینده‌ای که در آموزش ندیده شکست دهد؟

## چرا روش روز دوم کافی نبود؟

baseline روز دوم مجموع‌های منطقه‌ای را تقریباً دنبال کرد، اما Spearman سلول‌ـ‌زمان منفی بود. همچنین مقاله مقایسه FRP نشان می‌دهد اختلاف MODIS/VIIRS به زمان عبور، زاویه دید، اکوسیستم و مقیاس وابسته است و مقایسه‌های دقیق، Aqua MODIS و VIIRS را مکانی–زمانی match می‌کنند. منابع اصلی:

- [Li et al. 2018 — comparison of VIIRS and MODIS FRP](https://doi.org/10.1029/2017JD027823)
- [Schroeder et al. 2014 — VIIRS 375 m active-fire algorithm](https://doi.org/10.1016/j.rse.2013.12.008)
- [NASA VIIRS Collection 2 375 m User Guide](https://www.earthdata.nasa.gov/s3fs-public/2024-07/VIIRS_C2_AF-375m_User_Guide_1.0.pdf)

## جفت‌سازی passها

1. فقط Aqua MODIS و S-NPP VIIRS وارد calibration می‌شوند؛ Terra در داده اصلی حفظ می‌شود.
2. timestampهای هر `region × date × day/night × sensor` با شکاف بیش از ۳۰ دقیقه به pass جدا تقسیم می‌شوند.
3. passهای دو حسگر به‌صورت one-to-one و greedy-nearest جفت می‌شوند.
4. فاصله زمانی مجاز حداکثر ۶۰ دقیقه است و مقدار واقعی به مدل داده می‌شود.
5. ۱٬۰۶۹ جفت pass ساخته شد؛ median اختلاف ۲۵ دقیقه و بیشینه ۵۸ دقیقه است.

این روش approximation مبتنی بر FIRMS point export است، نه granule geometry کامل. بنابراین «contemporaneous» در این پروژه به معنی حداکثر ۶۰ دقیقه است، نه ادعای هم‌زمانی دقیق چنددقیقه‌ای.

## واحد تحلیل و ویژگی‌ها

واحد تحلیل `matched pass × equal-area cell × day/night` است. زوج‌های یک‌طرفه حذف نمی‌شوند و سمت فاقد detection مقدار صفر می‌گیرد.

ویژگی‌ها:

- VIIRS count و `log1p(count)` در سلول؛
- VIIRS FRP و neighborhood ۳×۳؛
- میانگین scan و track footprint؛
- اختلاف زمانی passها؛
- latitude؛
- چرخه فصلی با `sin(month)` و `cos(month)`؛
- region و day/night.

مدل `HistGradientBoostingRegressor` با Poisson loss، پارامترهای از پیش ثابت، regularization و random seed ثابت است. این انتخاب برای پاسخ غیرمنفی و رابطه غیرخطی انجام شده؛ مدل به دلیل پیچیدگی بیشتر فقط در صورت شکست baseline پذیرفته می‌شود.

## جلوگیری از leakage و انتخاب مدل

| بازه ۲۰۱۹ | نقش |
|---|---|
| ژانویه–ژوئن | fit اولیه |
| ژوئیه–سپتامبر | انتخاب baseline یا model برای هر region/day-night/metric |
| اکتبر–دسامبر | test نهایی؛ در انتخاب استفاده نمی‌شود |

مدل منتخب سپس روی ژانویه–سپتامبر refit و فقط یک‌بار روی test ارزیابی می‌شود. اگر validation کمتر از ۱۰۰ ردیف داشته باشد یا مدل MAE را بهتر نکند، baseline انتخاب می‌شود.

## عدم‌قطعیت و sensitivity

- bootstrap روی بلوک‌های تاریخ انجام می‌شود تا ردیف‌های یک روز مستقل فرض نشوند.
- ۵۰۰ بازنمونه برای نتیجه اصلی استفاده شده است.
- کل pipeline برای شبکه‌های ۵، ۱۰ و ۲۵ کیلومتر تکرار می‌شود.
- برای مقایسه اندازه شبکه از WAPE استفاده می‌شود؛ مقایسه MAE خام بین اندازه‌های مختلف گمراه‌کننده است.

## معیار پذیرش

Count فقط اگر در test، MAE/WAPE کمتر و Spearman بیشتر باشد و جهت بهبود در sensitivity حفظ شود پذیرفته می‌شود. FRP علاوه بر نتیجه کلی باید در subgroupها و همه مقیاس‌ها پایدار باشد؛ این شرط فعلاً برقرار نشده است.
