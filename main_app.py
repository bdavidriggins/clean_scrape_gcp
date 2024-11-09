# /home/bdavidriggins/Projects/clean_scrape/main_app.py
"""
main_app.py

This is the main Flask application file responsible for handling web routes, interacting with the database,
and managing article processing. It sets up the Flask app, defines routes for CRUD operations on articles,
processes incoming data by fetching and cleansing web content, interacts with a language model for content
generation, and initializes the database connection. This file serves as the central hub for the web
application's functionality.
"""

from flask import Flask, render_template, request, jsonify, g, redirect, send_file
from modules.config import MODEL_NAME_FLASH, ARTICLE_CLEAN_PROMPT, ARTICLE_IMPROVE_READABILITY_PROMPT
from modules.web_scraper import WebScraper
from modules.google_api_interface import ContentGenerator
from modules.common_logger import setup_logger
from modules.text_to_speech_service import text_to_speech
from modules.db_manager import (
    get_all_articles, 
    get_article_by_id,
    save_article,
    update_article_by_id,
    delete_article_by_id,
    get_audio_file_by_article_id,
    get_articles_with_audio_status as db_get_articles_with_audio_status
)
import io

# Initialize the logger for the application
logger = setup_logger("main_app")

# Initialize the Flask application
app = Flask(__name__)


@app.route('/')
def index():
    """
    Render the home page of the application.
    """
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index.html: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/get_articles')
def get_articles():
    """
    Retrieve all articles from the database and return them as JSON.
    """
    try:
        articles = get_all_articles()
        return jsonify(articles)
    except Exception as e:
        logger.error(f"Error fetching articles: {e}")
        return jsonify({'error': 'Failed to retrieve articles'}), 500

@app.route('/get_article/<article_id>')
def get_article(article_id):
    """
    Retrieve a specific article by its ID and return it as JSON.
    """
    try:
        article = get_article_by_id(article_id)
        if article:
            return jsonify(article)
        return jsonify({'error': 'Article not found'}), 404
    except Exception as e:
        logger.error(f"Error fetching article with ID {article_id}: {e}")
        return jsonify({'error': 'Failed to retrieve article'}), 500


@app.route('/tts_article/<article_id>')
def tts_article(article_id):
    """
    Convert article text to speech by its ID and return whether it was successful
    """
    try:
        # Get the article content
        article = get_article_by_id(article_id)
        if not article:
            logger.error(f"Article with ID {article_id} not found.")
            return jsonify({'error': 'Article not found'}), 404

        # Convert the text to speech using the article ID
        conversion_success = text_to_speech(article_id)
        
        if not conversion_success:
            logger.error(f"Text-to-speech conversion failed for article ID {article_id}")
            return jsonify({'error': 'Text-to-speech conversion failed'}), 500

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error processing text-to-speech for article ID {article_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500



@app.route('/process', methods=['POST'])
def process():
    """Process the submitted URL or HTML content."""
    try:
        data = request.get_json()
        if data is None:
            logger.warning("No JSON data received in request")
            return jsonify({'error': 'Invalid input data'}), 400

        url = data.get('url')
        html_content = data.get('html_content')

        if not url and not html_content:
            logger.warning("Neither URL nor HTML content provided")
            return jsonify({'error': 'URL or HTML content is required'}), 400

        scraper = WebScraper({
            'timeout': 15,
            'retry_attempts': 2,
            'retry_delay': 1,
            'headless': True
        })

        if html_content:
            article_data = scraper.scrape_article(raw_content=html_content)
            source_type = 'html'
        else:
            article_data = scraper.scrape_article(url=url)
            source_type = 'url'

        if article_data is None:
            logger.error("Failed to extract content")
            return jsonify({'error': 'Failed to extract content'}), 400

        if not article_data.get('content'):
            logger.error("Failed to extract content")
            return jsonify({'error': 'Failed to extract content'}), 400

        content_generator = ContentGenerator()

        full_prompt = ARTICLE_CLEAN_PROMPT.format(article_text=article_data.get('content'))        
        llm_response = content_generator.generate_content(
            user_prompt=full_prompt
        )

        full_prompt = ARTICLE_IMPROVE_READABILITY_PROMPT.format(article_text=llm_response)        
        llm_response = content_generator.generate_content(
            user_prompt=full_prompt
        )
       

        if llm_response is None:
            logger.error("Language model response is None")
            return jsonify({'error': 'Failed to generate content'}), 500

        if save_article(
            url=url,
            content=llm_response,
            title=article_data.get('title', ''),
            author=article_data.get('author', ''),
            date=article_data.get('date', ''),
            description=article_data.get('description', ''),
            source_type=source_type
        ):
            logger.info("Article saved successfully")
            return jsonify({'success': True})
        
        logger.error("Failed to save the article to the database")
        return jsonify({'error': 'Failed to save article'}), 500

    except Exception as e:
        logger.exception("An unexpected error occurred during processing")
        return jsonify({'error': str(e)}), 500

@app.route('/update_article/<article_id>', methods=['PUT'])
def update_article(article_id):
    """
    Update an existing article's content, title, author, and description by its ID.
    """
    try:
        data = request.get_json()
        if data is None:
            logger.warning("No JSON data received in update request")
            return jsonify({'error': 'Invalid input data'}), 400

        content = data.get('content')
        title = data.get('title')
        author = data.get('author')
        description = data.get('description')

        if not content:
            logger.warning("Content missing in update request data")
            return jsonify({'error': 'Content is required'}), 400

        if update_article_by_id(
            article_id=article_id,
            content=content,
            title=title,
            author=author,
            description=description
        ):
            logger.info(f"Article with ID {article_id} updated successfully")
            return jsonify({'success': True})
        logger.error(f"Article with ID {article_id} not found for update")
        return jsonify({'error': 'Article not found'}), 404

    except Exception as e:
        logger.exception(f"An unexpected error occurred while updating article ID {article_id}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.route('/delete_article/<article_id>', methods=['DELETE'])
def delete_article(article_id):
    """
    Delete an article by its ID.
    """
    try:
        if delete_article_by_id(article_id):
            logger.info(f"Article with ID {article_id} deleted successfully")
            return jsonify({'success': True})
        logger.error(f"Article with ID {article_id} not found for deletion")
        return jsonify({'error': 'Article not found'}), 404
    except Exception as e:
        logger.exception(f"An unexpected error occurred while deleting article ID {article_id}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_articles_with_audio_status')
def get_articles_with_audio_status_route():
    """
    Retrieve all articles with their audio status.
    This function delegates the database retrieval to db_manager.py.
    """
    try:
        articles = db_get_articles_with_audio_status()
        
        return jsonify([{
            'id': article['id'],
            'url': article['url'],
            'content': article['content'],
            'title': article['title'],
            'author': article['author'],
            'date': article['date'],
            'description': article['description'],
            'has_audio': article['has_audio']
        } for article in articles])
    except Exception as e:
        logger.error(f"Error retrieving articles with audio status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/audio_player/<article_id>')
def audio_player(article_id):
    """
    Render the audio player page for a specific article
    """
    try:
        article = get_article_by_id(article_id)
        if not article:
            return redirect('/')
            
        return render_template('audio_player.html', article=article)
    except Exception as e:
        logger.error(f"Error loading audio player: {e}")
        return redirect('/')

@app.route('/get_audio/<article_id>')
def get_audio(article_id):
    """
    Stream the audio file for a specific article
    """
    try:
        audio_content = get_audio_file_by_article_id(article_id)
        if audio_content is None:
            logger.error(f"Audio not found for article ID {article_id}")
            return jsonify({'error': 'Audio not found'}), 404
        
        # Directly pass the BytesIO object without wrapping
        return send_file(
            audio_content,
            mimetype='audio/mp4',
            as_attachment=False,    # Stream the audio instead of downloading
            download_name=f"{article_id}.m4a"  # Optional: Only needed if as_attachment=True
        )
    except Exception as e:
        logger.error(f"Error streaming audio for article ID {article_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/log_viewer')
def log_viewer():
    return render_template('log_viewer.html')

@app.route('/get_log')
def get_log():
    with open('app.log', 'r') as f:
        return f.read()

@app.route('/clear_log', methods=['POST'])
def clear_log():
    open('app.log', 'w').close()
    return '', 204


if __name__ == '__main__':
    try:        
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.critical(f"Failed to start the application: {e}")
