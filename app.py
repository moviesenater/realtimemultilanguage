from flask import Flask, request, jsonify, render_template
from deep_translator import GoogleTranslator
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import os, json, jwt, datetime
from functools import wraps

SECRET_KEY = "secret123"

pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

USER_FILE = "users.json"

def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    try:
        with open(USER_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token missing"}), 401
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    users = load_users()
    if data['username'] in users:
        return jsonify({"error": "User already exists"})
    users[data['username']] = data['password']
    save_users(users)
    return jsonify({"message": "Registered successfully"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    users = load_users()
    if users.get(data['username']) != data['password']:
        return jsonify({"error": "Invalid credentials"}), 401
    token = jwt.encode({
        "user": data['username'],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }, SECRET_KEY, algorithm="HS256")
    return jsonify({"token": token})

@app.route('/translate', methods=['POST'])
@token_required
def translate_text():
    data = request.json
    translated = GoogleTranslator(source='auto', target=data['target']).translate(data['text'])
    return jsonify({"translated_text": translated})

@app.route('/ocr', methods=['POST'])
@token_required
def ocr():
    file = request.files['image']
    path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(path)
    text = ""
    if path.endswith(".pdf"):
        images = convert_from_path(path)
        for img in images:
            text += pytesseract.image_to_string(img)
    else:
        text = pytesseract.image_to_string(Image.open(path))
    return jsonify({"text": text})

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True, port=5001)