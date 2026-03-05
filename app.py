from flask import Flask, render_template, request, send_file
import os, zipfile, io, urllib.request

app = Flask(__name__)

# روابط القوالب الأساسية
URL_ONLINE = "https://drive.google.com/uc?export=download&id=1UK7YwZFmRZgUH4YAZHqQiAbMMh-LM9Xw"
URL_OFFLINE = "https://drive.google.com/uc?export=download&id=1K80V2MYCMexHh8I4svD2AFAMUZaHnh4T"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_to_apk():
    # 1. استقبال البيانات من الموقع
    app_name = request.form.get('app_name', 'NovaTech_App')
    orientation = request.form.get('orientation', 'portrait')
    app_mode = request.form.get('app_mode', 'online')
    file = request.files.get('project_zip')

    if not file:
        return "خطأ: لم يتم رفع ملف ZIP", 400

    # 2. تحميل القالب المختار فقط لتوفير الذاكرة
    base_apk = "base.apk"
    url = URL_ONLINE if app_mode == 'online' else URL_OFFLINE
    urllib.request.urlretrieve(url, base_apk)

    # 3. إنشاء الملف في الذاكرة
    memory_file = io.BytesIO()
    
    try:
        with zipfile.ZipFile(base_apk, 'r') as zin:
            with zipfile.ZipFile(memory_file, 'w') as zout:
                for item in zin.infolist():
                    # تخطي ملفات الأصول القديمة
                    if item.filename.startswith('assets/'):
                        continue
                    
                    content = zin.read(item.filename)
                    
                    # تعديل اتجاه الشاشة برمجياً
                    if item.filename == 'AndroidManifest.xml' and orientation == 'landscape':
                        content = content.replace(b'portrait', b'landscape')
                    
                    zout.writestr(item, content)

                # 4. إضافة ملفات المستخدم مباشرة من الـ ZIP المرفوع
                with zipfile.ZipFile(file, 'r') as uzin:
                    for uitem in uzin.infolist():
                        if not uitem.is_dir():
                            zout.writestr(f'assets/{uitem.filename}', uzin.read(uitem.filename))
        
        memory_file.seek(0)
        return send_file(
            memory_file, 
            mimetype='application/vnd.android.package-archive', 
            as_attachment=True, 
            download_name=f"{app_name}.apk"
        )
    except Exception as e:
        return f"حدث خطأ في الكود: {str(e)}", 500
    finally:
        if os.path.exists(base_apk):
            os.remove(base_apk)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
