import os
import re
import json
import time
import argparse
from io import BytesIO
from datetime import datetime
import requests
from PIL import Image

BASE_API_URL = "https://animku-apis.vercel.app"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "cdn")
THUMB_DIR = os.path.join(OUTPUT_DIR, "thumbnails")
DATA_DIR = os.path.join(OUTPUT_DIR, "data")

os.makedirs(THUMB_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_image_url(url: str) -> str:
    """Removes resize parameters to fetch highest resolution thumbnail."""
    if not url:
        return ""
    clean_url = re.sub(r'\?resize=\d+.*$', '', url)
    return clean_url

def sanitize_slug(slug: str, fallback_title: str) -> str:
    if slug:
        clean = re.sub(r'[^a-zA-Z0-9\-_]', '', slug).strip('-').lower()
        if clean:
            return clean
    clean = re.sub(r'[^a-zA-Z0-9]+', '-', fallback_title).strip('-').lower()
    return clean or "unknown-anime"

def download_and_convert_webp(img_url: str, output_filepath: str) -> bool:
    """Downloads image and converts it to optimized WebP format."""
    try:
        res = requests.get(img_url, headers=HEADERS, timeout=15)
        if res.status_code == 200 and res.content:
            img = Image.open(BytesIO(res.content))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")
            
            img.save(output_filepath, "WEBP", quality=82, method=6)
            return True
        else:
            print(f"  [X] Failed HTTP {res.status_code} for {img_url}")
            return False
    except Exception as e:
        print(f"  [X] Exception downloading {img_url}: {e}")
        return False

def fetch_and_save_genres():
    """1. Fetch data list genre dari /api/listall dan simpan ke cdn/data/genres_list.json"""
    print("-> Fetching genres list from /api/listall...", flush=True)
    url = f"{BASE_API_URL}/api/listall"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            json_data = res.json()
            if json_data.get("status") and "data" in json_data:
                genres = json_data["data"].get("genres", [])
                genres_path = os.path.join(DATA_DIR, "genres_list.json")
                with open(genres_path, "w", encoding="utf-8") as f:
                    json.dump({"total_genres": len(genres), "genres": genres}, f, indent=2, ensure_ascii=False)
                print(f"[OK] Saved {len(genres)} genres to {genres_path}", flush=True)
                return genres
    except Exception as e:
        print(f"[X] Error fetching genres: {e}", flush=True)
    
    genres_path = os.path.join(DATA_DIR, "genres_list.json")
    if os.path.exists(genres_path):
        with open(genres_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("genres", [])
    return []

def scrape_anime_by_genres(genres, max_pages_per_genre=0):
    """2. Fetch halaman api data by genre: /api/filter?genre[]={genre_slug}&page={page_number} sampai selesai"""
    all_anime_map = {}

    for idx, genre_obj in enumerate(genres, 1):
        genre_name = genre_obj.get("name")
        genre_slug = genre_obj.get("value")
        if not genre_slug:
            continue

        print(f"\n[{idx}/{len(genres)}] Scraping Genre: {genre_name} ({genre_slug})...", flush=True)

        page = 1
        has_next_page = True

        while has_next_page:
            if max_pages_per_genre > 0 and page > max_pages_per_genre:
                print(f"  Reached max requested pages ({max_pages_per_genre}) for genre {genre_name}.", flush=True)
                break

            url = f"{BASE_API_URL}/api/filter?genre[]={genre_slug}&page={page}"
            print(f"  Fetching Page {page}: {url}", flush=True)

            success = False
            for attempt in range(1, 4):
                try:
                    res = requests.get(url, headers=HEADERS, timeout=15)
                    if res.status_code == 200:
                        json_data = res.json()
                        if json_data.get("status") and "data" in json_data:
                            data = json_data["data"]
                            anime_list = data.get("animeList") or data.get("anime") or []
                            pagination = data.get("pagination", {})
                            has_next_page = pagination.get("hasNextPage", False)

                            for item in anime_list:
                                title = item.get("title")
                                slug = item.get("slug")
                                img = item.get("image") or item.get("thumbnail")
                                if img and (slug or title):
                                    s_slug = sanitize_slug(slug, title)
                                    if s_slug not in all_anime_map:
                                        all_anime_map[s_slug] = {
                                            "slug": s_slug,
                                            "title": title,
                                            "status": item.get("status", "Unknown"),
                                            "type": item.get("type", "TV"),
                                            "link": item.get("link"),
                                            "original_image": clean_image_url(img),
                                            "genres": [genre_name]
                                        }
                                    else:
                                        if genre_name not in all_anime_map[s_slug]["genres"]:
                                            all_anime_map[s_slug]["genres"].append(genre_name)

                            print(f"    Found {len(anime_list)} anime items on page {page}. (Has Next Page: {has_next_page})", flush=True)
                            if not anime_list:
                                has_next_page = False
                            success = True
                            break
                        else:
                            print(f"  [!] Invalid response data on page {page}, stopping genre.", flush=True)
                            has_next_page = False
                            break
                    else:
                        print(f"  [!] HTTP {res.status_code} on attempt {attempt}, retrying...", flush=True)
                        time.sleep(1)
                except Exception as e:
                    print(f"  [!] Network attempt {attempt} error: {e}", flush=True)
                    time.sleep(1.5)

            if not success:
                print(f"  [X] Failed page {page} for genre {genre_slug} after 3 attempts. Moving to next page/genre.", flush=True)
                page += 1
                continue

            page += 1
            time.sleep(0.3)

    return all_anime_map

from concurrent.futures import ThreadPoolExecutor, as_completed

def process_single_image(item_tuple):
    idx, slug, info, github_user, github_repo, branch, no_download = item_tuple
    filename = f"{slug}.webp"
    filepath = os.path.join(THUMB_DIR, filename)
    rel_path = f"cdn/thumbnails/{filename}"

    gh_pages_url = f"https://{github_user}.github.io/{github_repo}/{rel_path}"
    jsdelivr_url = f"https://cdn.jsdelivr.net/gh/{github_user}/{github_repo}@{branch}/{rel_path}"
    statically_url = f"https://cdn.statically.io/gh/{github_user}/{github_repo}/{branch}/{rel_path}"

    downloaded = False
    skipped = False

    if not no_download:
        if not os.path.exists(filepath):
            success = download_and_convert_webp(info["original_image"], filepath)
            if success:
                downloaded = True
        else:
            skipped = True
    else:
        skipped = True

    file_size_kb = round(os.path.getsize(filepath) / 1024, 2) if os.path.exists(filepath) else 0

    catalog_entry = {
        "slug": slug,
        "title": info.get("title", slug),
        "type": info.get("type", "TV"),
        "status": info.get("status", "Unknown"),
        "genres": info.get("genres", []),
        "original_image": info.get("original_image"),
        "file_name": filename,
        "file_size_kb": file_size_kb,
        "local_path": rel_path,
        "cdn_urls": {
            "custom_domain": f"https://cdn.animku.my.id/{rel_path}",
            "github_pages": gh_pages_url,
            "jsdelivr": jsdelivr_url,
            "statically": statically_url
        },
        "updated_at": datetime.now().isoformat()
    }

    return catalog_entry, downloaded, skipped

def main():
    parser = argparse.ArgumentParser(description="Genre-based Anime Thumbnail Scraper & GitHub CDN Builder")
    parser.add_argument("--max-pages", type=int, default=0, help="Max pages per genre (0 = ALL pages until finished)")
    parser.add_argument("--no-download", action="store_true", help="Do not download images locally; generate metadata only")
    parser.add_argument("--github-user", type=str, default="AnimkuCDN", help="GitHub username/organization")
    parser.add_argument("--github-repo", type=str, default="AnimkuCDN", help="GitHub repository name")
    parser.add_argument("--branch", type=str, default="main", help="Target branch for CDN")
    parser.add_argument("--threads", type=int, default=10, help="Number of parallel download threads")
    args = parser.parse_args()

    print("==================================================", flush=True)
    print(" ANIME THUMBNAIL SCRAPER (ALL GENRES & ALL PAGES) ", flush=True)
    print("==================================================", flush=True)

    genres = fetch_and_save_genres()
    print(f"Loaded {len(genres)} genres.", flush=True)

    anime_items_map = scrape_anime_by_genres(genres, max_pages_per_genre=args.max_pages)
    print(f"\nTotal unique anime found across all genres: {len(anime_items_map)}", flush=True)

    catalog_list = []
    success_count = 0
    skip_count = 0

    if args.no_download:
        print("\n-> [--no-download Mode]: Skipping local image download. Generating metadata catalog only...", flush=True)
    else:
        print(f"\n-> Processing & Downloading Thumbnails (Fast Multi-threaded WebP Conversion with {args.threads} workers)...", flush=True)

    items_to_process = [
        (idx, slug, info, args.github_user, args.github_repo, args.branch, args.no_download)
        for idx, (slug, info) in enumerate(anime_items_map.items(), 1)
    ]

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {executor.submit(process_single_image, item): item for item in items_to_process}
        for future in as_completed(futures):
            try:
                entry, downloaded, skipped = future.result()
                catalog_list.append(entry)
                if downloaded:
                    success_count += 1
                if skipped:
                    skip_count += 1
            except Exception as e:
                print(f"[X] Error processing image: {e}", flush=True)

    catalog_path = os.path.join(DATA_DIR, "anime_catalog.json")
    meta_output = {
        "generated_at": datetime.now().isoformat(),
        "total_items": len(catalog_list),
        "github_user": args.github_user,
        "github_repo": args.github_repo,
        "branch": args.branch,
        "anime": catalog_list
    }

    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(meta_output, f, indent=2, ensure_ascii=False)

    print("\n==================================================", flush=True)
    print(" SCRAPING & CATALOGING COMPLETED SUCCESSFULLY!", flush=True)
    print("==================================================", flush=True)
    print(f"Total anime cataloged : {len(catalog_list)}", flush=True)
    print(f"New WebP downloaded   : {success_count}", flush=True)
    print(f"Existing files kept   : {skip_count}", flush=True)
    print(f"Catalog saved to      : {catalog_path}", flush=True)

if __name__ == "__main__":
    main()
