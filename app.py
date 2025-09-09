import os
import json
from flask import Flask, request, jsonify, send_from_directory

# データ保存用のファイルパス
DATA_FILE = 'data.json'

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)

# URL:/ に対して、static/index.htmlを表示して
# クライアントサイドのアプリケーションをホストする
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# URL:/add に対して、static/add.htmlを表示して
# レシピ追加ページをホストする
@app.route('/add')
def add():
    return send_from_directory(app.static_folder, 'add.html')

# URL:/ に対して、static/search.htmlを表示して
# レシピ検索ページをホストする
@app.route('/search')
def search():
    return send_from_directory(app.static_folder, 'search.html')


# テキストデータを取得・保存するためのAPIエンドポイント
@app.route('/api/texts', methods=['GET', 'POST'])
def handle_texts():
    if request.method == 'GET':
        # GETリクエスト: 保存されているテキストデータを返す
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return jsonify(data)
            else:
                # ファイルが存在しない場合は空のリストを返す
                return jsonify([])
        except Exception as e:
            app.logger.error(f"Error reading data file: {e}")
            return jsonify({"error": "Could not read data."}), 500

    elif request.method == 'POST':
        # POSTリクエスト: 送られてきたテキストデータをファイルに保存する
        data = request.get_json()
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return jsonify({"message": "Data saved successfully."})
        except Exception as e:
            app.logger.error(f"Error writing data file: {e}")
            return jsonify({"error": "Could not save data."}), 500

# スクリプトが直接実行された場合にのみ開発サーバーを起動
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)