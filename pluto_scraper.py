import os
import re
import json
import time
import argparse
from io import BytesIO
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from PIL import Image

BASE_API_URL = "https://shinigami-apis.vercel.app"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "cdn", "pluto")
COMICS_DIR = os.path.join(OUTPUT_DIR, "comics")
DATA_DIR = os.path.join(os.path.dirname(__file__), "cdn", "data")

os.makedirs(COMICS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def sanitize_slug(slug: str, fallback_title: str) -> str:
    if slug:
        clean = re.sub(r'[^a-zA-Z0-9\-_]', '', slug).strip('-').lower()
        if clean:
            return clean
    clean = re.sub(r'[^a-zA-Z0-9]+', '-', fallback_title).strip('-').lower()
    return clean or "unknown-manga"

def download_and_convert_webp(img_url: str, output_filepath: str) -> bool:
    """Downloads image and converts it to optimized WebP format."""
    if not img_url:
        return False
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
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
            return False
    except Exception as e:
        return False

def fetch_and_save_pluto_genres():
    """1. Fetch genres from https://shinigami-apis.vercel.app/genres?page=1&page_size=100"""
    print("-> Fetching PlutoScans genres list...", flush=True)
    genres = []
    page = 1
    has_next = True

    while has_next:
        url = f"{BASE_API_URL}/genres?page={page}&page_size=100"
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            if res.status_code == 200:
                body = res.json()
                data_obj = body.get("data", {})
                if isinstance(data_obj, dict):
                    g_list = data_obj.get("data", [])
                    genres.extend(g_list)
                    pagination = body.get("pagination", {})
                    has_next = pagination.get("has_next", False)
                    page += 1
                else:
                    has_next = False
            else:
                has_next = False
        except Exception as e:
            print(f"[X] Error fetching genres page {page}: {e}", flush=True)
            has_next = False

    genres_path = os.path.join(DATA_DIR, "pluto_genres.json")
    with open(genres_path, "w", encoding="utf-8") as f:
        json.dump({"total_genres": len(genres), "genres": genres}, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved {len(genres)} PlutoScans genres to {genres_path}", flush=True)
    return genres

def scrape_manga_by_genres(genres, max_pages_per_genre=0):
    """2. Fetch manga by genre: https://shinigami-apis.vercel.app/manga?page=1&page_size=100&genre={genre_slug}"""
    all_manga_map = {}

    for idx, genre_obj in enumerate(genres, 1):
        genre_name = genre_obj.get("name")
        genre_slug = genre_obj.get("slug")
        if not genre_slug:
            continue

        print(f"\n[{idx}/{len(genres)}] Scraping PlutoScans Genre: {genre_name} ({genre_slug})...", flush=True)

        page = 1
        has_next_page = True

        while has_next_page:
            if max_pages_per_genre > 0 and page > max_pages_per_genre:
                print(f"  Reached max pages ({max_pages_per_genre}) for genre {genre_name}.", flush=True)
                break

            url = f"{BASE_API_URL}/manga?page={page}&page_size=100&genre={genre_slug}"
            print(f"  Fetching Page {page}: {url}", flush=True)

            try:
                res = requests.get(url, headers=HEADERS, timeout=15)
                if res.status_code == 200:
                    body = res.json()
                    data_obj = body.get("data", {})
                    if isinstance(data_obj, dict):
                        manga_list = data_obj.get("data", [])
                        pagination = body.get("pagination", {})
                        has_next_page = pagination.get("has_next", False)

                        for item in manga_list:
                            m_id = item.get("manga_id")
                            title = item.get("title")
                            cover_url = item.get("cover_image_url") or item.get("cover_portrait_url")
                            if m_id and title:
                                s_slug = sanitize_slug(m_id, title)
                                if s_slug not in all_manga_map:
                                    taxonomy = item.get("taxonomy", {})
                                    fmt_list = [f.get("name") for f in taxonomy.get("Format", []) if f.get("name")]
                                    format_type = fmt_list[0] if fmt_list else "Manhwa"

                                    all_manga_map[s_slug] = {
                                        "manga_id": m_id,
                                        "slug": s_slug,
                                        "title": title,
                                        "alternative_title": item.get("alternative_title"),
                                        "format": format_type,
                                        "status": item.get("status"),
                                        "view_count": item.get("view_count", 0),
                                        "user_rate": item.get("user_rate", 0),
                                        "cover_image_url": cover_url,
                                        "latest_chapter_id": item.get("latest_chapter_id"),
                                        "latest_chapter_number": item.get("latest_chapter_number"),
                                        "genres": [genre_name]
                                    }
                                else:
                                    if genre_name not in all_manga_map[s_slug]["genres"]:
                                        all_manga_map[s_slug]["genres"].append(genre_name)

                        print(f"    Found {len(manga_list)} manga items on page {page}. (Has Next: {has_next_page})", flush=True)
                        if not manga_list:
                            has_next_page = False
                    else:
                        has_next_page = False
                else:
                    has_next_page = False
            except Exception as e:
                print(f"  [X] Error fetching manga page {page} for genre {genre_slug}: {e}", flush=True)
                has_next_page = False

            page += 1
            time.sleep(0.05)

    return all_manga_map

def fetch_chapter_details(chapter_id: str):
    """3. Fetch Chapter Images from https://shinigami-apis.vercel.app/chapter/{uuid_chapter}"""
    if not chapter_id:
        return None
    url = f"{BASE_API_URL}/chapter/{chapter_id}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            body = res.json()
            data_obj = body.get("data", {})
            base_url = data_obj.get("base_url", "https://assets.shngm.id")
            chapter_info = data_obj.get("chapter", {})
            path = chapter_info.get("path", "")
            files = chapter_info.get("data", [])
            chap_num = data_obj.get("chapter_number", 1)
            
            image_urls = [f"{base_url}{path}{fn}" for fn in files]
            return {
                "chapter_id": chapter_id,
                "chapter_number": chap_num,
                "images": image_urls
            }
    except Exception as e:
        print(f"  [X] Error fetching chapter {chapter_id}: {e}", flush=True)
    return None

def process_single_manga(item_tuple):
    idx, slug, info, github_user, github_repo, branch, no_download, fetch_chapters = item_tuple
    
    # -------------------------------------------------------------
    # FOLDER STRUCTURE: cdn/pluto/comics/{judul_comic}/
    # -------------------------------------------------------------
    manga_folder_rel = f"cdn/pluto/comics/{slug}"
    manga_folder_abs = os.path.join(COMICS_DIR, slug)
    os.makedirs(manga_folder_abs, exist_ok=True)

    # 1. Cover Image
    cover_filename = "cover.webp"
    cover_filepath = os.path.join(manga_folder_abs, cover_filename)
    cover_rel_path = f"{manga_folder_rel}/{cover_filename}"

    if not no_download and info.get("cover_image_url") and not os.path.exists(cover_filepath):
        download_and_convert_webp(info["cover_image_url"], cover_filepath)

    cover_custom_url = f"https://cdn.plutoscans.my.id/{cover_rel_path}"
    cover_jsdelivr_url = f"https://cdn.jsdelivr.net/gh/{github_user}/{github_repo}@{branch}/{cover_rel_path}"

    # 2. Chapters Hierarchy: {judul_comic}/chapter-{chapter_number}/{page_number}.webp
    chapter_data_list = []
    if fetch_chapters and info.get("latest_chapter_id"):
        chap_det = fetch_chapter_details(info["latest_chapter_id"])
        if chap_det:
            chap_num = chap_det["chapter_number"]
            chap_folder_name = f"chapter-{chap_num}"
            chap_folder_abs = os.path.join(manga_folder_abs, chap_folder_name)
            os.makedirs(chap_folder_abs, exist_ok=True)

            chap_pages = []
            for p_idx, orig_img_url in enumerate(chap_det["images"], 1):
                page_filename = f"{p_idx}.webp"
                page_filepath = os.path.join(chap_folder_abs, page_filename)
                page_rel_path = f"{manga_folder_rel}/{chap_folder_name}/{page_filename}"

                if not no_download and not os.path.exists(page_filepath):
                    download_and_convert_webp(orig_img_url, page_filepath)

                chap_pages.append({
                    "page": p_idx,
                    "file_name": page_filename,
                    "custom_domain_url": f"https://cdn.plutoscans.my.id/{page_rel_path}",
                    "jsdelivr_url": f"https://cdn.jsdelivr.net/gh/{github_user}/{github_repo}@{branch}/{page_rel_path}"
                })

            chapter_data_list.append({
                "chapter_id": chap_det["chapter_id"],
                "chapter_number": chap_num,
                "folder_name": chap_folder_name,
                "total_pages": len(chap_pages),
                "pages": chap_pages
            })

    catalog_entry = {
        "manga_id": info.get("manga_id"),
        "slug": slug,
        "title": info.get("title", slug),
        "alternative_title": info.get("alternative_title"),
        "format": info.get("format", "Manhwa"),
        "genres": info.get("genres", []),
        "view_count": info.get("view_count", 0),
        "user_rate": info.get("user_rate", 0),
        "latest_chapter_id": info.get("latest_chapter_id"),
        "latest_chapter_number": info.get("latest_chapter_number"),
        "cover": {
            "file_name": cover_filename,
            "custom_domain_url": cover_custom_url,
            "jsdelivr_url": cover_jsdelivr_url,
            "original_url": info.get("cover_image_url")
        },
        "chapters": chapter_data_list,
        "updated_at": datetime.now().isoformat()
    }

    return catalog_entry

def main():
    parser = argparse.ArgumentParser(description="PlutoScans Manga Scraper & Folder Hierarchy CDN Builder")
    parser.add_argument("--max-pages", type=int, default=0, help="Max pages per genre (0 = ALL pages until finished)")
    parser.add_argument("--no-download", action="store_true", help="Do not download images locally")
    parser.add_argument("--fetch-chapters", action="store_true", default=True, help="Fetch chapter images into folder structure")
    parser.add_argument("--github-user", type=str, default="AnimkuCDN", help="GitHub username/organization")
    parser.add_argument("--github-repo", type=str, default="PlutoScansCDN", help="GitHub repository name")
    parser.add_argument("--branch", type=str, default="main", help="Target branch")
    parser.add_argument("--threads", type=int, default=10, help="Number of parallel download threads")
    args = parser.parse_args()

    print("==================================================", flush=True)
    print("  PLUTOSCANS FOLDER HIERARCHY MANGA & CHAPTER CDN ", flush=True)
    print("==================================================", flush=True)

    genres = fetch_and_save_pluto_genres()
    print(f"Loaded {len(genres)} PlutoScans genres.", flush=True)

    manga_map = scrape_manga_by_genres(genres, max_pages_per_genre=args.max_pages)
    print(f"\nTotal unique manga found across all genres: {len(manga_map)}", flush=True)

    catalog_list = []
    print(f"\n-> Building Comic Folders & Downloading Chapter WebP Images ({args.threads} workers)...", flush=True)

    items_to_process = [
        (idx, slug, info, args.github_user, args.github_repo, args.branch, args.no_download, args.fetch_chapters)
        for idx, (slug, info) in enumerate(manga_map.items(), 1)
    ]

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {executor.submit(process_single_manga, item): item for item in items_to_process}
        for future in as_completed(futures):
            try:
                entry = future.result()
                catalog_list.append(entry)
            except Exception as e:
                print(f"[X] Error processing comic folder: {e}", flush=True)

    catalog_path = os.path.join(DATA_DIR, "pluto_catalog.json")
    meta_output = {
        "generated_at": datetime.now().isoformat(),
        "domain": "cdn.plutoscans.my.id",
        "total_items": len(catalog_list),
        "github_user": args.github_user,
        "github_repo": args.github_repo,
        "branch": args.branch,
        "manga": catalog_list
    }

    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(meta_output, f, indent=2, ensure_ascii=False)

    print("\n==================================================", flush=True)
    print(" PLUTOSCANS FOLDER STRUCTURE COMPLETED SUCCESSFULLY!", flush=True)
    print("==================================================", flush=True)
    print(f"Total manga folders cataloged : {len(catalog_list)}", flush=True)
    print(f"Catalog metadata saved to     : {catalog_path}", flush=True)

if __name__ == "__main__":
    main()
