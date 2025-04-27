import os
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import logging,csv,json

CONFIG_FILE = "../secrets/details.json"
def load_config() -> Dict:
    """Load configuration from JSON file"""
    try:
        with open(os.path.join(os.getcwd(), CONFIG_FILE), 'r') as file:
            config = json.load(file)
            config["printer_id"] = config.get("code", "")
            return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise
config = load_config()

def setup_logger():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)
logger = setup_logger()
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

UPLOAD_FOLDER = "files/"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        uid = request.form.get('user_id')
        logger.info(file.filename)
        user_folder = os.path.join(UPLOAD_FOLDER, uid)
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        filename = secure_filename(file.filename)
        filepath = os.path.join(user_folder,filename)
        logger.info(filepath)
        file.save(filepath)
        return jsonify({
            'message': 'File uploaded successfully', 
            'path': filepath
        }), 200
    
    except Exception as e:
        logger.info(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500


JSON_FILE = 'user_files.json'

@app.route('/save_user_files', methods=['POST'])
def save_user_files():
    data = request.json
    user_id = data.get('userId')
    file_ids = data.get('fileIds')

    if not user_id or not file_ids:
        return jsonify({'success': False, 'message': 'Invalid input'}), 400

    # Read existing JSON file
    user_files = {}
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r') as f:
            user_files = json.load(f)

    # Update the user's file IDs, avoiding duplicates
    if user_id in user_files:
        user_files[user_id].extend(file_ids)
        user_files[user_id] = list(set(user_files[user_id]))  # Remove duplicates
    else:
        user_files[user_id] = file_ids

    # Write back the updated data to the JSON file
    with open(JSON_FILE, 'w') as f:
        json.dump(user_files, f, indent=4)

    return jsonify({'success': True, 'message': 'Files saved successfully'})




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False, ssl_context=('/home/atomte'+config["code"]+'/cert.pem', '/home/atomte'+config["code"]+'/key.pem'))
