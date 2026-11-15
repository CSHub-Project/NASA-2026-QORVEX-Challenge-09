# سند پژوهش و راهبرد پروژه

## Harmonization of MODIS and VIIRS Hot Spots — NASA Space Apps 2026

تاریخ بررسی: ۳ نوامبر ۲۰۲۶

## ۱) برداشت دقیق از صورت مسئله رسمی

چالش از ما یک **وب‌اپلیکیشن تقویم فعالیت سوختن (Burning Activity Calendar)** می‌خواهد که رکورد تاریخی طولانی MODIS را با تداوم و جزئیات بیشتر VIIRS همگون کند. کاربر باید بتواند یک ناحیه و بازه زمانی انتخاب کند و الگوهای تاریخی، شرایط غیرعادی و دوره‌های بحرانی را ببیند و تحلیل/داده را دانلود کند.

خروجی دو بخش جدانشدنی دارد:

1. **همگون‌سازی علمی MODIS و VIIRS:** پس از این مرحله، تغییر سنسور نباید به‌اشتباه به‌صورت تغییر فعالیت آتش دیده شود.
2. **محصول کاربردی:** نقشه تعاملی، انتخاب AOI، انتخاب تاریخ، تقویم فعالیت، مقایسه با تاریخ، شاخص‌های محدود اما معنادار، رنگ‌های دسترس‌پذیر و خروجی CSV.

مخاطبان پیشنهادشده در صورت مسئله: تیم‌های هشدار زودهنگام، مدیران بحران، دانشمندان، مدیران زمین و آتش‌نشانان.

نکته تفسیری مهم: hotspot الزاماً «آتش‌سوزی جنگلی» نیست؛ می‌تواند آتش کشاورزی، پاک‌سازی زمین، فلر گازی، فعالیت صنعتی، آتشفشان یا ناهنجاری حرارتی دیگری باشد. بنابراین محصول نباید هر نقطه را بدون طبقه‌بندی یا هشدار، wildfire بنامد.

## ۲) چرا ترکیب ساده داده‌ها از نظر علمی غلط است؟

| عامل | MODIS | VIIRS 375 m | اثر روی مقایسه |
|---|---|---|---|
| تفکیک مکانی اسمی | حدود ۱ کیلومتر | حدود ۳۷۵ متر | VIIRS آتش‌های کوچک‌تر/سردتر و پیکسل‌های بیشتری از یک رخداد را می‌بیند |
| پوشش عرضی | حدود ۲۳۴۰ کیلومتر | حدود ۳۰۶۰ کیلومتر | MODIS به‌ویژه در عرض‌های پایین شکاف پوشش دارد |
| رفتار در لبه اسکن | اندازه پیکسل MODIS شدیداً بزرگ می‌شود | یکنواخت‌تر | شمارش و FRP با زاویه دید سوگیری می‌گیرد |
| حساسیت شب | کمتر از VIIRS 375 m | بسیار بیشتر | نسبت شمارش ثابت جهانی معتبر نیست |
| confidence | عدد ۰ تا ۱۰۰ و ماهیت آزمایشی | low/nominal/high | آستانه‌گذاری مستقیم بین دو سنسور قابل دفاع نیست |
| زمان و تعداد عبور | Terra و Aqua | S‑NPP، NOAA‑20، NOAA‑21 | تعداد فرصت مشاهده در زمان تغییر می‌کند |
| الگوریتم/کالکشن | MOD14/MYD14 C6.1 | VNP/VJ1/VJ2 14IMG C2 | تغییر نسخه و الگوریتم می‌تواند شکست مصنوعی بسازد |

محدودیت‌های مشترک نیز مهم‌اند: ابر، دود غلیظ، تاج پوشش، آتش کوتاه‌مدت بین دو عبور، خطای مکان‌یابی، اشباع کانال و تکرار تشخیص در اسکن/مدارهای هم‌پوشان.

نتیجه: **جمع‌کردن تعداد نقاط، حذف فاصله‌ای ساده، یا ضرب کل VIIRS در یک ضریب جهانی ثابت، harmonization علمی محسوب نمی‌شود.** ضریب به منطقه، فصل، روز/شب، پوشش زمین، شدت آتش، هندسه دید و تعداد فرصت مشاهده وابسته است.

## ۳) داده درست برای هر کاربرد

### تحلیل تاریخی و کالیبراسیون

- MODIS Standard Processing (C6.1)، نه NRT، از Terra و Aqua.
- VIIRS Standard Processing (Collection 2) برای S‑NPP و سپس NOAA‑20/NOAA‑21.
- بازه هم‌پوشانی Aqua MODIS و S‑NPP VIIRS از ۲۰۱۲ به بعد، پل اصلی کالیبراسیون است؛ هر دو تقریباً مدار ۱۳:۳۰ محلی دارند و برای مقایسه زوجی مناسب‌تر از Terra هستند.
- برای مطالعه علمی بلندمدت، راهنمای NASA صریحاً داده standard/science-quality را بر NRT ترجیح می‌دهد.

### وضعیت جاری

- FIRMS NRT/RT/URT برای پایش با تأخیر کم.
- داده جاری باید با برچسب روشن «provisional / NRT» نمایش داده شود و پس از رسیدن standard processing جایگزین شود.
- API ناحیه FIRMS حداکثر ۵ روز در هر درخواست می‌پذیرد و MAP_KEY می‌خواهد؛ برای آرشیو کامل نباید در زمان اجرای درخواست کاربر هزاران فراخوانی زنده انجام داد.

### داده‌های اعتبارسنجی مستقل

- MCD64A1/VNP64A1 burned area برای سازگاری مکانی/زمانی در مقیاس تجمعی؛ این محصول با hotspot یکی نیست و نباید ground truth کامل نامیده شود.
- Landsat 8/9 یا Sentinel‑2 برای نمونه‌های محدود با وضوح بالاتر.
- مرزهای رخداد معتبر محلی/ملی، در صورت دسترسی.
- پوشش زمین برای تحلیل خطای وابسته به اکوسیستم و جداکردن فلر/آتش کشاورزی از پوشش طبیعی.

## ۴) روش پیشنهادی همگون‌سازی

### مرحله A — کنترل کیفیت و provenance

1. نگه‌داری ستون‌های اصلی بدون دستکاری و افزودن ستون‌های استاندارد: `sensor`, `platform`, `product`, `collection`, `processing_mode`, `acquired_at_utc`, `daynight`, `frp_mw`, `confidence_raw`, `scan_km`, `track_km`.
2. ثبت منبع، نسخه، زمان دریافت و checksum هر پارتیشن.
3. تبدیل زمان UTC به زمان خورشیدی/محلی برای تحلیل روز و فصل، بدون حذف UTC.
4. تعریف crosswalk جداگانه برای confidence؛ مقدار عددی MODIS نباید مستقیماً با حروف VIIRS مقایسه شود.
5. نشانه‌گذاری کیفیت پوشش و gap به‌جای تعبیر «صفر تشخیص» به‌عنوان «صفر آتش».

### مرحله B — واحد تحلیل مشترک

- استفاده از شبکه مساوی‌مساحت یا سلول‌های تقریباً مساوی‌مساحت در چند رزولوشن، نه شمارش خام نقاط در مختصات WGS84.
- واحد پایه پیشنهادی برای تقویم: سلول ۵ تا ۱۰ کیلومتر × روز؛ برای نقشه جزئیات، نقاط/footprint اصلی حفظ شوند.
- تجمیع جداگانه روز/شب و platform، سپس ترکیب کنترل‌شده.
- دو متریک اصلی:
  - **فعالیت رخدادی:** تعداد cluster/event مستقل، نه تعداد پیکسل خام.
  - **شدت:** مجموع FRP و Fire Radiative Energy تقریبی در پنجره زمانی، همراه با عدم‌قطعیت.

### مرحله C — حذف تکرار و ساخت رخداد

- حذف duplicateهای درون‌سنسوری ناشی از اسکن/مدار هم‌پوشان با قواعد مکانی–زمانی وابسته به footprint.
- خوشه‌بندی detections نزدیک در فضا و زمان به یک fire episode با الگوریتمی مانند ST‑DBSCAN یا graph connected components.
- در نمایش زنده، نقاط اصلی قابل مشاهده باشند؛ اما تقویم بر event/grid summary متکی باشد تا VIIRS صرفاً به‌خاطر پیکسل کوچک‌تر امتیاز بیشتری نگیرد.

### مرحله D — کالیبراسیون overlap

طرح اصلی:

1. زوج‌سازی مشاهده‌های نزدیک‌زمان Aqua MODIS و S‑NPP VIIRS در سال‌های overlap.
2. تجمیع هر دو روی شبکه و پنجره زمانی مشترک.
3. برازش مدل count با توزیع Negative Binomial یا hurdle model برای صفرهای زیاد؛ متغیرها شامل فصل، day/night، latitude، land cover، footprint/scan، FRP و منطقه اقلیمی.
4. مدل جداگانه یا hierarchical partial pooling برای نواحی، به‌جای یک نسبت ثابت جهانی.
5. تبدیل خروجی به یک مقیاس مرجع روشن، مثلاً «MODIS‑equivalent event activity» یا شاخص بدون واحد ۰–۱۰۰. نام مقیاس باید در UI و CSV صریح باشد.
6. bootstrap مکانی–زمانی برای فاصله اطمینان؛ جلوگیری از data leakage با جداکردن بلوک‌های سال/منطقه در train/test.

راه مکمل بسیار قوی: استفاده از محصول VIIRS 750 m که الگوریتم آن از MODIS C6 به ارث رسیده به‌عنوان **bridge product** بین MODIS 1 km و VIIRS 375 m. این محصول می‌تواند انتقال الگوریتمی را بهتر توضیح دهد، درحالی‌که VIIRS 375 m برای جزئیات عملیاتی حفظ می‌شود.

### مرحله E — شاخص تقویم و anomaly

- baseline فصلی برای هر AOI با median و MAD یا quantileها، نه صرفاً mean/std که در داده آتش skewed و zero-inflated شکننده‌اند.
- نمایش percentile و robust z-score برای هفته/ماه جاری نسبت به همان هفته/ماه در سال‌های مبنا.
- حداقل حجم نمونه و پهنای عدم‌قطعیت نمایش داده شود.
- «هشدار» به معنای anomaly مشاهده‌شده باشد، نه پیش‌بینی قطعی گسترش آتش؛ اگر forecasting اضافه شد باید مدل، horizon و validation جداگانه داشته باشد.

## ۵) آزمون‌هایی که ادعای علمی را ثابت می‌کنند

1. **آزمون شکست ۲۰۱۲:** سری خام باید جهش ناشی از ورود VIIRS را نشان دهد؛ سری harmonized نباید جهش مصنوعی مشابه داشته باشد.
2. **Temporal holdout:** چند سال overlap فقط برای آزمون نگه داشته شوند.
3. **Spatial holdout:** چند اقلیم/کشور در آموزش دیده نشوند تا تعمیم‌پذیری سنجیده شود.
4. **Sensor holdout simulation:** در دوره overlap، MODIS را پنهان و با VIIRS بازسازی کنیم و برعکس.
5. **Ablation:** مقایسه روش کامل با ratio ثابت، count خام و FRP خام.
6. **Case studies:** حداقل سه نوع رژیم متفاوت—جنگل، savanna/cropland، و منطقه صنعتی/فلر.
7. **معیارها:** MAE/MedAE، bias، Spearman correlation، coverage فاصله اطمینان و خطای تشخیص anomaly.
8. **حساسیت:** نتایج با تغییر اندازه grid، پنجره زمانی، confidence filter و تعریف cluster چقدر تغییر می‌کند؟

صفحه «Method & Evidence» داخل محصول باید نمودار before/after، نمودار calibration، بازه اطمینان، محدودیت‌ها و لینک داده/کد را نشان دهد. این صفحه برای Best Use of Science و Validity حیاتی است.

## ۶) MVP پیشنهادی وب‌اپ

### تجربه اصلی کاربر

1. کاربر منطقه را جست‌وجو یا روی نقشه رسم می‌کند.
2. سیستم پوشش داده و کیفیت آن را نشان می‌دهد.
3. تقویم heatmap از ۲۰۰۰ تاکنون باز می‌شود.
4. کاربر یک هفته/ماه را انتخاب و آن را با median، IQR و percentile تاریخی مقایسه می‌کند.
5. نقشه detections، event clusters، FRP و نوع سنسور را با امکان خاموش/روشن‌کردن لایه‌ها نشان می‌دهد.
6. کاربر CSV/GeoJSON و یک گزارش تصویری کوتاه دانلود می‌کند.

### صفحات ضروری

- **Today / Situation:** وضعیت جاری با برچسب NRT و زمان آخرین به‌روزرسانی.
- **Calendar:** تقویم ۲۵+ ساله و anomalyهای robust.
- **Compare:** raw MODIS، raw VIIRS و harmonized کنار هم؛ این صفحه ارزش علمی پروژه را در چند ثانیه ثابت می‌کند.
- **Evidence:** روش، validation، uncertainty، limitations و provenance.
- **Story:** چند رخداد واقعی و اینکه تصمیم‌گیر چه چیزی از تقویم می‌آموزد.

### دسترس‌پذیری

- پالت‌های color-vision-safe مانند Viridis/Cividis؛ رنگ تنها حامل معنا نباشد.
- keyboard navigation، tooltip متنی، contrast مناسب، و حالت reduced motion.
- واحد، timezone، processing mode و تعریف هر شاخص نزدیک نمودار نوشته شود.
- رابط دست‌کم انگلیسی و فارسی؛ معماری ترجمه از ابتدا RTL/LTR را پشتیبانی کند.

## ۷) راهبرد امتیاز و جایزه

معیارهای ارزیابی پروژه‌ها پنج موردند: **Impact، Creativity، Validity، Relevance، Presentation**. ده عنوان جایزه جهانی، معیار امتیازدهی اولیه نیستند؛ آن‌ها دسته‌های انتخاب برنده‌اند.

تمرکز پیشنهادی ما:

1. **Best Use of Science:** روش قابل‌تکرار، فرضیه روشن، validation، ablation و uncertainty.
2. **Best Use of Data:** provenance، standard + NRT، خروجی قابل دانلود و توضیح تفاوت سنسورها.
3. **Local Impact:** یک پایلوت جدی برای ایران (مثلاً زاگرس/هیرکانی) در کنار کاربرد جهانی؛ انتخاب نهایی پایلوت باید بعد از بررسی کیفیت داده و نیاز کاربر انجام شود.

پروژه نباید تلاش کند همه ده جایزه را هم‌زمان هدف بگیرد. Storytelling و طراحی قوی باید در خدمت ادعای علمی باشند.

### نگاشت به معیارهای داوری

| معیار | مدرک قابل مشاهده در نسخه نهایی |
|---|---|
| Impact | persona و سناریوی تصمیم‌گیری، پایلوت محلی، خروجی قابل استفاده |
| Creativity | bridge product + event-based harmonization + uncertainty-aware calendar |
| Validity | holdout، ablation، روش بازتولیدپذیر، محدودیت‌های صریح |
| Relevance | تمام deliverableهای رسمی: AOI، date range، calendar، anomaly، export |
| Presentation | دموی ۹۰ ثانیه‌ای با مسئله «جهش مصنوعی سنسور» و نتیجه before/after |

## ۸) چیزهایی که نباید انجام دهیم

- نمایش count خام MODIS و VIIRS در یک خط و نامیدن آن harmonized.
- استفاده از یک ضریب جهانی بدون cross-validation و uncertainty.
- آموزش مدل روی داده مصنوعی و نمایش خروجی به‌عنوان مشاهده NASA.
- استفاده از NRT برای climatology بلندمدت بدون هشدار.
- ادعای پیش‌بینی یا «نجات جان» بدون validation عملیاتی.
- نامیدن هر hotspot به‌عنوان wildfire یا burned area.
- پنهان‌کردن gap، cloud، خطای سنسور یا تغییر نسخه محصول.
- افزودن LLM صرفاً برای جذابیت؛ اگر AI استفاده می‌شود باید grounded، قابل ارزیابی و غیرضروری برای مسیر اصلی باشد.

## ۹) معماری فنی سطح بالا

- **Ingestion:** jobهای تکرارپذیر برای FIRMS standard archive و NRT، پارتیشن‌بندی بر اساس sensor/date/region.
- **Storage:** فایل‌های خام immutable + Parquet/GeoParquet تحلیلی + پایگاه مکانی برای queryهای AOI.
- **Processing:** Python، DuckDB/Polars، GeoPandas/Shapely و pipeline نسخه‌دار.
- **Modeling:** statsmodels/PyMC یا LightGBM با calibration و explainability؛ مدل آماری ساده و معتبر بر مدل پیچیده بدون مدرک ترجیح دارد.
- **API:** query خلاصه‌های precomputed؛ response شامل value، uncertainty، coverage و provenance.
- **Frontend:** React/Next + MapLibre/Deck.gl + تقویم Canvas/SVG؛ download و shareable URL.
- **Reproducibility:** Docker، data dictionary، model card، test fixtures و notebook بازتولید نتایج اصلی.

## ۱۰) تصمیم‌های باز قبل از پیاده‌سازی

1. AOI پایلوت محلی ایران و دو AOI جهانی برای validation.
2. انتخاب مقیاس مرجع نهایی: event-equivalent، FRP-based یا شاخص ترکیبی.
3. دسترسی به FIRMS MAP_KEY و Earthdata Login.
4. سقف زیرساخت و محل deploy.
5. ترکیب تیم و تقسیم نقش علم داده، بک‌اند، فرانت‌اند، طراحی و روایت.

## ۱۱) منابع اصلی مطالعه‌شده

- [صورت مسئله رسمی NASA Space Apps 2026](https://www.spaceappschallenge.org/2026/challenges/harmonization-of-modis-and-viirs-hot-spots/)
- [NASA FIRMS Active Fire Data](https://firms.modaps.eosdis.nasa.gov/content/active_fire/)
- [FIRMS Area API](https://firms.modaps.eosdis.nasa.gov/api/area/)
- [FIRMS Data Availability API](https://firms.modaps.eosdis.nasa.gov/api/data_availability/)
- [VIIRS Collection 2 Active Fire 375 m User Guide](https://www.earthdata.nasa.gov/s3fs-public/2024-07/VIIRS_C2_AF-375m_User_Guide_1.0.pdf)
- [MODIS Collection 6 Active Fire Product User Guide](https://www.earthdata.nasa.gov/s3fs-public/imported/MODIS_C6_Fire_User_Guide_A.pdf)
- [FIRMS VIIRS attribute description](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html)
- [FIRMS MODIS attribute description](https://firms.modaps.eosdis.nasa.gov/descriptions/FIRMS_MODIS_Firehotspots.html)
- [Schroeder et al. (2014), VIIRS 375 m active fire algorithm](https://doi.org/10.1016/j.rse.2013.12.008)
- [Li et al. (2018), comparison of VIIRS and MODIS FRP](https://doi.org/10.1029/2017JD027823)
- [NASA Space Apps Awards](https://www.spaceappschallenge.org/2025/awards/)

## جمع‌بندی اجرایی

بهترین نسخه این پروژه یک داشبورد آتش معمولی نیست. هسته برنده آن یک **پل علمی قابل‌اثبات بین دو نسل سنسور** است که به یک تصمیم ساده پاسخ می‌دهد: «فعالیت این هفته در این منطقه واقعاً غیرعادی است، یا فقط سنسور جدیدتر جزئیات بیشتری دیده است؟»

اگر قبل از زیباسازی رابط، این سؤال را با overlap calibration، event construction، uncertainty و validation پاسخ دهیم، پروژه هم‌زمان در Science، Data، Validity و Relevance قوی خواهد بود.
