import os
import json
import uuid
from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)

# OpenRouterクライアントの設定
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

# URL:/ に対して、static/index.htmlを表示して
# クライアントサイドのアプリケーションをホストする
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')
        
# レシピを保存するJSONファイル
RECIPES_FILE = 'recipes.json'

def load_recipes():
    if os.path.exists(RECIPES_FILE):
        with open(RECIPES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_recipes(recipes):
    with open(RECIPES_FILE, 'w', encoding='utf-8') as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)

# レシピ管理用API
@app.route('/api/recipes', methods=['GET', 'POST'])
def handle_recipes():
    if request.method == 'GET':
        recipes = load_recipes()
        keyword = request.args.get('keyword')
        if keyword:
            # キーワードでレシピをフィルタリング
            keyword = keyword.lower()
            filtered_recipes = [
                recipe for recipe in recipes
                if keyword in recipe.get('recipe_name', '').lower() or
                   keyword in recipe.get('ingredients', '').lower() or
                   keyword in recipe.get('instructions', '').lower()
            ]
            return jsonify(filtered_recipes)
        return jsonify(recipes) # キーワードがなければ全件返す

    elif request.method == 'POST':
        data = request.get_json()
        if not data or "recipe_name" not in data:
            return jsonify({"error": "Invalid data"}), 400

        # レシピに一意のIDを付与
        data['id'] = uuid.uuid4().hex

        recipes = load_recipes()
        recipes.append(data)
        save_recipes(recipes)

        return jsonify({"message": "レシピを保存しました！"}), 201

# レシピ削除用API
@app.route('/api/recipes/<recipe_id>', methods=['DELETE'])
def delete_recipe(recipe_id):
    recipes = load_recipes()
    
    # 削除対象のレシピを除外した新しいリストを作成
    updated_recipes = [recipe for recipe in recipes if recipe.get('id') != recipe_id]

    if len(recipes) == len(updated_recipes):
        return jsonify({"error": "指定されたIDのレシピが見つかりませんでした。"}), 404

    save_recipes(updated_recipes)
    return jsonify({"message": "レシピを削除しました。"})

# AIレシピ生成API
@app.route('/api/generate-recipe', methods=['POST'])
def generate_recipe_api():
    # APIキーが設定されているかチェック
    if not os.getenv("OPENROUTER_API_KEY"):
        return jsonify({"error": "OpenRouter API key is not configured on the server."}), 500

    # リクエストから材料を取得
    data = request.get_json()
    if not data or 'ingredients' not in data or not data['ingredients'].strip():
        return jsonify({"error": "材料が入力されていません。"}), 400
    
    ingredients_text = data['ingredients']

    try:
        # AIに渡すプロンプトを作成
        prompt = f"""
        以下の料理について、家庭で簡単に作れるレシピを調べてください。
        回答は必ず以下のJSON形式で、キーも日本語で出力してください。

        {{
          "recipe_name": "料理名",
          "ingredients": "材料リスト（分量も含む）",
          "instructions": "作り方の手順"
        }}

        # 材料
        {ingredients_text}
        """

        # OpenRouter API (ChatGPT) を呼び出す
        completion = client.chat.completions.create(
            model="openai/gpt-3.5-turbo", # より高性能なモデルを使いたい場合は "openai/gpt-4o" など
            messages=[
                {"role": "system", "content": "あなたはプロの料理研究家です。"},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"}, # JSON形式での出力を強制
        )

        response_content = completion.choices[0].message.content
        recipe_data = json.loads(response_content)
        return jsonify(recipe_data)
    except RateLimitError as e:
        app.logger.warning(f"Rate limit exceeded: {e}")
        return jsonify({"error": "リクエストが多すぎます。少し時間をおいてから再度お試しください。"}), 429
    except Exception as e:
        app.logger.error(f"Error generating recipe: {e}")
        return jsonify({"error": "AIとの通信中にエラーが発生しました。"}), 500

# スクリプトが直接実行された場合にのみ開発サーバーを起動
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)