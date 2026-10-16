import os
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    # static/images فولڈر کا راستہ
    image_folder = os.path.join(app.static_folder, 'images')
    
    images = []
    if os.path.exists(image_folder):
        for filename in os.listdir(image_folder):
            # صرف تصویروں والی فائلیں اٹھائیں
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                images.append(filename)
    
    # تصویروں کو نمبر کے حساب سے ترتیب دیں (1, 2, 3...)
    images.sort()
    
    # index.html کو تصویروں کی لسٹ بھیجیں
    return render_template('index.html', images=images)

if __name__ == '__main__':
    app.run(debug=True)
