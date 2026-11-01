
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

NOTICE_URL = "https://jeemain.nta.nic.in/public-notices/"

ALLOWED_DOMAINS = {
    "jeemain.nta.nic.in",
    "cdnbbsr.s3waas.gov.in"
}


def fetch_notices():
    headers = {
        "User-Agent": "Mozilla/5.0 NoticeSaathi/1.0"
    }

    try:
        response = requests.get(
            NOTICE_URL,
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        container = (
            soup.find("main")
            or soup.find(id="content")
            or soup
        )

        notices = []
        seen_urls = set()

        for link in container.find_all("a", href=True):

            title = " ".join(
                link.get_text(" ", strip=True).split()
            )

            url = urljoin(NOTICE_URL, link["href"])
            domain = urlparse(url).netloc.lower()

            # Ignore social media and unrelated websites
            if domain not in ALLOWED_DOMAINS:
                continue

            # Ignore very short link titles
            if len(title) < 15:
                continue

            # Avoid duplicate notices
            if url in seen_urls:
                continue

            seen_urls.add(url)

            notices.append({
                "title": title,
                "url": url
            })

        return notices

    except requests.RequestException as error:
        print("Error fetching notices:", error)
        return []


if __name__ == "__main__":

    notices = fetch_notices()

    print(f"\nFound {len(notices)} notices:\n")

    for index, notice in enumerate(notices, start=1):
        print(f"{index}. {notice['title']}")
        print(f"   {notice['url']}\n")
