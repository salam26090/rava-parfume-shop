SWAT PERFUMES — RAVA + ZAMEL Flask Store
======================================
اس ZIP میں تصاویر، Flask کوڈ، HTML/CSS، SQLite آرڈر ریکارڈ اور ایڈمن پینل موجود ہیں۔

مقامی کمپیوٹر پر:
1) ZIP Extract کریں۔
2) Terminal میں فولڈر کھولیں۔
3) python -m pip install -r requirements.txt
4) python create_admin_hash.py چلائیں اور نتیجے میں ملنے والی مکمل ADMIN_PASSWORD_HASH ویلیو محفوظ کریں۔
5) SECRET_KEY اور ADMIN_PASSWORD_HASH کو ماحول (environment variables) میں سیٹ کریں۔
   مثال (Linux): export SECRET_KEY='ایک_لمبی_رینڈم_ویلیو'
   export ADMIN_PASSWORD_HASH='پچھلے_مرحلے_کا_مکمل_ہیش'
6) python app.py
7) براؤزر: http://127.0.0.1:5000
8) ایڈمن: /admin/login

PythonAnywhere پر عمومی طریقہ:
1) Files میں ZIP اپ لوڈ اور unzip کریں، یا Bash console میں unzip کریں۔
2) Bash میں pip install --user -r requirements.txt (اپنے اکاؤنٹ کی Python ورژن کے مطابق)۔
3) Web tab میں Flask/Manual configuration سے WSGI فائل سیٹ کریں؛ اس فولڈر کو sys.path میں ڈال کر from app import app as application لکھیں۔
4) Web tab کے WSGI میں ماحول کی SECRET_KEY اور ADMIN_PASSWORD_HASH ویلیوز مقرر کریں (کوڈ میں ہارڈکوڈ یا عوامی فائل میں شیئر نہ کریں)۔
5) Web app Reload کریں۔ HTTPS پر HTTPS_ONLY=1 سیٹ کریں۔
6) SQLite فائل کا ڈیٹا بیک اپ لیتے رہیں؛ مفت ہوسٹنگ کے قواعد، storage اور ویب ایپ دستیابی پہلے چیک کریں۔

اہم:
- قیمتیں ابتدائی/مثالی ہیں، مارکیٹ سے تصدیق شدہ نہیں۔ ایڈمن پینل سے اصل قیمتیں لگائیں۔
- تصویر میں دکھائی گئی بوتلوں کے تمام سائز کی حقیقی دستیابی کی تصدیق کریں۔
- ZAMEL تصویر ایک تصوراتی ڈیزائن ہے؛ بوتل/باکس پر لکھے غلط الفاظ درست کیے بغیر پرنٹ نہ کریں۔
- واٹس ایپ آرڈر صرف تب موصول ہوتا ہے جب خریدار WhatsApp میں Send دباتا ہے۔
- آرڈر پہلے SQLite میں pending محفوظ ہوتا ہے، چاہے خریدار WhatsApp میں Send نہ کرے۔
- یہ ورژن ایک پروڈکٹ فی آرڈر سپورٹ کرتا ہے؛ multi-product cart، تصویر اپ لوڈ اور آن لائن ادائیگی شامل نہیں۔
- Admin پاس ورڈ بغیر ADMIN_PASSWORD_HASH کے فعال نہیں ہوگا۔
- پروڈکٹ تصاویر static/images میں موجود ہیں؛ نئی تصویر شامل کرنے کے لیے ڈیولپر سے پروڈکٹ ریکارڈ اپ ڈیٹ کروائیں۔
- کسٹمر ڈیٹا حساس ہے؛ HTTPS، محفوظ پاس ورڈ اور باقاعدہ بیک اپ ضروری ہیں۔
- یہ ابتدائی کاروباری ورژن ہے؛ زیادہ ٹریفک اور ادائیگیوں سے پہلے مزید سیکیورٹی آڈٹ کریں۔
