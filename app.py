from flask import Flask, render_template, request, send_file
import os, zipfile, io, urllib.request, shutil

app = Flask(__name__)

# روابط القوالب (تأكد من أن الروابط تسمح بالتحميل المباشر)
URL_ONLINE = "https://drive.google.com/uc?export=download&id=1UK7YwZFmRZgUH4YAZHqQiAbMMh-LM9Xw"
URL_OFFLINE = "https://drive.google.com/uc?export=download&id=1K80V2MYCMexHh8I4svD2AFAMUZaHnh4T"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_to_apk():
    app_name = request.form.get('app_name', 'NovaTech_App')
    orientation = request.form.get('orientation', 'portrait')
    app_mode = request.form.get('app_mode', 'online')
    
    project_zip = request.files.get('project_zip')
    app_icon = request.files.get('app_icon')

    if not project_zip:
        return "خطأ: يجب رفع ملف المشروع ZIP", 400

    base_apk = f"temp_{app_name}.apk"
    url = URL_ONLINE if app_mode == 'online' else URL_OFFLINE
    
    try:
        # تحميل القالب
        urllib.request.urlretrieve(url, base_apk)
        
        memory_file = io.BytesIO()
        with zipfile.ZipFile(base_apk, 'r') as zin:
            with zipfile.ZipFile(memory_file, 'w') as zout:
                for item in zin.infolist():
                    # تخطي ملفات الأصول والأيقونات القديمة لاستبدالها
                    if item.filename.startswith('assets/') or "ic_launcher" in item.filename:
                        continue
                    
                    content = zin.read(item.filename)
                    
                    # تعديل اتجاه الشاشة في Manifest
                    if item.filename == 'AndroidManifest.xml' and orientation == 'landscape':
                        content = content.replace(b'portrait', b'landscape')
                    
                    zout.writestr(item, content)

                # إضافة ملفات المشروع إلى مجلد assets
                with zipfile.ZipFile(project_zip, 'r') as uzin:
                    for uitem in uzin.infolist():
                        if not uitem.is_dir():
                            zout.writestr(f'assets/{uitem.filename}', uzin.read(uitem.filename))
                
                # إضافة الأيقونة الجديدة إذا تم رفعها
                if app_icon:
                    icon_data = app_icon.read()
                    # استبدال الأيقونات في المسارات الشائعة داخل الأندرويد
                    icon_paths = [
                        'res/mipmap-hdpi-v4/ic_launcher.png',
                        'res/mipmap-mdpi-v4/ic_launcher.png',
                        'res/mipmap-xhdpi-v4/ic_launcher.png',
                        'res/mipmap-xxhdpi-v4/ic_launcher.png'
                    ]
                    for path in icon_paths:
                        zout.writestr(path, icon_data)

        memory_file.seek(0)
        return send_file(
            memory_file, 
            mimetype='application/vnd.android.package-archive', 
            as_attachment=True, 
            download_name=f"{app_name}.apk"
        )
    except Exception as e:
        return f"فشل التحويل: {str(e)}", 500
    finally:
        if os.path.exists(base_apk):
            os.remove(base_apk)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    
