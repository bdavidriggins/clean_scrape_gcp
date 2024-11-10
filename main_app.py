# /home/bdavidriggins/Projects/clean_scrape/main_app.py
"""
main_app.py

This is the main Flask application file responsible for handling web routes, interacting with the database,
and managing article processing. It sets up the Flask app, defines routes for CRUD operations on articles,
processes incoming data by fetching and cleansing web content, interacts with a language model for content
generation, and initializes the database connection. This file serves as the central hub for the web
application's functionality.
"""
from quart import Quart, render_template, request, jsonify, g, redirect, send_file
import asyncio
from modules.config import MODEL_NAME_FLASH, ARTICLE_CLEAN_PROMPT, ARTICLE_IMPROVE_READABILITY_PROMPT
from modules.web_scraper import WebScraper
from modules.google_api_interface import ContentGenerator
from modules.common_logger import setup_logger,logger, job_context, set_job_context, clear_job_context, truncate_text
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
import datetime, random, string


# Initialize the logger for the application
logger = setup_logger("main_app")

# Initialize the Flask application
app = Quart(__name__)

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/')
async def index():
    """
    Render the home page of the application.
    """
    try:
        return await render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index.html: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/get_articles')
async def get_articles():
    """
    Retrieve all articles from the database and return them as JSON.
    """
    try:
        articles = await get_all_articles()
        return jsonify(articles)
    except Exception as e:
        logger.error(f"Error fetching articles: {e}")
        return jsonify({'error': 'Failed to retrieve articles'}), 500

@app.route('/get_article/<article_id>')
async def get_article(article_id):
    """
    Retrieve a specific article by its ID and return it as JSON.
    """
    with job_context(article_id):
        try:
            article = await get_article_by_id(article_id)
            if article:
                return jsonify(article)
            return jsonify({'error': 'Article not found'}), 404
        except Exception as e:
            logger.error(f"Error fetching article with ID {article_id}: {e}")
            return jsonify({'error': 'Failed to retrieve article'}), 500


@app.route('/tts_article/<article_id>')
async def tts_article(article_id):
    """
    Convert article text to speech by its ID and return whether it was successful
    """
    with job_context(article_id):
        try:
            # Get the article content
            article = await get_article_by_id(article_id)
            if not article:
                logger.error(f"Article with ID {article_id} not found.")
                return jsonify({'error': 'Article not found'}), 404

            # Convert the text to speech using the article ID
            conversion_success = await text_to_speech(article_id)
            
            if not conversion_success:
                logger.error(f"Text-to-speech conversion failed for article ID {article_id}")
                return jsonify({'error': 'Text-to-speech conversion failed'}), 500

            return jsonify({'success': True})

        except Exception as e:
            logger.error(f"Error processing text-to-speech for article ID {article_id}: {e}")
            return jsonify({'error': 'Internal server error'}), 500



@app.route('/process', methods=['POST'])
async def process():
    """Process the submitted URL or HTML content."""
    try:
        data = await request.get_json()

        job_id = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

        with job_context(job_id):
            

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
                logger.info(f"Starting processing for raw data:\n{truncate_text(html_content)}")
                article_data = await scraper.scrape_article(raw_content=html_content)
                source_type = 'html'
            else:
                logger.info(f"Starting processing for URL: {data['url']}")
                article_data = await scraper.scrape_article(url=url)
                source_type = 'url'

            if article_data is None:
                logger.error("Failed to extract content")
                return jsonify({'error': 'Failed to extract content'}), 400

            if not article_data.get('content'):
                logger.error("Failed to extract content")
                return jsonify({'error': 'Failed to extract content'}), 400

            content_generator = ContentGenerator()

            full_prompt = ARTICLE_CLEAN_PROMPT.format(article_text=article_data.get('content'))        
            llm_response = await content_generator.generate_content(
                user_prompt=full_prompt
            )

            full_prompt = ARTICLE_IMPROVE_READABILITY_PROMPT.format(article_text=llm_response)        
            llm_response = await content_generator.generate_content(
                user_prompt=full_prompt
            )
        

            if llm_response is None:
                logger.error("Language model response is None")
                return jsonify({'error': 'Failed to generate content'}), 500

            if await save_article(
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
async def update_article(article_id):
    """
    Update an existing article's content, title, author, and description by its ID.
    """
    with job_context(article_id):
        try:
            data = await request.get_json()
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

            if await update_article_by_id(
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

@app.route('/delete_article/<article_id>', methods=['DELETE'])
async def delete_article(article_id):
    """
    Delete an article by its ID.
    """
    with job_context(article_id): 
        try:
            if await delete_article_by_id(article_id):
                logger.info(f"Article with ID {article_id} deleted successfully")
                return jsonify({'success': True})
            logger.error(f"Article with ID {article_id} not found for deletion")
            return jsonify({'error': 'Article not found'}), 404
        except Exception as e:
            logger.exception(f"An unexpected error occurred while deleting article ID {article_id}")
            return jsonify({'error': str(e)}), 500

@app.route('/get_articles_with_audio_status')
async def get_articles_with_audio_status_route():
    """
    Retrieve all articles with their audio status.
    This function delegates the database retrieval to db_manager.py.
    """
    try:
        articles = await db_get_articles_with_audio_status()
        
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
async def audio_player(article_id):
    """
    Render the audio player page for a specific article
    """
    with job_context(article_id):
        try:
            article = await get_article_by_id(article_id)
            if not article:
                return redirect('/')
                
            return await render_template('audio_player.html', article=article)
        except Exception as e:
            logger.error(f"Error loading audio player: {e}")
            return redirect('/')

@app.route('/get_audio/<article_id>')
async def get_audio(article_id):
    """
    Stream the audio file for a specific article
    """
    with job_context(article_id):
        try:
            audio_content = await get_audio_file_by_article_id(article_id)
            if audio_content is None:
                logger.error(f"Audio not found for article ID {article_id}")
                return jsonify({'error': 'Audio not found'}), 404
            
            # Directly pass the BytesIO object without wrapping
            return await send_file(
                audio_content,
                mimetype='audio/mp4',
                as_attachment=False    # Stream the audio instead of downloading
            )
        except Exception as e:
            logger.error(f"Error streaming audio for article ID {article_id}: {e}")
            return jsonify({'error': str(e)}), 500

from asgiref.wsgi import WsgiToAsgi
wsgi_app = WsgiToAsgi(app.asgi_app)

wsgi_app = app.asgi_app

if __name__ == '__main__':
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(app.run_task(host='0.0.0.0', port=5000, debug=True))
    except Exception as e:
        logger.critical(f"Failed to start the application: {e}")