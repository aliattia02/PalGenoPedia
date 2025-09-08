from flask import Flask, render_template, request, jsonify
from extractor.text_parser import extract_incidents_from_text
from extractor.url_parser import extract_incidents_from_url

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/extract', methods=['POST'])
def extract():
    data = request.json

    if 'text' in data:
        incidents = extract_incidents_from_text(data['text'])
        return jsonify({'incidents': incidents})
    elif 'url' in data:
        incidents = extract_incidents_from_url(data['url'])
        return jsonify({'incidents': incidents})
    else:
        return jsonify({'error': 'No text or URL provided'}), 400


if __name__ == '__main__':
    app.run(debug=True, port=5000)