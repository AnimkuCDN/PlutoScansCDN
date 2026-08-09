import os
import sys
import stat
import shutil
import subprocess

# Konfigurasi GitHub Repository & Token untuk PlutoScans
GITHUB_USER = "AnimkuCDN"
GITHUB_REPO = "PlutoScansCDN"
BRANCH = "main"

def get_github_token():
    token = os.environ.get("GITHUB_TOKEN")
    if token and token.strip():
        return token.strip()
    token_file = os.path.join(os.path.dirname(__file__), "token.txt")
    if os.path.exists(token_file):
        with open(token_file, "r", encoding="utf-8") as f:
            t = f.read().strip()
            if t:
                return t
    print("[X] ERROR: File token.txt tidak ditemukan atau kosong!", flush=True)
    sys.exit(1)

GITHUB_TOKEN = get_github_token()
REMOTE_URL = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{GITHUB_REPO}.git"

def run_cmd(cmd, check=True):
    print(f"-> Executing: {cmd}", flush=True)
    res = subprocess.run(cmd, shell=True, text=True, capture_output=False)
    if res.returncode != 0 and check:
        print(f"[X] Error running command (code {res.returncode}): {cmd}", flush=True)
        sys.exit(res.returncode)
    return res

def remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def main():
    print("==================================================", flush=True)
    print("  PLUTOSCANS CDN - FRESH RESET & DEPLOYMENT ENGINE", flush=True)
    print("==================================================", flush=True)

    # 1. Tulis CNAME & set index.html khusus PlutoScans CDN
    cname_path = os.path.join(os.path.dirname(__file__), "CNAME")
    with open(cname_path, "w", encoding="utf-8") as f:
        f.write("cdn.plutoscans.my.id\n")

    # Copy pluto.html ke index.html agar menjadi halaman utama repository PlutoScansCDN
    pluto_html_path = os.path.join(os.path.dirname(__file__), "pluto.html")
    index_html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(pluto_html_path):
        shutil.copyfile(pluto_html_path, index_html_path)
        print("-> Set index.html to PlutoScans Manga Explorer UI.", flush=True)

    # -------------------------------------------------------------
    # STEP 1: Reset Git History & Menghubungkan ke PlutoScansCDN.git
    # -------------------------------------------------------------
    print("\n[STEP 1/3] Mereset Git History & Menghubungkan ke Repo PlutoScansCDN...", flush=True)
    
    git_dir = os.path.join(os.path.dirname(__file__), ".git")
    if os.path.exists(git_dir):
        try:
            shutil.rmtree(git_dir, onerror=remove_readonly)
            print("-> Cleaned local .git folder.", flush=True)
        except Exception as e:
            print(f"-> Note cleaning .git: {e}", flush=True)

    run_cmd("git init")
    run_cmd('git config user.name "AnimkuCDN Bot"')
    run_cmd('git config user.email "bot@animkucdn.com"')
    run_cmd(f"git branch -M {BRANCH}")

    run_cmd("git remote remove origin", check=False)
    run_cmd(f"git remote add origin {REMOTE_URL}")

    os.makedirs(os.path.join(os.path.dirname(__file__), "cdn", "pluto", "comics"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "cdn", "data"), exist_ok=True)

    run_cmd("git add .")
    run_cmd("git rm --cached token.txt", check=False)
    run_cmd('git commit -m "feat: initial release PlutoScans CDN Engine & Web Pages"')

    print("\n-> Force Pushing perawan bersih ke GitHub Repository PlutoScansCDN...", flush=True)
    push_res = run_cmd(f"git -c credential.helper= push -u origin {BRANCH} --force", check=False)
    
    if push_res.returncode == 0:
        print("[SUCCESS] STEP 1 SELESAI: Repository PlutoScansCDN telah di-reset!", flush=True)
    else:
        print("[X] ERROR: Push gagal. Periksa kembali token di token.txt", flush=True)
        sys.exit(1)

    # -------------------------------------------------------------
    # STEP 2: PlutoScans Scraping & Folder Hierarchy Generation
    # -------------------------------------------------------------
    print("\n[STEP 2/3] Menjalankan PlutoScans Manga & Chapter Scraper...", flush=True)
    scraper_script = os.path.join(os.path.dirname(__file__), "pluto_scraper.py")
    run_cmd(f'"{sys.executable}" "{scraper_script}" --max-pages 1 --fetch-chapters --github-user {GITHUB_USER} --github-repo {GITHUB_REPO} --branch {BRANCH}')

    # -------------------------------------------------------------
    # STEP 3: Push Catalog & Folder Assets ke PlutoScansCDN
    # -------------------------------------------------------------
    print("\n[STEP 3/3] Upload Metadata Catalog & Folder Komik ke PlutoScansCDN...", flush=True)
    run_cmd("git add CNAME cdn/ index.html pluto.html styles.css app.js pluto_app.js pluto_scraper.py README.md .github/ .gitignore")
    run_cmd('git commit -m "chore(cdn): update PlutoScans catalog metadata & comic/chapter folder structure"', check=False)
    run_cmd(f"git -c credential.helper= push origin {BRANCH}", check=False)

    print("\n==================================================", flush=True)
    print(" 🎉 PLUTOSCANS CDN DEPLOYMENT BERHASIL 100%!", flush=True)
    print("==================================================", flush=True)
    print("🌐 Custom Domain CDN  : https://cdn.plutoscans.my.id/", flush=True)
    print("🌐 Web Pages Pages    : https://AnimkuCDN.github.io/PlutoScansCDN/", flush=True)
    print("⚙️ Status Cloud Runner: https://github.com/AnimkuCDN/PlutoScansCDN/actions", flush=True)
    print("📄 Manga Catalog API  : https://cdn.plutoscans.my.id/cdn/data/pluto_catalog.json", flush=True)
    print("📄 Genres List API    : https://cdn.plutoscans.my.id/cdn/data/pluto_genres.json", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    main()
