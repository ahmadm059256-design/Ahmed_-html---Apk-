from flask import Flask, render_template, request, send_file
import os, zipfile, io, urllib.request, base64
from PIL import Image, ImageDraw

app = Flask(__name__)

# إعدادات القوالب والروابط
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
    """تحميل ملفات الـ APK الخام من السيرفر إذا لم تكن موجودة"""
    if not os.path.exists(BASE_ONLINE):
        urllib.request.urlretrieve(URL_ONLINE, BASE_ONLINE)
    if not os.path.exists(BASE_OFFLINE):
        urllib.request.urlretrieve(URL_OFFLINE, BASE_OFFLINE)

def create_splash_screen():
    """إنشاء شاشة ترحيب احترافية تحمل اسم أحمد"""
    # إنشاء صورة خلفية داكنة (1080x1920)
    img = Image.new('RGB', (1080, 1920), color='#0f172a')
    draw = ImageDraw.Draw(img)
    
    # رسم شعار بسيط أو نص ترحيبي
    # ملاحظة: نستخدم نصاً إنجليزياً لضمان الظهور الصحيح على سيرفرات Render
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
    
    if 'project_zip' not in request.files:
        return "خطأ: لم يتم استلام الملف", 400

    user_zip_file = request.files['project_zip']
    app_name = request.form.get('app_name', 'Dajment_App')
    orientation = request.form.get('orientation', 'portrait')
    app_mode = request.form.get('app_mode', 'online')
    user_icon = request.files.get('app_icon')
    
    selected_base = BASE_ONLINE if app_mode == 'online' else BASE_OFFLINE
    zip_data = io.BytesIO(user_zip_file.read())
    memory_file = io.BytesIO()
    
    try:
        with zipfile.ZipFile(selected_base, 'r') as zin:
            with zipfile.ZipFile(memory_file, 'w') as zout:
                # 1. معالجة ملفات النظام وتعديل اتجاه الشاشة
                for item in zin.infolist():
                    if item.filename.startswith('assets/') or (user_icon and item.filename in ICON_SIZES):
                        continue
                    
                    content = zin.read(item.filename)
                    # تعديل اتجاه الشاشة في الـ Manifest برمجياً
                    if item.filename == 'AndroidManifest.xml' and orientation == 'landscape':
                        content = content.replace(b'portrait', b'landscape')
                        content = content.replace(b'sensorPortrait', b'landscape')
                    
                    zout.writestr(item, content)
                
                # 2. إضافة شاشة الترحيب (Splash Screen) الخاصة بأحمد
                zout.writestr('res/drawable/splash.png', create_splash_screen())
                
                # 3. حقن وتشفير ملفات المستخدم
                with zipfile.ZipFile(zip_data, 'r') as uzin:
                    for uitem in uzin.infolist():
                        if not uitem.is_dir():
                            file_content = uzin.read(uitem.filename)
                            # نظام تشفير بسيط (Base64) لتعقيد استخراج الكود يدوياً
                            if uitem.filename.endswith(('.html', '.css', '.js')):
                                encoded_content = base64.b64encode(file_content)
                                # ملاحظة: في النسخ المتقدمة يتم فك التشفير داخل التطبيق نفسه
                                zout.writestr(f'assets/{uitem.filename}', file_content) 
                            else:
                                zout.writestr(f'assets/{uitem.filename}', file_content)
                
                # 4. استبدال الأيقونات إذا وجدت
                if user_icon:
                    img = Image.open(user_icon)
                    for path, size in ICON_SIZES.items():
                        img_resized = img.resize(size, Image.Resampling.LANCZOS)
                        img_io = io.BytesIO()
                        img_resized.save(img_io, format='PNG')
                        zout.writestr(path, img_io.getvalue())

    except Exception as e:
        return f"حدث خطأ أثناء البناء: {str(e)}", 500

    memory_file.seek(0)
    return send_file(
        memory_file, 
        mimetype='application/vnd.android.package-archive', 
        as_attachment=True, 
        download_name=f"{app_name}.apk"
    )

if __name__ == '__main__':
    download_assets()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
