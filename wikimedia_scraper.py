#wikimedia_scraper.py
#import necessary libraries
# wikimedians_scraper.py
import requests
from bs4 import BeautifulSoup
import markdownify
from slugify import slugify
import os
import re

# Main events page
EVENTS_PAGE = "https://meta.wikimedia.org/wiki/Wikimedians_of_Kerala/Activities/Events"
WIKI_BASE = "https://meta.wikimedia.org"

def fetch_page(url):
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; EventScraper/1.0)'}
    response = requests.get(url, headers=headers)
    return BeautifulSoup(response.content, 'html.parser')

def extract_events(soup):
    """Extract event links and titles from main page"""
    events = []
    # Target tables and links - adjust selectors based on actual structure
    links = soup.find_all('a', href=re.compile(r'/wiki/Wikimedians_of_Kerala/Events/'))
    for link in links:
        title = link.get_text().strip()
        href = link.get('href')
        if title and href:
            events.append({
                'title': title,
                'url': WIKI_BASE + href if href.startswith('/') else href
            })
    return events

def convert_html_to_md(soup, base_url):
    """Convert full page HTML to clean Markdown"""
    # Clean up wiki-specific elements
    for elem in soup(['sup', 'span.editsection']):
        elem.decompose()
    
    md_content = markdownify.markdownify(str(soup), heading_style="ATX")
    return md_content.strip()

def scrape_event_details(event):
    """Fetch and convert individual event page"""
    print(f"Processing: {event['title']}")
    soup = fetch_page(event['url'])
    
    # Extract main content (usually #mw-content-text)
    content = soup.find('div', {'id': 'mw-content-text'})
    if not content:
        content = soup.find('div', class_='mw-parser-output')
    
    md_content = convert_html_to_md(content, event['url'])
    
    # Extract images
    images = []
    for img in content.find_all('img'):
        src = img.get('src')
        if src and ('commons.wikimedia.org' in src or 'upload.wikimedia.org' in src):
            images.append(src)
    
    return {
        'title': event['title'],
        'slug': slugify(event['title']),
        'content': md_content,
        'images': images,
        'url': event['url']
    }

def generate_hugo_pages(events_data, output_dir="content/events"):
    """Generate Hugo Markdown frontmatter pages"""
    os.makedirs(output_dir, exist_ok=True)
    
    for event in events_data:
        slug = event['slug']
        filename = os.path.join(output_dir, f"{slug}.md")
        
        frontmatter = f"""---
title: "{event['title']}"
date: {pd.Timestamp.now().isoformat()}
url: "{event['url']}"
images:
"""
        for img in event['images']:
            frontmatter += f"  - {img}\n"
        frontmatter += "---\n\n"
        
        content = frontmatter + event['content']
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Generated: {filename}")

# Main execution
if __name__ == "__main__":
    print("Fetching main events page...")
    main_soup = fetch_page(EVENTS_PAGE)
    
    events = extract_events(main_soup)
    print(f"Found {len(events)} events")
    
    events_data = []
    for event in events[:10]:  # Limit for testing
        events_data.append(scrape_event_details(event))
    
    generate_hugo_pages(events_data)
    print("Hugo pages generated in content/events/")
