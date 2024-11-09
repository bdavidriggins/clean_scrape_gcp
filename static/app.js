/**
 * Main JavaScript Module for Clean Scrape Application
 * 
 * This script manages the client-side interactions for the Clean Scrape application.
 * It handles loading, viewing, editing, saving, and deleting articles by communicating
 * with the backend API endpoints. The module ensures dynamic updates to the DOM based
 * on user actions and server responses.
 */

let currentArticleId = null;
let isUrlInput = true;



// Load articles when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize loadingManager after DOM is loaded
    loadingManager = {
        overlay: document.getElementById('loadingOverlay'),
        activeRequests: 0,
        show() {
            this.activeRequests++;
            this.overlay.classList.add('active');
        },
        hide() {
            this.activeRequests--;
            if (this.activeRequests <= 0) {
                this.activeRequests = 0;
                this.overlay.classList.remove('active');
            }
        }
    };

    // Add event listeners
    document.getElementById('toggleInputType').addEventListener('click', toggleInputType);
    document.getElementById('addArticleButton').addEventListener('click', handleArticleSubmission);
    document.getElementById('viewLogButton').addEventListener('click', function(event) {
        event.preventDefault(); // Prevent any default action
        window.open('/log_viewer', '_blank');
    });

    loadArticles();
});


function toggleInputType() {
    isUrlInput = !isUrlInput;
    const toggleButton = document.getElementById('toggleInputType');
    const urlSection = document.getElementById('urlInputSection');
    const htmlSection = document.getElementById('htmlInputSection');

    if (isUrlInput) {
        toggleButton.textContent = 'Switch to HTML Input';
        urlSection.classList.add('active');
        htmlSection.classList.remove('active');
    } else {
        toggleButton.textContent = 'Switch to URL Input';
        urlSection.classList.remove('active');
        htmlSection.classList.add('active');
    }
}


async function handleArticleSubmission() {
    const addArticleButton = document.getElementById('addArticleButton');
    const urlInput = document.getElementById('newArticleUrlInput');
    const htmlInput = document.getElementById('newArticleHtmlInput');
    
    // Disable the button to prevent multiple submissions
    addArticleButton.disabled = true;

    // Clear input fields immediately
    const urlValue = urlInput.value.trim();
    const htmlValue = htmlInput.value.trim();
    urlInput.value = '';
    htmlInput.value = '';

    // Show processing notification
    showToast('Processing article...', 10000);  // Show for 10 seconds or until process completes

    try {
        if (isUrlInput) {
            await addArticleByUrl(urlValue);
        } else {
            await addArticleByHtml(htmlValue);
        }

        // Refresh the article list
        await loadArticles();

        // Show success notification
        showToast('Article added successfully!');

    } catch (error) {
        console.error('Error adding article:', error);
        
        // Show error notification
        showToast(`Failed to add article: ${error.message}`, 5000);

        // If there's an error, restore the input values
        if (isUrlInput) {
            urlInput.value = urlValue;
        } else {
            htmlInput.value = htmlValue;
        }
    } finally {
        // Re-enable the button
        addArticleButton.disabled = false;
    }
}


/**
 * Process and submit a new article based on HTML content
 * @param {string} htmlContent - The HTML content of the article to process
 */
async function addArticleByHtml(htmlContent) {
    if (!htmlContent) {
        throw new Error('Please enter HTML content');
    }
    
    const response = await fetch('/process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ html_content: htmlContent })
    });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Network response was not ok');
    }
    
    const data = await response.json();
    if (!data.success) {
        throw new Error(data.error || 'Failed to process article');
    }
    
}




/**
 * Fetch and display all articles from the server.
 */
async function loadArticles() {
    try {
        const response = await fetch('/get_articles_with_audio_status');
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const articles = await response.json();
        const articleList = document.getElementById('articleList');
        articleList.innerHTML = '';
        articles.forEach(article => {
            const li = document.createElement('li');
            li.className = 'article-item';
            
            // Determine which button to show based on audio status
            const audioButton = article.has_audio 
                ? `<button onclick="playAudio('${article.id}')" class="btn btn-secondary">
                     <img src="/static/feather/play.svg" alt="play" aria-hidden="true" class="icon-white">
                   </button>`
                : `<button onclick="ttsArticleContent('${article.id}')" class="btn btn-secondary">
                     <img src="/static/feather/mic.svg" alt="convert to speech" aria-hidden="true" class="icon-white">
                   </button>`;
            
            li.innerHTML = `
            <div class="article-header">
                <span class="article-name">${article.title}</span>
                <div class="article-buttons">
                    ${audioButton}
                    <button onclick="copyArticleContent('${article.id}')" class="btn btn-secondary">
                        <img src="/static/feather/copy.svg" alt="copy" aria-hidden="true" class="icon-white">
                    </button>
                    <button onclick="viewArticle('${article.id}')" class="btn btn-secondary">
                        <img src="/static/feather/book-open.svg" alt="view" aria-hidden="true" class="icon-white">
                    </button>
                    <button onclick="deleteArticle('${article.id}')" class="btn btn-danger">
                        <img src="/static/feather/delete.svg" alt="del" aria-hidden="true" class="icon-white">
                    </button>
                </div>
                <!-- Rest of the article HTML... -->
            </div>`;
            articleList.appendChild(li);
        });
    } catch (error) {
        console.error('Error loading articles:', error);
        showToast('Failed to load articles. Please try again.', 5000);
    }
}


function playAudio(articleId) {
    // Store current scroll position
    sessionStorage.setItem('scrollPosition', window.scrollY);
    // Navigate to audio player page
    window.location.href = `/audio_player/${articleId}`;
}



/**
 * Process and submit a new article based on URL input
 * @param {string} url - The URL of the article to process
 */
async function addArticleByUrl(url) {
    if (!url) {
        throw new Error('Please enter a URL');
    }
    try {
        new URL(url);
    } catch (e) {
        throw new Error('Please enter a valid URL');
    }
    
    const response = await fetch('/process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url })
    });
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
        throw new TypeError("Response was not JSON");
    }
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || `HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    if (!data.success) {
        throw new Error(data.error || 'Failed to process article');
    }
}

/**
 * Fetch and display the content of a specific article.
 * @param {number} id - The ID of the article to view.
 */
function viewArticle(id) {
    fetch(`/get_article/${id}`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(errData => { throw new Error(errData.error || 'Network response was not ok'); });
            }
            return response.json();
        })
        .then(article => {
            // Create editable fields for metadata
            document.getElementById('articleContent').innerHTML = `
                <div class="modal-content">
                    <span class="close-button" onclick="closeArticle()">&times;</span>
                    <div class="form-group">
                        <label for="editTitle">Title</label>
                        <input type="text" id="editTitle" value="${article.title || ''}" />
                    </div>
                    <div class="form-group">
                        <label for="editAuthor">Author</label>
                        <input type="text" id="editAuthor" value="${article.author || ''}" />
                    </div>
                    <div class="form-group">
                        <label for="editAuthor">URL</label>
                        <input type="text" id="editAuthor" value="${article.url || ''}" />
                    </div>
                    <div class="form-group">
                        <label for="editDescription">Description</label>
                        <textarea id="editDescription">${article.description || ''}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="articleText">Content</label>
                        <textarea id="articleText" class="expandable-textarea">${article.content || ''}</textarea>
                    </div>
                    <div class="button-group">
                        <button type="button" class="btn btn-save" onclick="saveArticle()">Save</button>
                        <button type="button" class="btn btn-cancel" onclick="closeArticle()">Close</button>
                    </div>
                </div>
            `;
            document.getElementById('articleContent').style.display = 'flex';
            currentArticleId = id;
        })
        .catch(error => {
            console.error('Error:', error);
            showToast(`Failed to load article: ${error.message}`, 5000);
        });
}


// And add this new function to handle the copying:
function copyArticleContent(id) {
    // Find the button using the article ID
    const buttonSelector = `button[onclick="copyArticleContent('${id}')"]`;
    const button = document.querySelector(buttonSelector);

    fetch(`/get_article/${id}`)
        .then(response => response.json())
        .then(article => {
            navigator.clipboard.writeText(article.content)
                .then(() => {
                    // Visual feedback using the found button
                    if (button) {
                        button.style.backgroundColor = '#4CAF50';
                        setTimeout(() => {
                            button.style.backgroundColor = '';
                        }, 500);
                    }
                    showToast('Article content copied to clipboard');
                })
                .catch(err => {
                    console.error('Failed to copy text: ', err);
                    showToast('Failed to copy text to clipboard', 5000);
                });
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Failed to fetch article content', 5000);
        });
}


//Get the article ID and send it to ge the article TTS'd
function ttsArticleContent(id) {
    const buttonSelector = `button[onclick="ttsArticleContent('${id}')"]`;
    const button = document.querySelector(buttonSelector);
    
    if (button) {
        button.disabled = true;
        const originalContent = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
        

        showToast('Converting article to speech...', 10000);

        fetch(`/tts_article/${id}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Update the button to show play icon instead of mic
                button.onclick = () => playAudio(id);
                button.innerHTML = '<img src="/static/feather/play.svg" alt="play" aria-hidden="true" class="icon-white">';
                showToast('Article converted to speech successfully');
                button.style.backgroundColor = '#4CAF50';
                setTimeout(() => {
                    button.style.backgroundColor = '';
                }, 1000);
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Failed to process text-to-speech conversion', 5000);
                button.innerHTML = originalContent;
            })
            .finally(() => {
                button.disabled = false;
                loadingManager.hide();
            });
    }
}


/**
 * Save the edited content of the current article.
 */
function saveArticle() {
    if (!currentArticleId) return;

    const content = document.getElementById('articleText').value;
    const title = document.getElementById('editTitle').value;
    const author = document.getElementById('editAuthor').value;
    const description = document.getElementById('editDescription').value;

    showToast('Saving article...', 10000);

    fetch(`/update_article/${currentArticleId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            content, 
            title,
            author,
            description
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errData => { 
                throw new Error(errData.error || 'Network response was not ok'); 
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showToast('Article saved successfully');
            loadArticles();
            closeArticle();
        } else {
            showToast(data.error || 'Failed to save article', 5000);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast(`Failed to save article: ${error.message}`, 5000);
    })
    .finally(() => {
        loadingManager.hide();
    });
}

/**
 * Delete a specific article after user confirmation.
 * @param {number} id - The ID of the article to delete.
 */
function deleteArticle(id) {
    if (!confirm('Are you sure you want to delete this article?')) return;

    
    showToast('Deleting article...', 10000);
    fetch(`/delete_article/${id}`, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errData => { throw new Error(errData.error || 'Network response was not ok'); });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showToast('Article deleted successfully');
            loadArticles();
            if (currentArticleId === id) {
                closeArticle();
            }
        } else {
            showToast(data.error || 'Failed to delete article', 5000);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast(`Failed to delete article: ${error.message}`, 5000);
    })
    .finally(() => {
        loadingManager.hide();
    });
}

/**
 * Close the article view/edit modal and reset the current article ID.
 */
function closeArticle() {
    document.getElementById('articleContent').style.display = 'none';
    currentArticleId = null;
}



function showToast(message, duration = 3000) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
        <span>${message}</span>
        <button class="toast-close">&times;</button>
    `;
    
    const toastContainer = document.getElementById('toast');
    toastContainer.appendChild(toast);
    
    // Trigger reflow
    toast.offsetHeight;
    
    toast.classList.add('show');
    
    const closeToast = () => {
        toast.classList.remove('show');
        setTimeout(() => {
            toastContainer.removeChild(toast);
        }, 300);
    };
    
    toast.querySelector('.toast-close').addEventListener('click', closeToast);
    
    if (duration > 0) {
        setTimeout(closeToast, duration);
    }
}