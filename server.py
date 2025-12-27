import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from rembg import remove, new_session
from PIL import Image
import requests
from io import BytesIO
import base64

app = Flask(__name__)
CORS(app)

# ★【Standardプラン専用】高画質モデル(u2net)を使用
# メモリが2GBあるので、この高精度モデルでも余裕で動きます
session = new_session("u2net")

@app.route('/process', methods=['POST'])
def process_image():
    try:
        data = request.json
        image_url = data.get('url')
        if not image_url: return jsonify({'error': 'URLが必要です'}), 400

        # 画像ダウンロード
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(image_url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        input_image = Image.open(BytesIO(response.content)).convert("RGBA")

        # ★【画質向上】サイズ制限を大きく緩和
        # 無料版では1000pxでしたが、Standardなら2000pxまでOKです
        input_image.thumbnail((2000, 2000), Image.LANCZOS)

        # 背景削除（高画質モデルで実行）
        no_bg_image = remove(input_image, session=session, alpha_matting=True)

        # 正方形・白背景加工
        w, h = no_bg_image.size
        max_dim = max(w, h)
        
        square_bg = Image.new("RGBA", (max_dim, max_dim), "WHITE")
        
        paste_x = (max_dim - w) // 2
        paste_y = (max_dim - h) // 2
        square_bg.paste(no_bg_image, (paste_x, paste_y), no_bg_image)
        
        final_image = square_bg.convert("RGB")

        # Base64変換
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
