# Manga Import Tool

This tool helps you synchronize your manga reading progress between your local list and AniList/MyAnimeList. It automatically updates your reading progress on AniList based on your local manga bookmarks.

## Author

Created by [Nebulae23](https://github.com/Nebulae23)

This tool is specifically for importing manga progress to AniList/MyAnimeList. For generating the input file (`manga_bookmarks.txt`), you can use the [Manga Bookmarks Export](https://greasyfork.org/en/scripts/390432-mananelo-mangakakalot-manganato-manga4life-bookmarks-export) userscript by sm00nie (Note: I don't maintain the export script, I'm only the author of this AniList import tool).

### Supported Source Sites
The input file can be generated from bookmarks on:
- mangakakalot.fun
- mangakakalot.gg
- nelomanga.com
- natomanga.com
- manganato.gg

Note: When using the export script, you'll need to remove the first 3 lines from the generated file before using it with this tool.

## Features

- Imports manga reading progress from a local text file to AniList
- Supports various chapter number formats (decimal, volume-based)
- Handles rate limiting and retries automatically
- Standardizes manga titles using AniList/MyAnimeList data
- Maintains progress tracking to resume interrupted imports
- Supports alternative title matching for better accuracy

## Prerequisites

- Python 3.6 or higher
- A registered AniList application (for API access)
- A registered MyAnimeList application (for API access)

## Getting API Credentials

### AniList API Credentials
1. Go to [AniList Developer Settings](https://anilist.co/settings/developer)
2. Click "Create New Client"
3. Fill in the following:
   - Name: Any name for your application
   - Redirect URL: `http://localhost:8080`
   - Homepage URL: (Optional) Can be left blank
4. Save the generated Client ID and Client Secret

For detailed instructions, see the [AniList API Documentation](https://anilist.gitbook.io/anilist-apiv2-docs/overview/oauth/getting-started).

### MyAnimeList API Credentials
1. Go to [MyAnimeList API Applications](https://myanimelist.net/apiconfig)
2. Click "Create ID"
3. Fill in the required information:
   - App Name: Any name for your application
   - App Type: "Web"
   - App Description: Brief description of your tool
   - Homepage URL: `http://localhost:8080`
   - Redirect URL: `http://localhost:8080`
4. Accept the API License Agreement
5. Save the generated Client ID and Client Secret

For detailed instructions, see the [MyAnimeList API Documentation](https://myanimelist.net/apiconfig/references/authorization).

## Installation

1. Clone this repository or download the files
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Before running the tool, you need to set up your API credentials in `Importing_tool.py`:

1. AniList credentials:
```python
CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"
REDIRECT_URI = "http://localhost:8080"  # Must match your AniList app settings
```

2. MyAnimeList credentials:
```python
MAL_CLIENT_ID = "your_mal_client_id"
MAL_CLIENT_SECRET = "your_mal_client_secret"
MAL_REDIRECT_URI = "http://localhost:8080"  # Must match your MAL app settings
```

## Input File Format

The tool expects a file named `manga_bookmarks.txt` with the following format:

```
Manga Title || Viewed: Chapter X
```

Examples:
```
Solo Leveling || Viewed: Chapter 200
Tales of Demons and Gods || Viewed: Chapter 480.1
Berserk || Viewed: Chapter 378: Invited Assassin
Isekai Nonbiri Nouka || Viewed: Vol.12 Chapter 253: Garf's Adventure (3)
```

### Supported Chapter Format Patterns:

- Simple chapter numbers: `Chapter 123`
- Decimal chapters: `Chapter 123.5`
- Volume-based: `Vol.12 Chapter 253`
- Chapters with titles: `Chapter 378: Chapter Title`
- Volume-only: `Vol.5` (will be converted to an estimated chapter number)

## Usage

1. Prepare your `manga_bookmarks.txt` file with your manga list
2. Run the tool:
```bash
python Importing_tool.py
```

3. The tool will:
   - Open your browser for AniList authorization
   - Ask you to paste the authorization code
   - Start importing your manga list
   - Show progress and any errors during import
   - Save progress in case of interruption

## Progress Tracking

The tool creates a `progress.txt` file to track which manga entries have been processed. If the tool is interrupted, you can restart it, and it will continue from where it left off.

## Error Handling

- The tool automatically handles rate limits
- Retries failed requests
- Logs errors for manual review
- Saves progress regularly to prevent data loss

## Limitations

- Maximum of 50 search results per manga title
- Rate limiting by AniList/MyAnimeList APIs
- Title matching may not be perfect for very different localizations
- Some manga titles might need manual intervention if not found

## Troubleshooting

If you encounter issues:

1. Check your API credentials are correct
2. Verify your `manga_bookmarks.txt` follows the correct format
3. Ensure your internet connection is stable
4. Check the console output for specific error messages
5. Delete `progress.txt` to force a fresh start if needed

## Contributing

Feel free to submit issues and enhancement requests! 