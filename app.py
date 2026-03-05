from flask import Flask, render_template, request, send_file
import os, zipfile, io, urllib.request, base64
from PIL import Image, ImageDraw

app = Flask(__name__)

# إعدادات الروابط والقوالب
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
    """تحميل القوالب الأساسية إذا لم تكن موجودة"""
    if not os.path.exists(BASE_ONLINE):
        urllib.request.urlretrieve(URL_ONLINE, BASE_ONLINE)
    if not os.path.exists(BASE_OFFLINE):
        urllib.request.urlretrieve(URL_OFFLINE, BASE_OFFLINE)

def create_splash_screen():
    """إنشاء شاشة ترحيب احترافية تحمل اسم أحمد"""
    img = Image.new('RGB', (1080, 1920), color='#0f172a')
    draw = ImageDraw.Draw(img)
    text = "Ahmad Welcomes You\nPowered by NovaTech"
    draw.text((540, 960), text, fill="#6366f1", anchor="mm", align="center")
    img_io = io.BytesIO()
    img.save(img_io, format='PNG')
    return img_io.getvalue()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_to_apk():
    download_assets()
    
    file = request.files.get('project_zip')
    if not file:
        return "خطأ: لم يتم استلام الملف المضغوط", 400

    # الحل السحري لهاتفك: حفظ الملف مؤقتاً لتجنب أخطاء الذاكرة والقراءة
    temp_path = "temp_user_project.zip"
    file.save(temp_path)

    app_name = request.form.get('app_name', 'Dajment_App')
    orientation = request.form.get('orientation', 'portrait')
    app_mode = request.form.get('app_mode', 'online')
    user_icon = request.files.get('app_icon')
    
    selected_base = BASE_ONLINE if app_mode == 'online' else BASE_OFFLINE
    memory_file = io.BytesIO()
    
    try:
        with zipfile.ZipFile(selected_base, 'r') as zin:
            with zipfile.ZipFile(memory_file, 'w') as zout:
                # 1. نسخ ملفات النظام وتعديل الاتجاه
                for item in zin.infolist():
                    if item.filename.startswith('assets/') or (user_icon and item.filename in ICON_SIZES):
                        continue
                    content = zin.read(item.filename)
                    if item.filename == 'AndroidManifest.xml' and orientation == 'landscape':
                        content = content.replace(b'portrait', b'landscape')
                    zout.writestr(item, content)
                
                # 2. إضافة شاشة ترحيب أحمد
                zout.writestr('res/drawable/splash.png', create_splash_screen())
                
                # 3. محاولة فتح ملف المستخدم ومعالجته
                with zipfile.ZipFile(temp_path, 'r') as uzin:
                    for uitem in uzin.infolist():
                        if not uitem.is_dir():
                            zout.writestr(f'assets/{uitem.filename}', uzin.read(uitem.filename))
                
                # 4. معالجة الأيقونة
                if user_icon:
                    img = Image.open(user_icon)
                    for path, size in ICON_SIZES.items():
                        img_resized = img.resize(size, Image.Resampling.LANCZOS)
                        img_io = io.BytesIO()
                        img_resized.save(img_io, format='PNG')
                        zout.writestr(path, img_io.getvalue())

        # حذف الملف المؤقت بعد النجاح
        if os.path.exists(temp_path): os.remove(temp_path)

    except Exception as e:
        if os.path.exists(temp_path): os.remove(temp_path)
        return f"حدث خطأ فني: {str(e)}. تأكد من ضغط الملف بـ ZArchiver.", 400

    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/vnd.android.package-archive', as_attachment=True, download_name=f"{app_name}.apk")

if __name__ == '__main__':
    download_assets()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
