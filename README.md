# ⚡ AnimkuCDN & PlutoScans CDN Engine

Sistem scraping & CDN otomatis untuk **Anime (Animku API)** dan **Manga/Komik (PlutoScans / Shinigami API)**, mengompresi gambar ke format **WebP** super cepat & hemat bandwidth.

---

## 🚀 1. Deployment AnimkuCDN (Anime)

Repository: `https://github.com/AnimkuCDN/AnimkuCDN.git`

```bash
python deploy.py
```

- **Web Dashboard**: `https://cdn.animku.my.id/`
- **Catalog API**: `https://cdn.animku.my.id/cdn/data/anime_catalog.json`

---

## 📖 2. Deployment PlutoScans CDN (Manga / Komik)

Repository: `https://github.com/AnimkuCDN/PlutoScansCDN.git`

API Source:
- **List Genres**: `https://shinigami-apis.vercel.app/genres?page=1&page_size=100`
- **Data By Genre**: `https://shinigami-apis.vercel.app/manga?page=1&page_size=100&genre={genre_slug}`
- **Chapter Images**: `https://shinigami-apis.vercel.app/chapter/{uuid_chapter}`

Perintah Deploy:
```bash
python pluto_deploy.py
```

- **Web Dashboard**: `https://pluto.animku.my.id/`
- **Manga Catalog API**: `https://pluto.animku.my.id/cdn/data/pluto_catalog.json`
- **Genres List API**: `https://pluto.animku.my.id/cdn/data/pluto_genres.json`
