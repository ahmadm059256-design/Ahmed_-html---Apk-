from flask import Flask, render_template, request, send_file
import os
import zipfile
import io
import requests
import uuid

app = Flask(__name__)

# روابط القوالب (تأكد من أنها روابط تحميل مباشر)
URL_ONLINE = "https://drive.google.com/uc?export=download&id=1UK7YwZFmRZgUH4YAZHqQiAbMMh-LM9Xw"
URL_OFFLINE = "https://drive.google.com/uc?export=download&id=1K80V2MYCMexHh8I4svD2AFAMUZaHnh4T"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_to_apk():
    # 1. استلام البيانات من النموذج
    app_name = request.form.get('app_name', 'NovaTech_App')
    orientation = request.form.get('orientation', 'portrait')
    app_mode = request.form.get('app_mode', 'online')
    
    project_zip = request.files.get('project_zip')
    app_icon = request.files.get('app_icon')

    if not project_zip:
        return "خطأ: يرجى رفع ملف المشروع بصيغة ZIP", 400

    # 2. إعداد المسارات المؤقتة (Render يستخدم /tmp للكتابة)
    unique_id = str(uuid.uuid4())[:8]
    base_apk_path = f"/tmp/base_{unique_id}.apk"
    url = URL_ONLINE if app_mode == 'online' else URL_OFFLINE
    
    try:
        # 3. تحميل قالب الـ APK من السيرفر
        print(f"جاري تحميل القالب من: {url}")
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status() # التأكد من أن الرابط يعمل
        
        with open(base_apk_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        # 4. معالجة ملف الـ APK في الذاكرة
        output_buffer = io.BytesIO()
        with zipfile.ZipFile(base_apk_path, 'r') as zin:
            with zipfile.ZipFile(output_buffer, 'w') as zout:
                for item in zin.infolist():
                    # تخطي الملفات التي سنقوم باستبدالها (الأصول والأيقونات)
                    if item.filename.startswith('assets/') or "ic_launcher" in item.filename:
                        continue
                    
                    file_content = zin.read(item.filename)
                    
                    # تعديل اتجاه الشاشة في AndroidManifest
                    if item.filename == 'AndroidManifest.xml' and orientation == 'landscape':
                        file_content = file_content.replace(b'portrait', b'landscape')
                    
                    zout.writestr(item, file_content)

                # 5. دمج ملفات المستخدم (ZIP) في مجلد assets
                with zipfile.ZipFile(project_zip, 'r') as uzin:
                    for uitem in uzin.infolist():
                        if not uitem.is_dir():
                            zout.writestr(f'assets/{uitem.filename}', uzin.read(uitem.filename))
                
                # 6. تحديث الأيقونة إذا تم رفعها
                if app_icon:
                    icon_bytes = app_icon.read()
                    # استبدال الأيقونات في المسارات الشائعة للأندرويد
                    icon_locations = [
                        'res/mipmap-hdpi-v4/ic_launcher.png',
                        'res/mipmap-mdpi-v4/ic_launcher.png',
                        'res/mipmap-xhdpi-v4/ic_launcher.png',
                        'res/mipmap-xxhdpi-v4/ic_launcher.png'
                    ]
                    for loc in icon_locations:
                        zout.writestr(loc, icon_bytes)

        output_buffer.seek(0)
        return send_file(
            output_buffer,
            mimetype='application/vnd.android.package-archive',
            as_attachment=True,
            download_name=f"{app_name}.apk"
        )

    except Exception as e:
        print(f"Detailed Error: {e}")
        return f"حدث خطأ أثناء المعالجة: {str(e)}", 500
    
    finally:
        # تنظيف السيرفر من الملفات المؤقتة
        if os.path.exists(base_apk_path):
            os.remove(base_apk_path)

if __name__ == '__main__':
    # تشغيل التطبيق على المنفذ المطلوب بواسطة Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
