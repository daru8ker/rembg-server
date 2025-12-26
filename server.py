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

# モデルを事前にロード（初回高速化）
session = new_session("u2net")

@app.route('/process', methods=['POST'])
def process_image():
    try:
        data = request.json
        image_url = data.get('url')
        if not image_url: return jsonify({'error': 'URLが必要です'}), 400

        # 画像ダウンロード
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(image_url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()
        
        input_image = Image.open(BytesIO(response.content)).convert("RGBA")

        # 【重要】無料サーバー対策：画像をリサイズしてメモリ不足エラーを防ぐ
        # 最大辺を1000pxに制限（画質は十分維持されます）
        input_image.thumbnail((1000, 1000), Image.LANCZOS)

        # 背景削除実行
        no_bg_image = remove(input_image, session=session, alpha_matting=True)

        # 白背景と合成
        white_bg = Image.new("RGBA", no_bg_image.size, "WHITE")
        white_bg.paste(no_bg_image, (0, 0), no_bg_image)
        final_image = white_bg.convert("RGB")

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
