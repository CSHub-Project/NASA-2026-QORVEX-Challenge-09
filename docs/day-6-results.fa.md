# گزارش روز ششم — بستهٔ داوری و ارائه

## هدف

روز ششم پروژه را از «محصول علمی قابل‌دمو» به «ارسال قابل‌داوری» تبدیل می‌کند. مبنا پنج معیار رسمی داوری Space Apps 2026 است: Impact، Creativity، Validity، Relevance و Presentation. ده Global Award به‌عنوان دستهٔ انتخاب برنده در نظر گرفته شده‌اند، نه جایگزین این پنج معیار.

## خروجی‌های وب‌اپ

- Judge Mode پنج‌مرحله‌ای و دوزبانه؛
- مسیر ۹۰ ثانیه‌ای مسئله → محصول → اعتبار → معماری → اثر صادقانه؛
- کنترل با دکمه، Escape و کلیدهای جهت؛
- focus بازگردانده‌شده به دکمهٔ آغاز پس از پایان؛
- نمودار معماری منبع تا محصول در خود صفحه؛
- Decision Brief مبتنی بر پنج معیار با لینک به مدرک قابل‌مشاهده؛
- لینک منابع رسمی چالش، FIRMS، VIIRS Land و کد منبع؛
- حفظ RTL، دسترس‌پذیری صفحه‌کلید و طراحی واکنش‌گرا.

## بستهٔ Submission

پوشهٔ `submission/` شامل این تحویل‌هاست:

- `project-page.en.md`: متن انگلیسی آمادهٔ copy/paste صفحهٔ پروژه؛
- `demo-script.en.md`: سناریوی دقیق سه‌دقیقه‌ای انگلیسی؛
- `demo-script.fa.md`: نسخهٔ فارسی برای تمرین تیم؛
- `architecture.md`: معماری Mermaid، trust boundary و failure control؛
- `judge-scorecard.md`: خودارزیابی پنج معیار با red flag؛
- `final-checklist.fa.md`: چک‌لیست ارسال، آزمون، علم و اجرای ارائه؛
- `README.md`: ترتیب استفاده و قانون ادعاهای کمی.

## تصمیم‌های روایی

1. داستان با «شکست شمارش خام در تغییر حسگر» شروع می‌شود، نه با نام الگوریتم.
2. اولین نمایش محصول، تفاوت no coverage و zero است؛ چون هم علمی است و هم سریع فهمیده می‌شود.
3. عدد ۳۲٪ تنها پس از توضیح split زمانی گفته می‌شود.
4. انتقال مکانی به‌عنوان دفاع در برابر حفظ‌کردن منطقه نمایش داده می‌شود.
5. FRP و نبود نقش هشدار اضطراری عمداً در ارائه گفته می‌شوند تا اعتماد بالا برود.
6. جایگاه اصلی Global Award، Best Use of Science و Best Use of Data است؛ Storytelling و Local Impact نقش پشتیبان دارند.

## ادعاهای مجاز در ارائه

- داده: ۲٬۵۲۳٬۲۵۷ مشاهده، چهار سال، سه منطقه، ۴٬۴۴۴ pass؛
- آزمون ۲۰۲۰: WAPE شمارش `1.226 → 0.833`، بهبود ۳۲٫۰٪؛
- Spearman شمارش `0.045 → 0.635`؛
- bootstrap: `[-0.272, -0.226]` با ۵۰۰ تکرار؛
- انتقال مکانی: ۳۷٫۰٪، ۱۱٫۰٪ و ۴۴٫۹٪ بهبود WAPE؛
- محصول: calendar و CSV حساس به پوشش.

ادعاهای غیرمجاز: پیش‌بینی آتش، هشدار زنده، پوشش جهانی، operational FRP یا اثبات causal impact.

## منابع رسمی بررسی‌شده

- صورت چالش ۲۰۲۶: `https://www.spaceappschallenge.org/2026/challenges/harmonization-of-modis-and-viirs-hot-spots/`
- صفحهٔ رسمی رویداد و مهلت ۱۵ نوامبر ۲۰۲۶: `https://www.spaceappschallenge.org/2026/`
- NASA FIRMS science-quality guidance: `https://firms.modaps.eosdis.nasa.gov/content/active_fire/`
- NASA VIIRS active-fire continuity: `https://viirsland.gsfc.nasa.gov/Products/NASA/FireESDR.html`

## معیار پایان روز ششم

- متن Submission آماده و بدون ادعای اثبات‌نشده باشد؛
- سناریوی دمو زمان‌دار و دارای fallback باشد؛
- پنج معیار داوری به proof واقعی نگاشت شوند؛
- Judge Mode در مرورگر، انگلیسی و فارسی، صفحه‌کلید و موبایل بررسی شود؛
- build و همهٔ تست‌ها موفق باشند؛
- تغییرات در GitHub کامیت و push شوند؛
- انتشار خصوصی فقط در صورت بازگشت اتصال source repository انجام شود و هیچ URL ثبت‌شده اما منتشرنشده به‌عنوان live معرفی نشود.
