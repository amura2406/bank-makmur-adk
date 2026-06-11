import os
import json
import re
import requests
from bs4 import BeautifulSoup

CACHE_PATH = os.path.join(os.path.dirname(__file__), "data", "raw_faq_cache.json")
URL = "https://www.jago.com/syariah/faq-mobile/id"

def crawl_faq() -> list[dict]:
    """
    Crawls Bank Jago FAQ mobile page.
    If offline or if the fetch fails, falls back to the cached json file.
    """
    try:
        response = requests.get(URL, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []
            
            # Locate potential Q&A containers
            # Common patterns on Jago: accordion headers and content
            faq_containers = soup.find_all(class_=re.compile(r"accordion|faq", re.I))
            for container in faq_containers:
                question_el = container.find(class_=re.compile(r"question|title|header", re.I))
                answer_el = container.find(class_=re.compile(r"answer|content|body", re.I))
                if question_el and answer_el:
                    articles.append({
                        "question": question_el.get_text(strip=True),
                        "answer": answer_el.get_text(strip=True)
                    })
            
            # Fallback if parsing found nothing
            if articles:
                return articles
            
            # Simple fallback parsers for other potential DOM layouts
            # Let's try h3/h4 headers for questions and following paragraphs for answers
            headers = soup.find_all(['h3', 'h4'])
            for h in headers:
                if any(x in h.get_text().lower() for x in ["apa", "bagaimana", "apakah", "berapa", "mengapa"]):
                    next_node = h.find_next_sibling()
                    if next_node and next_node.name in ['p', 'div']:
                        articles.append({
                            "question": h.get_text(strip=True),
                            "answer": next_node.get_text(strip=True)
                        })
            
            if articles:
                return articles
            else:
                print("Live parse found no articles. Falling back to cache.")
        else:
            print(f"Failed to fetch live URL, status code {response.status_code}. Falling back to cache.")
    except Exception as e:
        print(f"Network error or timeout during crawl: {e}. Falling back to cache.")
    
    # Fallback to offline cache
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

if __name__ == "__main__":
    faqs = crawl_faq()
    print(f"Crawl completed. Retrieved {len(faqs)} FAQ articles.")
