import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from rembg import remove, new_session
from PIL import Image
from io import BytesIO
import base64
import requests

app = Flask(__name__)
CORS(app)

# Standardプラン: 高画質モデル
session = new_session("u2net")

@app.route('/process', methods=['POST'])
def process_image():
    try:
        data = request.json
        
        # 画像データの取得
        if 'url' in data:
            image_url = data['url']
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(image_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            input_image = Image.open(BytesIO(response.content)).convert("RGBA")
        elif 'image_data' in data:
            image_data = data['image_data']
            if "," in image_data:
                image_data = image_data.split(",")[1]
            input_image = Image.open(BytesIO(base64.b64decode(image_data))).convert("RGBA")
        else:
            return jsonify({'error': '画像データが必要です'}), 400

        # リサイズ（高画質維持）
        input_image.thumbnail((2000, 2000), Image.LANCZOS)

        # ★【修正】エラーの原因だった alpha_matting を削除
        # これで「division by zero」や「画像が黒くなる」問題が完全に直ります。
        no_bg_image = remove(input_image, session=session)

        # ★【変更】サーバーは「透明な画像」をそのまま返します
        # 白背景やアスペクト比の加工は、すべて拡張機能側（sidepanel.js）で行います。
        final_image = no_bg_image

        # Base64返却
        buffered = BytesIO()
        final_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return jsonify({'image_data': f'data:image/png;base64,{img_str}'})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
