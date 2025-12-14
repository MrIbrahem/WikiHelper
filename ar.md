أنت وكيل ذكاء اصطناعي مسؤول عن تصميم وتنفيذ تطبيق ويب داخلي/خفيف لإدارة نصوص ويكي واستخراج/استعادة وسوم <ref> باستخدام مكتبة wikitextparser (wtp). نفّذ التطبيق ببايثون + Flask مع واجهة HTML بسيطة (Jinja2) دون أطر واجهات ثقيلة. اتبع الخطة أدناه حرفيًا، وركّز على السلامة والاعتمادية وقابلية التشغيل.

========================================
1) الهدف العام (Core Workflow)
========================================
أنشئ تطبيق Flask يتيح للمستخدم:
A) إدخال "عنوان" + "نص ويكي طويل" عبر فورم.
B) عند الإرسال:
   1) إنشاء مجلد جديد باسم العنوان داخل مسار رئيسي ROOT_DIR يحدد عبر متغيرات البيئة.
   2) إنشاء 4 ملفات داخل المجلد:
      (1) original.wiki   : النص الأصلي بدون أي تعديل (يكتب مرة واحدة فقط).
      (2) refs.json       : قاموس المراجع المستخرجة من وسوم <ref> (يكتب مرة واحدة فقط).
      (3) restored.wiki   : ملف قابل للتحديث يمثل ناتج الاستعادة بعد عمل المستخدم (يُحدَّث لاحقًا فقط).
      (4) editable.wiki   : ملف معدل يمثل النص بعد إزالة المراجع واستبدالها بـ placeholders مثل [ref1]… (يُحدَّث بواسطة المستخدم فقط).
   3) بعد الإنشاء: إعادة توجيه المستخدم لصفحة تحرير تعرض textarea تحتوي محتوى الملف (4).

C) في صفحة التحرير:
   - المستخدم يعدّل النص داخل textarea (يمثل file 4 فقط).
   - عند الإرسال:
     1) تحديث editable.wiki بمحتوى textarea.
     2) استعادة وسوم <ref> إلى النص اعتمادًا على refs.json.
     3) حفظ الناتج المستعاد في restored.wiki (file 3).
     4) عرض الناتج للمستخدم (يمكن عرضه في textarea منفصلة أو pre block).

D) صفحة رئيسية Dashboard:
   - تعرض قائمة المجلدات الموجودة داخل ROOT_DIR مرتبة (الأحدث أولًا).
   - لكل مجلد: روابط لصفحات:
     - Edit (تحرير file 4 ثم توليد file 3)
     - Browse (عرض الملفات الأربعة ونسخ محتواها/تحميلها)
     - Meta (معلومات: تاريخ الإنشاء، حجم الملفات، عدد المراجع)

========================================
2) القيود والمتطلبات
========================================
- ROOT_DIR إلزامي عبر متغير بيئة مثل: WIKI_WORK_ROOT.
- يجب منع Path Traversal:
  - اسم المجلد يُشتق من العنوان عبر slugify صارم (أحرف/أرقام/شرطة/شرطة سفلية فقط).
  - لا تسمح بـ ".." أو "/" أو "\" أو أسماء محجوزة.
- في مرحلة الإنشاء الأولى:
  - original.wiki و refs.json يكتبان مرة واحدة فقط.
  - إذا كان المجلد موجودًا بالفعل: لا تعدّل (1) و(2)، لكن اسمح بالانتقال للتحرير أو إظهار رسالة.
- المستخدم يُسمح له بتعديل editable.wiki فقط (عبر الواجهة). أي تعديل للملفات الأخرى يتم برمجيًا فقط.
- استخدم wikitextparser (wtp) لاستخراج وسوم ref من النص:
  - تعامل مع <ref>...</ref> و <ref ... />.
  - احفظ النص الأصلي للوسم بالاعتماد على span للحفاظ على التنسيق حرفيًا.
  - استبدل كل وسم بـ placeholder ثابت مثل [ref1], [ref2] حسب ترتيب ظهوره في النص.
- الاستعادة:
  - استبدل placeholders في editable.wiki إلى وسومها الأصلية من refs.json.
  - إذا وُجد placeholder بدون قيمة في refs.json اتركه كما هو.
- الأمن:
  - استخدم SECRET_KEY من متغير بيئة.
  - حدّد MAX_CONTENT_LENGTH (مثلاً 2-5MB) لمنع إدخال نصوص ضخمة جدًا.
  - فعّل CSRF (Flask-WTF) أو بديل بسيط إذا لزم.
- التشغيل:
  - وفر requirements.txt
  - وفر ملف .env.example
  - وفر README تشغيل مختصر

========================================
3) هيكلة المشروع (Project Structure)
========================================
أنشئ مشروعًا بهذه البنية:

project/
  app.py
  config.py
  requirements.txt
  .env.example
  README.md
  templates/
    base.html
    index.html
    new.html
    edit.html
    browse.html
    view_file.html
  static/
    style.css
  wikiops/
    __init__.py
    refs.py        # extraction & restoration logic using wtp
    storage.py     # filesystem operations, safe paths, slugify, atomic writes
    models.py      # optional dataclasses for workspace metadata

========================================
4) تصميم البيانات (Workspace Folder Layout)
========================================
داخل ROOT_DIR/<slug_title>/:
  original.wiki
  refs.json
  restored.wiki
  editable.wiki
  meta.json  (اختياري لكن موصى به)
- meta.json يتضمن: title_original, slug, created_at, updated_at, refs_count

========================================
5) منطق wtp (Extraction & Restoration)
========================================
5.1 extraction:
- parse = wtp.parse(text)
- tags = [t for t in parse.get_tags() if (t.name or '').lower() == 'ref']
- sort tags by t.span[0]
- refs_map: {"ref1": text[start:end], ...}
- replacements list: (start,end,"[refN]")
- apply replacements in reverse order
- return modified_text, refs_map

5.2 restoration:
- regex: r"\[(ref\d+)\]"
- replace with refs_map[key] if exists else keep as-is

========================================
6) عمليات التخزين (Filesystem Storage)
========================================
- اكتب helpers:
  - slugify_title(title: str) -> str
  - safe_workspace_path(root: Path, slug: str) -> Path (resolve + check within root)
  - atomic_write(path, content): write to temp then replace
  - read_text(path)
- عند إنشاء Workspace:
  - mkdir(workspace, exist_ok=True)
  - إذا لم يوجد original.wiki:
      write original.wiki = input_text
      extract -> editable_text + refs_map
      write refs.json
      write editable.wiki = editable_text
      write restored.wiki = "" (أو original.wiki كقيمة ابتدائية حسب اختيارك)
      write meta.json
  - إذا موجود:
      لا تعيد استخراج ولا تعيد كتابة original/refs
      اسمح بالانتقال لصفحة edit

========================================
7) مسارات Flask (Routes)
========================================
- GET / : dashboard قائمة workspaces
- GET /new : صفحة إنشاء workspace (title + wikitext)
- POST /new :
    - validate
    - create workspace
    - redirect to /w/<slug>/edit
- GET /w/<slug>/edit :
    - load editable.wiki to textarea
    - optionally load restored.wiki to preview
- POST /w/<slug>/edit :
    - update editable.wiki
    - restore -> restored_text
    - write restored.wiki
    - update meta.json updated_at
    - render edit.html مع preview للمستعاد
- GET /w/<slug>/browse :
    - قائمة الملفات الأربعة + meta (روابط عرض/تحميل)
- GET /w/<slug>/file/<name> :
    - عرض محتوى ملف محدد (name محصور في whitelist: original, refs, editable, restored, meta)
- GET /w/<slug>/download/<name> (اختياري):
    - تنزيل الملف

========================================
8) واجهة المستخدم (UI)
========================================
- base.html: Header + nav (Home / New)
- index.html: جدول workspaces: slug/title/updated_at/links
- new.html: فورم title + textarea للنص
- edit.html:
  - textarea كبيرة لمحتوى editable.wiki (file 4)
  - زر "حفظ + توليد النسخة المستعادة"
  - قسم Preview يعرض restored.wiki (file 3)
- browse.html: روابط للملفات الأربعة + meta
- view_file.html: عرض محتوى ملف مع زر نسخ

========================================
9) التحقق من صحة الإدخال (Validation)
========================================
- title:
  - non-empty, length limit (مثلاً 120)
- text:
  - non-empty, length limit (مع MAX_CONTENT_LENGTH)
- slug:
  - derived only from title
  - إذا slug فارغ بعد التنقية -> ارفض واطلب عنوانًا صالحًا

========================================
10) اختبارات سريعة (Optional but Recommended)
========================================
- pytest tests for:
  - extraction handles multiline refs
  - extraction handles self-closing <ref name="x" />
  - restoration replaces placeholders correctly
  - storage slugify safety
- إن لم تُنفّذ اختبارات، على الأقل نفّذ self-check endpoint أو CLI sanity script.

========================================
11) التشغيل والتوثيق
========================================
- requirements.txt:
  - Flask
  - python-dotenv
  - wikitextparser
  - Flask-WTF (إذا استخدمت CSRF)
- .env.example:
  - WIKI_WORK_ROOT=./data
  - FLASK_SECRET_KEY=change-me
  - FLASK_DEBUG=1
- README.md:
  - خطوات التثبيت والتشغيل
  - توضيح الملفات الأربعة
  - ملاحظات أمنية (الـ slug + limits)

========================================
12) معايير التسليم (Definition of Done)
========================================
- يمكن تشغيل التطبيق محليًا ويعمل المسار الكامل:
  - إنشاء workspace -> توليد الملفات الأربعة -> تحرير file 4 -> توليد file 3 -> تصفح الملفات
- لا يحدث أي تعديل على original.wiki و refs.json بعد الإنشاء الأول
- يمنع أي حقن مسارات أو خروج عن ROOT_DIR
- يعالج وسوم ref المفتوحة وذاتية الإغلاق بواسطة wtp كما هو موصوف

ابدأ التنفيذ مباشرة وفق هذه الخطة. لا تسأل المستخدم أسئلة متابعة. إذا واجهت قرارًا غير محدد، اختر الافتراضي الأكثر أمانًا ودوّن ذلك في README.
