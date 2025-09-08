import requests
from bs4 import BeautifulSoup
import re
import json
import time
import logging
from urllib.parse import urlparse
from .text_parser import extract_incidents_from_text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Site-specific extraction rules
SITE_RULES = {
    'aljazeera.com': {
        'article_selectors': ['article', '.article-body', '.wysiwyg'],
        'date_selectors': ['header time', '.date-simple'],
        'title_selectors': ['h1.article-title', '.article-header h1'],
    },
    'bbc.com': {
        'article_selectors': ['article', '[data-component="text-block"]', '.ssrcss-11r1m41-RichTextContainer'],
        'date_selectors': ['time', 'header time'],
        'title_selectors': ['h1', '.ssrcss-1pl2zfy-StyledHeading'],
    },
    'reuters.com': {
        'article_selectors': ['.article-body', '.paywall-article'],
        'date_selectors': ['time', '.published-datetime'],
        'title_selectors': ['h1', '.article-header'],
    },
    # Default rules for unknown sites
    'default': {
        'article_selectors': ['article', '.article', '.content', '.entry-content', '.post-content', '.story-content',
                              'main'],
        'date_selectors': ['time', '.date', '.published', '.posted-on', 'meta[property="article:published_time"]'],
        'title_selectors': ['h1', '.title', '.headline', '.entry-title'],
    }
}


def get_site_rules(url):
    """Get the appropriate extraction rules for a given URL"""
    domain = urlparse(url).netloc.lower()

    # Remove 'www.' prefix if present
    if domain.startswith('www.'):
        domain = domain[4:]

    # Find the most specific matching rule
    for site_domain, rules in SITE_RULES.items():
        if site_domain in domain:
            return rules

    return SITE_RULES['default']


def clean_text(text):
    """Clean up extracted text"""
    if not text:
        return ""

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove common newsletter/subscription prompts
    text = re.sub(r'(subscribe to our newsletter|sign up for our daily newsletter|subscribe now)', '', text,
                  flags=re.IGNORECASE)

    # Remove social media prompts
    text = re.sub(r'(follow us on|share this article)', '', text, flags=re.IGNORECASE)

    # Remove advertising text
    text = re.sub(r'(advertisement|sponsored content|paid content)', '', text, flags=re.IGNORECASE)

    return text.strip()


def extract_article_metadata(soup, url, rules):
    """Extract metadata like title, date, author from article"""
    metadata = {
        'title': None,
        'date': None,
        'source': urlparse(url).netloc,
        'url': url
    }

    # Extract title
    for selector in rules['title_selectors']:
        title_elem = soup.select_one(selector)
        if title_elem:
            metadata['title'] = title_elem.get_text().strip()
            break

    # Extract date
    for selector in rules['date_selectors']:
        date_elem = soup.select_one(selector)
        if date_elem:
            # Try to get datetime attribute first
            if date_elem.get('datetime'):
                metadata['date'] = date_elem['datetime']
            else:
                metadata['date'] = date_elem.get_text().strip()
            break

    # Look for structured data
    try:
        ld_json = soup.find('script', {'type': 'application/ld+json'})
        if ld_json:
            json_data = json.loads(ld_json.string)
            if isinstance(json_data, dict):
                if not metadata['date'] and 'datePublished' in json_data:
                    metadata['date'] = json_data['datePublished']
                if not metadata['title'] and 'headline' in json_data:
                    metadata['title'] = json_data['headline']
    except Exception as e:
        logger.warning(f"Error extracting structured data: {e}")

    return metadata


def extract_main_content(soup, rules):
    """Extract the main article content using site-specific rules"""
    content_text = ""

    # Try each selector in order until we find content
    for selector in rules['article_selectors']:
        content_elements = soup.select(selector)
        if content_elements:
            # Join text from all matching elements
            content_text = "\n\n".join([elem.get_text() for elem in content_elements])
            break

    # Fallback: if no content found, extract all paragraphs
    if not content_text:
        paragraphs = soup.find_all('p')
        content_text = "\n\n".join([p.get_text() for p in paragraphs])

    return clean_text(content_text)


def extract_images(soup, url):
    """Extract relevant images from the article"""
    images = []
    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    # Find all image elements in the article content
    img_elements = soup.find_all('img')
    for img in img_elements:
        # Skip small icons, logos, etc.
        if img.get('width') and int(img.get('width')) < 200:
            continue

        src = img.get('src', '')
        if src:
            # Handle relative URLs
            if src.startswith('/'):
                src = base_url + src

            # Extract alt text or caption
            alt_text = img.get('alt', '') or img.get('title', '')

            # Add to images list
            images.append({
                'url': src,
                'alt_text': alt_text
            })

    return images


def extract_incidents_from_url(url, user_agent=None):
    """
    Enhanced function to fetch a URL and extract incidents from its content
    """
    try:
        logger.info(f"Extracting incidents from URL: {url}")

        # Configurable user agent
        headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Fetch the URL with timeout and proper headers
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        # Get site-specific extraction rules
        rules = get_site_rules(url)

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract metadata
        metadata = extract_article_metadata(soup, url, rules)

        # Extract main content
        article_content = extract_main_content(soup, rules)

        # Extract images
        images = extract_images(soup, url)

        logger.info(f"Successfully extracted content: {len(article_content)} characters")

        # Extract incidents using text parser
        incidents = extract_incidents_from_text(article_content)

        # Enhance incidents with metadata
        for incident in incidents:
            incident['source'] = metadata['source']
            incident['article_url'] = url
            incident['article_title'] = metadata['title']
            incident['article_date'] = metadata['date']

            # Add relevant images if available
            if images:
                incident['images'] = images

        logger.info(f"Extracted {len(incidents)} incidents from the URL")
        return incidents

    except requests.exceptions.Timeout:
        logger.error(f"Timeout error while fetching URL: {url}")
        return [{"error": "Request timed out", "description": f"The request to {url} took too long to complete"}]

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error while fetching URL: {e}")
        return [{"error": f"HTTP Error: {e}", "description": f"The server returned an error response: {e}"}]

    except Exception as e:
        logger.error(f"Error extracting content from URL: {e}")
        return [{"error": str(e), "description": f"Failed to process URL: {url}"}]


def extract_incidents_from_multiple_urls(urls, delay=1):
    """Process multiple URLs and extract incidents from each"""
    all_incidents = []
    errors = []

    for i, url in enumerate(urls):
        logger.info(f"Processing URL {i + 1}/{len(urls)}: {url}")

        try:
            # Extract incidents from this URL
            incidents = extract_incidents_from_url(url)

            # Check for errors
            if incidents and 'error' in incidents[0]:
                errors.append({'url': url, 'error': incidents[0]['error']})
            else:
                all_incidents.extend(incidents)

            # Be nice to servers with a delay between requests
            if i < len(urls) - 1:
                time.sleep(delay)

        except Exception as e:
            errors.append({'url': url, 'error': str(e)})
            logger.error(f"Error processing URL {url}: {e}")

    return {
        'incidents': all_incidents,
        'errors': errors,
        'stats': {
            'total_urls': len(urls),
            'successful_urls': len(urls) - len(errors),
            'failed_urls': len(errors),
            'total_incidents': len(all_incidents)
        }
    }