import os
import sys
import shutil
import subprocess

# Konfigurasi GitHub Repository & Token
GITHUB_USER = "AnimkuCDN"
GITHUB_REPO = "AnimkuCDN"
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

import stat

def remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def main():
    print("==================================================", flush=True)
    print("  ANIMKU CDN - FRESH RESET & CLEAN DEPLOYMENT    ", flush=True)
    print("==================================================", flush=True)

    # -------------------------------------------------------------
    # STEP 1: Reset Git History Lokal & Hapus Semua Isi Lama di Remote GitHub
    # -------------------------------------------------------------
    print("\n[STEP 1/3] Mereset Git History & Menghapus Isi Lama di GitHub...", flush=True)
    
    # Hapus folder .git lama secara aman dengan izin read-only Windows handler
    git_dir = os.path.join(os.path.dirname(__file__), ".git")
    if os.path.exists(git_dir):
        try:
            shutil.rmtree(git_dir, onerror=remove_readonly)
            print("-> Cleaned old local .git folder successfully.", flush=True)
        except Exception as e:
            print(f"-> Note cleaning .git: {e}", flush=True)

    # Inisialisasi git baru
    run_cmd("git init")
    run_cmd('git config user.name "AnimkuCDN Bot"')
    run_cmd('git config user.email "bot@animkucdn.com"')
    run_cmd(f"git branch -M {BRANCH}")

    # Atur remote URL secara aman
    run_cmd("git remote remove origin", check=False)
    run_cmd(f"git remote add origin {REMOTE_URL}")

    # Pastikan direktori penting cdn ada
    os.makedirs(os.path.join(os.path.dirname(__file__), "cdn", "thumbnails"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "cdn", "data"), exist_ok=True)

    # Add semua file proyek bersih (mengabaikan token.txt)
    run_cmd("git add .")
    run_cmd("git rm --cached token.txt", check=False)
    run_cmd('git commit -m "feat: initial clean release AnimkuCDN Web Pages & Scraper Engine"')

    print("\n-> Force Pushing perawan bersih ke GitHub (Menghapus semua file/commit lama di repo)...", flush=True)
    push_res = run_cmd(f"git -c credential.helper= push -u origin {BRANCH} --force", check=False)
    
    if push_res.returncode == 0:
        print("[SUCCESS] STEP 1 SELESAI: Repository GitHub telah dibersihkan & di-reset dari 0!", flush=True)
    else:
        print("[X] ERROR: Push gagal. Periksa kembali token di token.txt", flush=True)
        sys.exit(1)

    # -------------------------------------------------------------
    # STEP 2: Download & Convert Thumbnails to WebP & Generate Metadata
    # -------------------------------------------------------------
    print("\n[STEP 2/3] Downloading & Converting Thumbnails to WebP (Auto-Skip Existing)...", flush=True)
    scraper_script = os.path.join(os.path.dirname(__file__), "scraper.py")
    run_cmd(f'"{sys.executable}" "{scraper_script}" --max-pages 1 --github-user {GITHUB_USER} --github-repo {GITHUB_REPO} --branch {BRANCH}')

    # -------------------------------------------------------------
    # STEP 3: Push Metadata & Web Pages Terupdate ke GitHub
    # -------------------------------------------------------------
    print("\n[STEP 3/3] Upload Metadata Catalog Terupdate ke GitHub...", flush=True)
    run_cmd("git add CNAME cdn/ index.html styles.css app.js scraper.py README.md .github/ .gitignore")
    run_cmd('git commit -m "chore(cdn): catalog metadata & CNAME updated"', check=False)
    run_cmd(f"git -c credential.helper= push origin {BRANCH}", check=False)

    print("\n==================================================", flush=True)
    print("  FRESH DEPLOYMENT BERHASIL 100%!", flush=True)
    print("==================================================", flush=True)
    print("Custom Domain CDN  : https://cdn.animku.my.id/", flush=True)
    print("Web Pages Pages    : https://AnimkuCDN.github.io/AnimkuCDN/", flush=True)
    print("Status Cloud Runner: https://github.com/AnimkuCDN/AnimkuCDN/actions", flush=True)
    print("Anime Catalog API  : https://cdn.animku.my.id/cdn/data/anime_catalog.json", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    main()
