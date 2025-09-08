from flask import Flask, render_template, request, jsonify, url_for
from extractor.text_parser import extract_incidents_from_text
from extractor.url_parser import extract_incidents_from_url, extract_incidents_from_multiple_urls
import logging
import json
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extractor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Create data directory if it doesn't exist
if not os.path.exists('data'):
    os.makedirs('data')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/extract', methods=['POST'])
def extract():
    data = request.json

    try:
        if 'text' in data:
            logger.info("Processing text extraction request")
            incidents = extract_incidents_from_text(data['text'])
            return jsonify({'incidents': incidents})

        elif 'url' in data:
            logger.info(f"Processing URL extraction request: {data['url']}")
            incidents = extract_incidents_from_url(data['url'])

            # Save extracted incidents
            save_extraction_results(incidents, source_type='url', source=data['url'])

            return jsonify({'incidents': incidents})

        elif 'urls' in data:
            logger.info(f"Processing multiple URLs: {len(data['urls'])} URLs")
            results = extract_incidents_from_multiple_urls(data['urls'])

            # Save extracted incidents
            save_extraction_results(results['incidents'], source_type='multiple_urls', source=json.dumps(data['urls']))

            return jsonify(results)

        else:
            logger.warning("Invalid request: No text or URL provided")
            return jsonify({'error': 'No text or URL provided'}), 400

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({'error': str(e)}), 500


def save_extraction_results(incidents, source_type, source):
    """Save extracted incidents to a JSON file for later review"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/extraction_{source_type}_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'source_type': source_type,
                'source': source,
                'incidents': incidents
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved extraction results to {filename}")
    except Exception as e:
        logger.error(f"Failed to save extraction results: {e}")


@app.route('/history')
def history():
    """Show extraction history"""
    try:
        extractions = []

        if os.path.exists('data'):
            for file in os.listdir('data'):
                if file.startswith('extraction_') and file.endswith('.json'):
                    file_path = os.path.join('data', file)

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        extractions.append({
                            'timestamp': data.get('timestamp'),
                            'source_type': data.get('source_type'),
                            'source': data.get('source'),
                            'incident_count': len(data.get('incidents', [])),
                            'filename': file
                        })
                    except Exception as e:
                        logger.error(f"Error reading {file}: {e}")

        # Sort by timestamp (newest first)
        extractions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return render_template('history.html', extractions=extractions)
    except Exception as e:
        logger.error(f"Error in history view: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/view_extraction/<filename>')
def view_extraction(filename):
    """View details of a specific extraction"""
    try:
        file_path = os.path.join('data', filename)

        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return render_template('view_extraction.html', data=data)
    except Exception as e:
        logger.error(f"Error viewing extraction {filename}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/<filename>')
def export_extraction(filename):
    """Export extraction data as JSON"""
    try:
        file_path = os.path.join('data', filename)

        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return jsonify(data)
    except Exception as e:
        logger.error(f"Error exporting {filename}: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)