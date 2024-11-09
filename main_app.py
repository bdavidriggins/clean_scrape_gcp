from flask import Flask, jsonify, render_template_string
from test_db_and_function import test_db_manager, test_audio_functions
import os
from dotenv import load_dotenv
import sys
import io
import unittest
from test_text_to_speech import TestTextToSpeech

from modules.common_logger import setup_logger

logger = setup_logger("main_app")

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Global variable to store test results
test_results = {}



def capture_test_output(test_func):
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    
    try:
        test_func()
        output = sys.stdout.getvalue()
        return 'Success', output
    except Exception as e:
        output = sys.stdout.getvalue()
        return f'Failed: {str(e)}', output
    finally:
        sys.stdout = old_stdout



def run_all_tests():
    global test_results
    test_results['db_manager_tests'] = capture_test_output(test_db_manager)
    test_results['audio_functions_tests'] = capture_test_output(test_audio_functions)
    test_results['web_scraper_tests'] = capture_test_output(run_web_scraper_tests)
    test_results['google_api_interface_tests'] = capture_test_output(run_google_api_interface_tests)
    test_results['text_to_speech_tests'] = capture_test_output(run_text_to_speech_tests)

def run_text_to_speech_tests():
    tests = unittest.TestLoader().loadTestsFromTestCase(TestTextToSpeech)
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    return result

def run_web_scraper_tests():
    tests = unittest.TestLoader().loadTestsFromName('test_web_scraper')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    return result


def run_google_api_interface_tests():
    tests = unittest.TestLoader().loadTestsFromName('test_google_api_interface')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    return result



# Run tests at startup
try:
    run_all_tests()
except Exception as e:
    logger.error(f"Error during startup: {e}")


@app.route('/')
def hello():
    return "Hello, World! Go to /test_results to see test outcomes."

@app.route('/test_results')
def show_test_results():
    html_template = """
    <html>
        <head>
            <title>Test Results</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #333; }
                .test { margin-bottom: 20px; }
                .success { color: green; }
                .failure { color: red; }
                pre { background-color: #f0f0f0; padding: 10px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>Test Results</h1>
            {% for test_name, (result, output) in test_results.items() %}
                <div class="test">
                    <h2>{{ test_name }}</h2>
                    <p class="{{ 'success' if result == 'Success' else 'failure' }}">
                        Result: {{ result }}
                    </p>
                    <h3>Output:</h3>
                    <pre>{{ output }}</pre>
                </div>
            {% endfor %}
        </body>
    </html>
    """
    return render_template_string(html_template, test_results=test_results)

@app.route('/run_tests')
def run_tests():
    run_all_tests()
    return jsonify(test_results)

@app.route('/env')
def show_env():
    return jsonify({
        'GOOGLE_CLOUD_PROJECT': os.getenv('GOOGLE_CLOUD_PROJECT'),
        'GCS_BUCKET_NAME': os.getenv('GCS_BUCKET_NAME'),
        'USE_MOCK_STORAGE': os.getenv('USE_MOCK_STORAGE')
    })

if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=5000, debug=True)
    pass
