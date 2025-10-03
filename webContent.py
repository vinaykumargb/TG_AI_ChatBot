import requests
from bs4 import BeautifulSoup

def get_readable_content(url: str) -> str:
    """
    Fetches and returns cleaned, human-readable text from a webpage.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/126.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove unwanted tags
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
            tag.decompose()

        # Extract readable text
        text = soup.get_text(separator="\n", strip=True)
        clean_lines = [line for line in text.splitlines() if line.strip()]
        return "\n".join(clean_lines)

    else:
        return f"Failed to fetch content. Status code: {response.status_code}"