import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from rembg import remove
from PIL import Image
import requests
from io import BytesIO
import base64

app = Flask(__name__)
# すべてのアクセスを許可（セキュリティを強化したければ拡張機能のIDを指定）
CORS(app)

@app.route('/process', methods=['POST'])
def process_image():
    try:
        data = request.json
        image_url = data.get('url')

        if not image_url:
            return jsonify({'error': 'URLが必要です'}), 400

        print(f"Processing: {image_url[:30]}...") # ログ用

        # 画像ダウンロード
        # User-Agentを設定して、拒否されるサイトを減らす
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(image_url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()
        
        input_image = Image.open(BytesIO(response.content)).convert("RGBA")

        # 背景削除処理
        no_bg_image = remove(input_image, alpha_matting=True)

        # 白背景と合成
        white_bg = Image.new("RGBA", no_bg_image.size, "WHITE")
        white_bg.paste(no_bg_image, (0, 0), no_bg_image)
        final_image = white_bg.convert("RGB")

        # Base64変換して返却
        buffered = BytesIO()
        final_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return jsonify({'image_data': f'data:image/png;base64,{img_str}'})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def health_check():
    return "Server is running!", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)