from flask import Flask, send_from_directory
import os

app = Flask(__name__)
VIDEO_FOLDER = os.path.join(os.path.dirname(__file__), 'videos')

@app.route('/videos/<filename>')
def serve_video(filename):
    return send_from_directory(VIDEO_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7000, debug=True)
