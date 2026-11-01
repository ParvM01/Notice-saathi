import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

NOTICE_URL = "https://jeemain.nta.nic.in/public-notices/"

ALLOWED_DOMAINS = {
    "jeemain.nta.nic.in",
    "cdnbbsr.s3waas.gov.in"
}

MAX_FILE_SIZE = 50 * 1024 * 1024


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

            if domain not in ALLOWED_DOMAINS:
                continue

            if len(title) < 15:
                continue

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


def fetch_notice_hash(url):
    domain = urlparse(url).netloc.lower()

    if domain not in ALLOWED_DOMAINS:
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 NoticeSaathi/1.0"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=(10, 30),
            stream=True
        )

        response.raise_for_status()

        final_domain = urlparse(response.url).netloc.lower()

        if final_domain not in ALLOWED_DOMAINS:
            response.close()
            return None

        content_length = response.headers.get("Content-Length")

        if content_length:
            if int(content_length) > MAX_FILE_SIZE:
                response.close()
                return None

        file_hash = hashlib.sha256()
        total_size = 0

        for chunk in response.iter_content(chunk_size=65536):
            if not chunk:
                continue

            total_size += len(chunk)

            if total_size > MAX_FILE_SIZE:
                response.close()
                return None

            file_hash.update(chunk)

        response.close()

        if total_size == 0:
            return None

        return file_hash.hexdigest()

    except (requests.RequestException, ValueError) as error:
        print(f"Error checking notice file {url}: {error}")
        return None


if __name__ == "__main__":
    notices = fetch_notices()

    print(f"\nFound {len(notices)} notices:\n")

    for index, notice in enumerate(notices, start=1):
        print(f"{index}. {notice['title']}")
        print(f"   {notice['url']}\n")