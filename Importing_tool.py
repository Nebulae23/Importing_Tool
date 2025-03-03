import requests
import webbrowser
import re
import time
import json
import secrets
import hashlib
import base64
from googlesearch import search

# AniList API credentials
CLIENT_ID = "1234567890"
CLIENT_SECRET = "1234567890"
REDIRECT_URI = "http://localhost:8080"  # Must match the redirect URI registered in your AniList app

# MyAnimeList API credentials
MAL_CLIENT_ID = "1234567890"
MAL_CLIENT_SECRET = "1234567890"  # Add your MAL client secret here
MAL_REDIRECT_URI = "http://localhost:8080"  # Make sure this matches exactly what's registered in MAL

# AniList API endpoints
ANILIST_API_URL = "https://graphql.anilist.co"
ANILIST_AUTH_URL = "https://anilist.co/api/v2/oauth/authorize"
ANILIST_TOKEN_URL = "https://anilist.co/api/v2/oauth/token"
MAL_API_URL = "https://api.myanimelist.net/v2"
MAL_AUTH_URL = "https://myanimelist.net/v1/oauth2/authorize"
MAL_TOKEN_URL = "https://myanimelist.net/v1/oauth2/token"

# GraphQL query to search for manga by title
SEARCH_MANGA_QUERY = """
query ($search: String) {
    Page(perPage: 50) {  # Increase the number of search results
        media(search: $search, type: MANGA) {
            id
            title {
                romaji
                english
            }
        }
    }
}
"""

# GraphQL mutation to update manga status
UPDATE_MANGA_STATUS_MUTATION = """
mutation ($mediaId: Int, $status: MediaListStatus, $progress: Int) {
    SaveMediaListEntry(mediaId: $mediaId, status: $status, progress: $progress) {
        id
        status
        progress
    }
}
"""

def generate_code_verifier():
    """Generate a code verifier for PKCE."""
    token = secrets.token_urlsafe(100)
    return token[:128]  # Ensure length is exactly 128 characters

def generate_code_challenge(code_verifier):
    """Generate a code challenge for PKCE (MAL uses plain transformation)."""
    return code_verifier  # For MAL, code_challenge is identical to code_verifier

def get_authorization_code():
    auth_url = f"{ANILIST_AUTH_URL}?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code"
    print("Please authorize the application by visiting this URL:")
    print(auth_url)
    webbrowser.open(auth_url)
    return input("Enter the authorization code from the redirect URL: ")

def get_access_token(authorization_code):
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": authorization_code
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    response = requests.post(ANILIST_TOKEN_URL, json=data, headers=headers)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print("Failed to get access token. Response details:")
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        raise Exception("Failed to get access token")

def handle_rate_limit():
    RATE_LIMIT_WAIT = 60  # Fixed 60 seconds wait time
    print(f"\nRate limit reached. Waiting {RATE_LIMIT_WAIT} seconds before retrying...")
    time.sleep(RATE_LIMIT_WAIT)
    print("Resuming operations...")

def make_request_with_retry(url, json_data, headers, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=json_data, headers=headers)
            
            if response.status_code == 429:  # Rate limit hit
                handle_rate_limit()
                continue
            
            return response
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:  # Last attempt
                raise e
            
            print(f"\nRequest failed. Retrying in 5 seconds...")
            time.sleep(5)  # Simple 5 second retry delay for other errors
    
    return None

def get_mal_authorization_code():
    """Get the authorization code from MyAnimeList using PKCE."""
    code_verifier = generate_code_verifier()
    code_challenge = code_verifier  # For MAL, they're the same
    
    auth_url = (
        f"{MAL_AUTH_URL}"
        f"?response_type=code"
        f"&client_id={MAL_CLIENT_ID}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=plain"  # MAL only supports plain
        f"&redirect_uri={MAL_REDIRECT_URI}"
        f"&state=RequestID42"
    )
    
    print("\nCode verifier (save this):", code_verifier)
    print("\nPlease authorize the MAL application by visiting this URL:")
    print(auth_url)
    webbrowser.open(auth_url)
    
    # Get the full redirect URL from user
    redirect_url = input("\nEnter the full redirect URL: ")
    
    # Extract the code parameter from the URL
    try:
        from urllib.parse import parse_qs, urlparse
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        auth_code = query_params.get('code', [None])[0]
        
        if not auth_code:
            raise ValueError("No authorization code found in the redirect URL")
            
        print(f"Extracted authorization code: {auth_code}")
        return auth_code, code_verifier
    except Exception as e:
        print(f"Error extracting authorization code: {e}")
        raise

def get_mal_access_token(authorization_code, code_verifier):
    """Exchange the authorization code for a MAL access token using PKCE."""
    data = {
        "client_id": MAL_CLIENT_ID,
        "grant_type": "authorization_code",
        "code": authorization_code,
        "code_verifier": code_verifier,
        "redirect_uri": MAL_REDIRECT_URI
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    try:
        # Convert data to URL-encoded format
        encoded_data = "&".join([f"{k}={requests.utils.quote(str(v))}" for k, v in data.items()])
        
        print("\nSending token request with data:")
        print(encoded_data)
        print("\nRequest headers:")
        print(headers)
        
        response = requests.post(MAL_TOKEN_URL, data=encoded_data, headers=headers)
        print(f"\nResponse status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print("Failed to get MAL access token. Response details:")
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")
            raise Exception("Failed to get MAL access token")
    except Exception as e:
        print(f"Error getting MAL access token: {e}")
        raise

def standardize_manga_name(original_name, found_name, source="AniList"):
    """Update manga_bookmarks.txt with the standardized name from AniList/MAL."""
    try:
        # Don't update if the names are the same (case-insensitive)
        if original_name.lower() == found_name.lower():
            return original_name

        with open("manga_bookmarks.txt", "r", encoding="utf-8") as file:
            lines = file.readlines()
        
        updated = False
        with open("manga_bookmarks.txt", "w", encoding="utf-8") as file:
            for line in lines:
                if "||" in line:
                    title, chapter = line.split("||")
                    if title.strip().lower() == original_name.lower():
                        line = f"{found_name} || {chapter}"
                        updated = True
                file.write(line)
        
        if updated:
            print(f"Updated manga name from '{original_name}' to '{found_name}' (source: {source})")
            
            # Also update the name in progress.txt if it exists
            try:
                with open("progress.txt", "r", encoding="utf-8") as file:
                    progress_lines = file.readlines()
                
                with open("progress.txt", "w", encoding="utf-8") as file:
                    for line in progress_lines:
                        if line.strip().lower() == original_name.lower():
                            file.write(f"{found_name}\n")
                        else:
                            file.write(line)
            except FileNotFoundError:
                pass  # progress.txt doesn't exist yet
        
        return found_name
    except Exception as e:
        print(f"Error updating manga name: {e}")
        return original_name

def extract_chapter_number(chapter_text):
    """Extract chapter number from various formats or return default."""
    try:
        # Remove common words and clean the text
        chapter_text = chapter_text.lower().strip()
        
        # Try to find any number in the string
        numbers = re.findall(r'\d+\.?\d*', chapter_text)
        if numbers:
            return float(numbers[0])
        
        # If no number found, check for volume information
        if "vol." in chapter_text or "volume" in chapter_text:
            vol_numbers = re.findall(r'vol(?:ume)?\s*\.?\s*(\d+)', chapter_text)
            if vol_numbers:
                # Multiply volume number by 5 as a rough estimate of chapters per volume
                return float(vol_numbers[0]) * 5
        
        print(f"Could not extract chapter number from: {chapter_text}")
        return 0  # Default to chapter 0 if no number found
        
    except Exception as e:
        print(f"Error extracting chapter number: {e}")
        return 0

def parse_file(file_path):
    """Parse the manga bookmarks file with improved chapter handling."""
    manga_list = []
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            if "||" in line:
                title, chapter = line.split("||")
                title = title.strip()
                chapter = chapter.strip()
                
                # Extract chapter number using the new function
                chapter_number = extract_chapter_number(chapter)
                manga_list.append((title, str(chapter_number)))
                
                if chapter_number == 0:
                    print(f"Warning: Could not determine chapter number for '{title}', defaulting to 0")
    return manga_list

def save_progress(processed_titles, file_path="progress.txt"):
    with open(file_path, "w", encoding="utf-8") as f:
        for title in processed_titles:
            f.write(f"{title}\n")

def load_progress(file_path="progress.txt"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def get_alternative_names(title, mal_access_token=None):
    """Search MyAnimeList for alternative names of the manga."""
    print(f"\nSearching for alternative names for: {title}")
    
    # For client auth, we can just use the client ID in the header
    headers = {
        "X-MAL-CLIENT-ID": MAL_CLIENT_ID
    }
    
    try:
        # Search MAL API with proper query parameter
        search_url = f"{MAL_API_URL}/manga"
        
        # Clean and encode the query parameter
        cleaned_title = title.strip()
        # Remove special characters but keep Japanese characters
        cleaned_title = re.sub(r'[^\w\s\-\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', '', cleaned_title)
        # Take only the first few meaningful words to increase chances of a match
        words = cleaned_title.split()
        if len(words) > 3:
            # If title has Japanese characters, prioritize them
            jp_words = [w for w in words if any('\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF' or '\u4E00' <= c <= '\u9FFF' for c in w)]
            if jp_words:
                cleaned_title = ' '.join(jp_words[:3])
            else:
                # Otherwise take first 3 words but avoid common words
                skip_words = {'the', 'a', 'an', 'in', 'on', 'at', 'my', 'your', 'was', 'is', 'are', 'to', 'for', 'of', 'with'}
                meaningful_words = [w for w in words if w.lower() not in skip_words]
                cleaned_title = ' '.join(meaningful_words[:3])
        
        params = {
            "q": cleaned_title,
            "limit": 5,
            "fields": "alternative_titles,title",  # Request specific fields we need
            "offset": 0
        }
        
        print(f"Searching MAL with cleaned query: {cleaned_title}")
        response = requests.get(search_url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            alternative_names = set()
            best_match = None
            best_match_score = 0
            
            for manga in data.get("data", []):
                node = manga.get("node", {})
                main_title = node.get("title")
                
                # Calculate match score for the main title
                if isinstance(main_title, str):
                    score = calculate_title_match_score(title, main_title)
                    if score > best_match_score:
                        best_match_score = score
                        best_match = main_title
                    alternative_names.add(main_title)
                
                # Add alternative titles
                alt_titles = node.get("alternative_titles", {})
                if isinstance(alt_titles, dict):
                    for titles in alt_titles.values():
                        if isinstance(titles, str):
                            score = calculate_title_match_score(title, titles)
                            if score > best_match_score:
                                best_match_score = score
                                best_match = titles
                            alternative_names.add(titles)
                        elif isinstance(titles, list):
                            for t in titles:
                                if t:
                                    score = calculate_title_match_score(title, t)
                                    if score > best_match_score:
                                        best_match_score = score
                                        best_match = t
                                    alternative_names.add(t)
            
            # If we found a good match from MAL, update the manga name
            if best_match and best_match_score > 0.6:  # Threshold for considering it a good match
                standardize_manga_name(title, best_match, "MyAnimeList")
            
            return alternative_names
            
        elif response.status_code == 429:
            print("MyAnimeList rate limit reached. Waiting 60 seconds...")
            time.sleep(60)
            return set()
        else:
            print(f"MyAnimeList API error: {response.status_code}")
            print(f"Response: {response.text}")
            return set()
            
    except Exception as e:
        print(f"Error searching MyAnimeList: {e}")
        return set()

def calculate_title_match_score(title1, title2):
    """Calculate a similarity score between two titles."""
    # Convert both titles to lowercase for comparison
    t1 = title1.lower()
    t2 = title2.lower()
    
    # Direct match
    if t1 == t2:
        return 1.0
    
    # One title contains the other
    if t1 in t2 or t2 in t1:
        return 0.8
    
    # Calculate word overlap
    words1 = set(re.findall(r'\w+', t1))
    words2 = set(re.findall(r'\w+', t2))
    
    if not words1 or not words2:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0

def search_manga(title, access_token):
    # First try with the original title
    manga_id, found_title = search_manga_with_title(title, access_token)
    if manga_id:
        if found_title:
            title = standardize_manga_name(title, found_title, "AniList")
        return manga_id
    
    # If not found, try with alternative names
    print("\nTrying to find alternative names...")
    alternative_names = get_alternative_names(title)
    
    if not alternative_names:
        print("No alternative names found, continuing with original title.")
        return None
    
    print("\nTrying alternative names...")
    for alt_name in alternative_names:
        try:
            manga_id, found_title = search_manga_with_title(alt_name, access_token)
            if manga_id:
                if found_title:
                    title = standardize_manga_name(title, found_title, "AniList")
                print(f"Found manga using alternative name: {alt_name}")
                return manga_id
            time.sleep(2)
        except Exception as e:
            print(f"Error searching with alternative name '{alt_name}': {e}")
            continue
    
    return None

def search_manga_with_title(title, access_token):
    """Helper function to search manga with a specific title. Now returns both ID and title."""
    variables = {"search": title}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    response = make_request_with_retry(
        ANILIST_API_URL,
        {"query": SEARCH_MANGA_QUERY, "variables": variables},
        headers
    )
    
    if response and response.status_code == 200:
        data = response.json()
        media_list = data["data"]["Page"]["media"]
        if media_list:
            print(f"\nSearching for: {title}")
            print("Found these matches:")
            for media in media_list[:5]:  # Show first 5 results for debugging
                print(f"- ID: {media['id']}")
                print(f"  English: {media['title']['english']}")
                print(f"  Romaji: {media['title']['romaji']}")
            
            # First try exact matches
            for media in media_list:
                if media["title"]["english"] and title.lower() == media["title"]["english"].lower():
                    print(f"Found exact English match: {media['title']['english']}")
                    return media["id"], media["title"]["english"]
                if media["title"]["romaji"] and title.lower() == media["title"]["romaji"].lower():
                    print(f"Found exact Romaji match: {media['title']['romaji']}")
                    return media["id"], media["title"]["romaji"]
            
            # Then try partial matches
            for media in media_list:
                # Check if the search title is contained within the manga title or vice versa
                if media["title"]["english"] and (
                    title.lower() in media["title"]["english"].lower() or
                    media["title"]["english"].lower() in title.lower()
                ):
                    print(f"Found partial English match: {media['title']['english']}")
                    return media["id"], media["title"]["english"]
                if media["title"]["romaji"] and (
                    title.lower() in media["title"]["romaji"].lower() or
                    media["title"]["romaji"].lower() in title.lower()
                ):
                    print(f"Found partial Romaji match: {media['title']['romaji']}")
                    return media["id"], media["title"]["romaji"]
            
            # If still no match, return the first result
            first_title = media_list[0]["title"]["english"] or media_list[0]["title"]["romaji"]
            print(f"No exact or partial match found. Using first result: {first_title}")
            return media_list[0]["id"], first_title
        else:
            print(f"No results found for manga: {title}")
    else:
        print(f"API request failed with status code: {response.status_code}")
        print(f"Response: {response.text}")
    return None, None

# Update manga status and progress
def update_manga_status(media_id, status, progress, access_token):
    variables = {
        "mediaId": media_id,
        "status": status,
        "progress": progress
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    response = make_request_with_retry(
        ANILIST_API_URL,
        {"query": UPDATE_MANGA_STATUS_MUTATION, "variables": variables},
        headers
    )
    
    if response and response.status_code == 200:
        data = response.json()
        if "errors" not in data:
            print(f"Updated manga {media_id} to status '{status}' and progress {progress}.")
        else:
            print(f"Failed to update manga {media_id}: {data['errors'][0]['message']}")
    else:
        print(f"Failed to update manga {media_id}: {response.text if response else 'No response'}")

# Main function
def main():
    try:
        # Load previously processed titles
        processed_titles = load_progress()
        
        # Step 1: Get the authorization code
        authorization_code = get_authorization_code()

        # Step 2: Get the access token
        access_token = get_access_token(authorization_code)
        print("Access token obtained successfully!")

        # Step 3: Parse the file and update manga status
        manga_list = parse_file("manga_bookmarks.txt")
        
        while True:  # Keep trying until all manga are processed
            try:
                for title, chapter_number in manga_list:
                    # Skip already processed titles
                    if title in processed_titles:
                        print(f"Skipping already processed manga: {title}")
                        continue
                    
                    retry_count = 0
                    while retry_count < 3:  # Maximum 3 retries per manga
                        try:
                            manga_id = search_manga(title, access_token)
                            if manga_id:
                                update_manga_status(manga_id, "CURRENT", int(float(chapter_number)), access_token)
                                processed_titles.add(title)
                                save_progress(processed_titles)  # Save progress after each successful update
                                break  # Break the retry loop on success
                            else:
                                print(f"Manga '{title}' not found on AniList.")
                                break  # Break if manga truly not found
                            
                        except requests.exceptions.RequestException as e:
                            if hasattr(e, 'response') and e.response and e.response.status_code == 429:
                                handle_rate_limit()
                                retry_count += 1
                                continue
                            else:
                                raise e
                    
                    # Add a small delay between manga processing
                    time.sleep(2)
                
                # If we get here, all manga have been processed
                print("\nAll manga processing completed!")
                break
                    
            except Exception as e:
                print(f"\nAn error occurred: {str(e)}")
                print("Saving progress and waiting 60 seconds before retrying...")
                save_progress(processed_titles)
                time.sleep(60)
                continue
                    
    except Exception as e:
        print(f"A critical error occurred: {e}")
        print("Progress has been saved. You can restart the script to continue from where it left off.")
        
if __name__ == "__main__":
    main()