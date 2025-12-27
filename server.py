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

# Standardプランなので高画質モデルを使用
session = new_session("u2net")

@app.route('/process', methods=['POST'])
def process_image():
    try:
        data = request.json
        
        # 画像データの取得（URLまたはBase64）
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

        # 高画質用に大きめにリサイズ
        input_image.thumbnail((2000, 2000), Image.LANCZOS)

        # ★【改善ポイント】post_process_mask=True を追加
        # これにより、境界線の判定精度が向上し、塗りつぶし問題が改善します。
        no_bg_image = remove(input_image, session=session, alpha_matting=True, post_process_mask=True)

        # 正方形・白背景加工
        w, h = no_bg_image.size
        max_dim = max(w, h)
        square_bg = Image.new("RGBA", (max_dim, max_dim), "WHITE")
        paste_x = (max_dim - w) // 2
        paste_y = (max_dim - h) // 2
        square_bg.paste(no_bg_image, (paste_x, paste_y), no_bg_image)
        final_image = square_bg.convert("RGB")

        # 返却
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
