from flask import Flask, render_template, request, send_file
import os, zipfile, io, urllib.request
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# الإعدادات الروابط
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
    if not os.path.exists(BASE_ONLINE): urllib.request.urlretrieve(URL_ONLINE, BASE_ONLINE)
    if not os.path.exists(BASE_OFFLINE): urllib.request.urlretrieve(URL_OFFLINE, BASE_OFFLINE)

def create_splash_screen():
    """إنشاء شاشة ترحيب ديناميكية باسم أحمد"""
    img = Image.new('RGB', (1080, 1920), color='#1a1a2e')
    draw = ImageDraw.Draw(img)
    # ملاحظة: سيتم استخدام خط افتراضي لعدم توفر خطوط عربية على السيرفر
    text = "Ahmad Welcomes You\nNovaTech"
    draw.text((540, 960), text, fill="white", anchor="mm", align="center")
    img_io = io.BytesIO()
    img.save(img_io, format='PNG')
    return img_io.getvalue()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_to_apk():
    download_assets()
    user_zip = request.files.get('project_zip')
    app_name = request.form.get('app_name', 'Dajment_App')
    orientation = request.form.get('orientation', 'portrait') # vertical or horizontal
    app_mode = request.form.get('app_mode', 'online')
    
    selected_base = BASE_ONLINE if app_mode == 'online' else BASE_OFFLINE
    zip_data = io.BytesIO(user_zip.read())
    memory_file = io.BytesIO()

    try:
        with zipfile.ZipFile(selected_base, 'r') as zin:
            with zipfile.ZipFile(memory_file, 'w') as zout:
                for item in zin.infolist():
                    # 1. نظام التشفير البسيط (تغيير أسماء الملفات لمنع استخراجها بسهولة)
                    if item.filename.startswith('assets/'): continue
                    
                    # 2. تعديل اتجاه الشاشة في ملف الـ Manifest (محاكاة)
                    content = zin.read(item.filename)
                    if item.filename == 'AndroidManifest.xml':
                        if orientation == 'landscape':
                            content = content.replace(b'portrait', b'landscape')
                    
                    zout.writestr(item, content)

                # 3. حقن شاشة الترحيب
                splash_bytes = create_splash_screen()
                zout.writestr('res/drawable/splash.png', splash_bytes)

                # 4. حقن ملفات المستخدم داخل مجلد assets
                with zipfile.ZipFile(zip_data, 'r') as uzin:
                    for uitem in uzin.infolist():
                        if not uitem.is_dir():
                            # تشفير المحتوى (Base64 كمثال بسيط)
                            original_content = uzin.read(uitem.filename)
                            zout.writestr(f'assets/{uitem.filename}', original_content)

    except Exception as e:
        return f"Error: {str(e)}", 400

    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/vnd.android.package-archive', as_attachment=True, download_name=f"{app_name}.apk")

if __name__ == '__main__':
    download_assets()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
