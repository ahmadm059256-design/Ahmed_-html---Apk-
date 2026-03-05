from flask import Flask, render_template, request, send_file
import os
import zipfile
import io
import urllib.request
from PIL import Image

app = Flask(__name__)

# أسماء الملفات التي سيستخدمها السيرفر محلياً
BASE_ONLINE = 'base_online.apk'
BASE_OFFLINE = 'base_offline.apk'

# --- تنبيه هام يا أحمد ---
# استبدل الروابط أدناه بروابط التحميل المباشرة التي حصلت عليها من Google Drive
URL_ONLINE = "ضع_رابط_الأونلاين_المباشر_هنا"
URL_OFFLINE = "ضع_رابط_الأوفلاين_المباشر_هنا"

# إعدادات أيقونات أندرويد القياسية
ICON_SIZES = {
    'res/mipmap-mdpi/ic_launcher.png': (48, 48),
    'res/mipmap-hdpi/ic_launcher.png': (72, 72),
    'res/mipmap-xhdpi/ic_launcher.png': (96, 96),
    'res/mipmap-xxhdpi/ic_launcher.png': (144, 144),
    'res/mipmap-xxxhdpi/ic_launcher.png': (192, 192),
}

def download_assets():
    """تحميل القوالب الكبيرة من الروابط الخارجية إذا لم تكن موجودة"""
    if not os.path.exists(BASE_ONLINE) and URL_ONLINE.startswith("http"):
        print("جاري جلب قالب الأونلاين (70MB)...")
        urllib.request.urlretrieve(URL_ONLINE, BASE_ONLINE)
    
    if not os.path.exists(BASE_OFFLINE) and URL_OFFLINE.startswith("http"):
        print("جاري جلب قالب الأوفلاين (70MB)...")
        urllib.request.urlretrieve(URL_OFFLINE, BASE_OFFLINE)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_to_apk():
    # التأكد من وجود القوالب قبل المعالجة
    download_assets()
    
    if 'project_zip' not in request.files:
        return "خطأ: يرجى رفع ملف المشروع بصيغة ZIP", 400

    user_zip_file = request.files['project_zip']
    new_app_name = request.form.get('app_name', 'Dajment_App')
    user_icon = request.files.get('app_icon')
    
    # تحديد الوضع (أونلاين أو أوفلاين)
    app_mode = request.form.get('app_mode', 'online')
    selected_base = BASE_ONLINE if app_mode == 'online' else BASE_OFFLINE

    if not os.path.exists(selected_base):
        return "السيرفر ما زال يجهز الملفات الكبيرة، جرب بعد دقيقة", 503

    memory_file = io.BytesIO()
    
    try:
        with zipfile.ZipFile(selected_base, 'r') as zin:
            with zipfile.ZipFile(memory_file, 'w') as zout:
                # 1. نسخ ملفات النظام الأساسية
                for item in zin.infolist():
                    if item.filename.startswith('assets/') or (user_icon and item.filename in ICON_SIZES):
                        continue
                    zout.writestr(item, zin.read(item.filename))
                
                # 2. حقن ملفات مشروع المستخدم داخل assets
                with zipfile.ZipFile(user_zip_file, 'r') as uzin:
                    for uitem in uzin.infolist():
                        if not uitem.is_dir():
                            zout.writestr(f'assets/{uitem.filename}', uzin.read(uitem.filename))
                
                # 3. تعديل الأيقونات برمجياً
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
        download_name=f"{new_app_name}.apk"
    )

if __name__ == '__main__':
    # تشغيل السيرفر وتجهيز الملفات
    download_assets()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
