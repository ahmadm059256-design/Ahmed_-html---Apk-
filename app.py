from flask import Flask, render_template, request, send_file
import os
import zipfile
import io
import urllib.request
from PIL import Image

app = Flask(__name__)

# أسماء الملفات التي سيتم إنشاؤها على السيرفر
BASE_ONLINE = 'base_online.apk'
BASE_OFFLINE = 'base_offline.apk'

# الروابط المباشرة لملفاتك من Google Drive
URL_ONLINE = "https://drive.google.com/uc?export=download&id=1UK7YwZFmRZgUH4YAZHqQiAbMMh-LM9Xw"
URL_OFFLINE = "https://drive.google.com/uc?export=download&id=1K80V2MYCMexHh8I4svD2AFAMUZaHnh4T"

# إعدادات الأيقونات القياسية لأندرويد
ICON_SIZES = {
    'res/mipmap-mdpi/ic_launcher.png': (48, 48),
    'res/mipmap-hdpi/ic_launcher.png': (72, 72),
    'res/mipmap-xhdpi/ic_launcher.png': (96, 96),
    'res/mipmap-xxhdpi/ic_launcher.png': (144, 144),
    'res/mipmap-xxxhdpi/ic_launcher.png': (192, 192),
}

def download_assets():
    """تحميل القوالب الكبيرة من الروابط الخارجية إذا لم تكن موجودة"""
    if not os.path.exists(BASE_ONLINE):
        print("جاري جلب قالب الأونلاين (70MB)...")
        urllib.request.urlretrieve(URL_ONLINE, BASE_ONLINE)
    
    if not os.path.exists(BASE_OFFLINE):
        print("جاري جلب قالب الأوفلاين (70MB)...")
        urllib.request.urlretrieve(URL_OFFLINE, BASE_OFFLINE)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_to_apk():
    download_assets()
    
    if 'project_zip' not in request.files:
        return "خطأ: يرجى رفع ملف المشروع", 400

    user_zip_file = request.files['project_zip']
    new_app_name = request.form.get('app_name', 'Dajment_App')
    user_icon = request.files.get('app_icon')
    app_mode = request.form.get('app_mode', 'online')
    selected_base = BASE_ONLINE if app_mode == 'online' else BASE_OFFLINE

    zip_data = io.BytesIO(user_zip_file.read())
    memory_file = io.BytesIO()
    
    try:
        with zipfile.ZipFile(selected_base, 'r') as zin:
            with zipfile.ZipFile(memory_file, 'w') as zout:
                for item in zin.infolist():
                    if item.filename.startswith('assets/') or (user_icon and item.filename in ICON_SIZES):
                        continue
                    zout.writestr(item, zin.read(item.filename))
                
                try:
                    with zipfile.ZipFile(zip_data, 'r') as uzin:
                        for uitem in uzin.infolist():
                            if not uitem.is_dir():
                                zout.writestr(f'assets/{uitem.filename}', uzin.read(uitem.filename))
                except Exception:
                    return "خطأ: الملف المرفوع غير صالح. تأكد من ضغطه بصيغة .zip وتسميته بالإنجليزية.", 400
                
                if user_icon:
                    img = Image.open(user_icon)
                    for path, size in ICON_SIZES.items():
                        img_resized = img.resize(size, Image.Resampling.LANCZOS)
                        img_io = io.BytesIO()
                        img_resized.save(img_io, format='PNG')
                        zout.writestr(path, img_io.getvalue())

    except Exception as e:
        return f"حدث خطأ داخلي أثناء البناء: {str(e)}", 500

    memory_file.seek(0)
    return send_file(
        memory_file, 
        mimetype='application/vnd.android.package-archive', 
        as_attachment=True, 
        download_name=f"{new_app_name}.apk"
    )

if __name__ == '__main__':
    download_assets()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
