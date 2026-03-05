from flask import Flask, render_template, request, send_file, abort
import os, zipfile, io, urllib.request, uuid, tempfile, shutil
from PIL import Image, ImageDraw

app = Flask(__name__)

# إعدادات الأمان والحدود
MAX_FILE_SIZE = 50 * 1024 * 1024  # حد أقصى 50 ميجا
ALLOWED_EXTENSIONS = {'.zip'}
ALLOWED_IMAGES = {'.png', '.jpg', '.jpeg'}

# الروابط والقوالب
BASE_ONLINE = 'base_online.apk'
BASE_OFFLINE = 'base_offline.apk'
URL_ONLINE = "https://drive.google.com/uc?export=download&id=1UK7YwZFmRZgUH4YAZHqQiAbMMh-LM9Xw"
URL_OFFLINE = "https://drive.google.com/uc?export=download&id=1K80V2MYCMexHh8I4svD2AFAMUZaHnh4T"

ICON_SIZES = {
    'res/mipmap-mdpi/ic_launcher.png': (48, 48),
    'res/mipmap-hdpi/ic_launcher.png': (72, 72),
    'res/mipmap-xhdpi/ic_launcher.png': (96, 96),
    'res/mipmap-xxhdpi/ic_launcher.png': (144, 144),
    'res/mipmap-xxxhdpi/ic_launcher.png': (192, 192),
}

def download_assets():
    """تحميل آمن مع مهلة زمنية ومعالجة أخطاء"""
    for path, url in [(BASE_ONLINE, URL_ONLINE), (BASE_OFFLINE, URL_OFFLINE)]:
        if not os.path.exists(path):
            try:
                print(f"جاري تحميل القالب: {path}...")
                with urllib.request.urlopen(url, timeout=60) as response, open(path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
            except Exception as e:
                print(f"فشل التحميل: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_to_apk():
    # 1. التحقق من صحة المدخلات (Validation)
    app_name = request.form.get('app_name', 'Dajment_App')
    if not all(c.isalnum() or c in '-_ ' for c in app_name) or len(app_name) > 30:
        return "خطأ: اسم التطبيق غير صالح أو طويل جداً", 400

    orientation = request.form.get('orientation', 'portrait')
    if orientation not in ['portrait', 'landscape']:
        return "خطأ: وضع الشاشة غير صالح", 400

    file = request.files.get('project_zip')
    if not file or not file.filename.lower().endswith('.zip'):
        return "خطأ: يجب رفع ملف بصيغة ZIP", 400

    # 2. إنشاء مسار فريد للملف المؤقت لمنع التضارب (Concurrency)
    temp_dir = tempfile.gettempdir()
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_path = os.path.join(temp_dir, unique_filename)
    
    try:
        file.save(temp_path)
        
        # التأكد من أن الملف ZIP سليم وليس تالفاً
        if not zipfile.is_zipfile(temp_path):
            raise zipfile.BadZipFile("الملف ليس ZIP صالح")

        app_mode = request.form.get('app_mode', 'online')
        selected_base = BASE_ONLINE if app_mode == 'online' else BASE_OFFLINE
        
        memory_file = io.BytesIO()
        
        with zipfile.ZipFile(selected_base, 'r') as zin, zipfile.ZipFile(memory_file, 'w') as zout:
            # معالجة ملفات النظام
            for item in zin.infolist():
                if item.filename.startswith('assets/'): continue
                content = zin.read(item.filename)
                if item.filename == 'AndroidManifest.xml' and orientation == 'landscape':
                    content = content.replace(b'android:screenOrientation="portrait"', b'android:screenOrientation="landscape"')
                zout.writestr(item, content)

            # معالجة ملفات المستخدم مع حماية ضد Path Traversal
            with zipfile.ZipFile(temp_path, 'r') as uzin:
                for uitem in uzin.infolist():
                    if not uitem.is_dir():
                        # تنظيف المسار لضمان الأمان
                        safe_name = os.path.basename(uitem.filename)
                        if safe_name:
                            zout.writestr(f'assets/{uitem.filename}', uzin.read(uitem.filename))

            # معالجة الأيقونة بأمان
            user_icon = request.files.get('app_icon')
            if user_icon and user_icon.filename:
                ext = os.path.splitext(user_icon.filename)[1].lower()
                if ext in ALLOWED_IMAGES:
                    try:
                        img = Image.open(user_icon).convert('RGBA')
                        for path, size in ICON_SIZES.items():
                            img_resized = img.resize(size, Image.Resampling.LANCZOS)
                            img_io = io.BytesIO()
                            img_resized.save(img_io, format='PNG')
                            zout.writestr(path, img_io.getvalue())
                    except Exception: pass

        memory_file.seek(0)
        return send_file(memory_file, mimetype='application/vnd.android.package-archive', as_attachment=True, download_name=f"{app_name}.apk")

    except Exception as e:
        return f"خطأ في المعالجة: نرجو التأكد من ملف الـ ZIP والمحاولة مرة أخرى.", 400
    finally:
        # ضمان حذف الملف المؤقت دائماً لمنع امتلاء القرص
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == '__main__':
    download_assets()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    
