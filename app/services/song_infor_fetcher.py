from difflib import SequenceMatcher
import re
from bs4 import BeautifulSoup, Tag
import urllib.parse
import requests
import os
from dotenv import load_dotenv

load_dotenv()

GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")  

STOP_WORDS = {'by', 'the', 'a', 'an', 'of', '-', '–', 'x', 'ft', 'feat', 'and', '&'}

def reduce_title(title):
    title = re.split(r'[x]', title, maxsplit=1)[0]
    return title.strip()

def clean_text(text):
    text = re.sub(r'[^\w\s]', '', text.lower())
    words = text.split()
    return ' '.join(word for word in words if word not in STOP_WORDS)

def calculate_similarity(query, title):
    query_cleaned = clean_text(query)
    title_cleaned = clean_text(reduce_title(title))
    query_words = set(query_cleaned.split())
    title_words = set(title_cleaned.split())
    if not query_words:
        return 0
    common_words = query_words.intersection(title_words)
    query_match_ratio = len(common_words) / len(query_words)
    overall_similarity = SequenceMatcher(None, query_cleaned, title_cleaned).ratio()
    return max(query_match_ratio, overall_similarity)

def fetch_lyrics_from_genius(query):
    reduced_query = reduce_title(query)
    cleaned_query = clean_text(reduced_query)
    encoded_query = urllib.parse.quote(cleaned_query)
    search_url = f"https://api.genius.com/search?q={encoded_query}"
    headers = {"Authorization": f"Bearer {GENIUS_TOKEN}"}
    response = requests.get(search_url, headers=headers)
    if response.status_code != 200:
        return None, f"Failed to fetch lyrics (status {response.status_code})"
    hits = response.json().get("response", {}).get("hits", [])
    if not hits:
        return None, "Lyrics not found"
    result = hits[0]["result"]
    song_url = result["url"]
    title = result["full_title"]
    artist = result["artist_names"]
    song_art_image_url = result["song_art_image_url"]
    similarity_ratio = calculate_similarity(cleaned_query, title)
    if similarity_ratio < 0.7:
        return None, "No matching song found"
    # Scrape lyrics
    page = requests.get(song_url)
    soup = BeautifulSoup(page.text, "html.parser")
    lyrics_elements = soup.find_all("div", attrs={"data-lyrics-container": "true"})
    lyrics = []
    for div in lyrics_elements:
        if isinstance(div, Tag):
            for content in div.contents:
                if isinstance(content, str):
                    lyrics.append(content.strip())
                elif isinstance(content, Tag) and content.name == "br":
                    lyrics.append("\n")
                elif isinstance(content, Tag) and content.name == "a":
                    a_text = content.get_text(separator="\n", strip=True)
                    lyrics.append(a_text)
                    lyrics.append("\n")
    lyrics = " ".join(lyrics).strip()
    filtered_lyrics = "\n".join([
        line for line in lyrics.split("\n")
        if not line.startswith("[") and line.strip()
    ])
    if not filtered_lyrics:
        return None, "Lyrics not found"
    return {
        'lyrics': filtered_lyrics,
        'title': title,
        'artist': artist,
        'song_art_image_url': song_art_image_url
    }, None