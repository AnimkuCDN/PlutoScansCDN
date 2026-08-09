let animeCatalog = [];

document.addEventListener('DOMContentLoaded', () => {
  loadCatalogData();
  setupEventListeners();
  setupCopyDelegation();
  updateEndpointPreview();
});

async function loadCatalogData() {
  const gallery = document.getElementById('galleryGrid');
  gallery.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 60px; color: var(--text-muted);"><i class="fa-solid fa-spinner fa-spin fa-2x"></i><p style="margin-top: 12px;">Memuat katalog CDN...</p></div>';

  try {
    const res = await fetch('cdn/data/anime_catalog.json');
    if (!res.ok) throw new Error('File metadata catalog belum dibuat atau gagal dimuat');
    const data = await res.json();
    animeCatalog = data.anime || [];
    
    document.getElementById('badgeTotalCount').innerHTML = `<i class="fa-solid fa-images"></i> ${data.total_items || animeCatalog.length} Thumbnails`;
    
    if (data.generated_at) {
      const dateStr = new Date(data.generated_at).toLocaleString('id-ID');
      document.getElementById('lastUpdatedText').innerHTML = `<i class="fa-solid fa-clock"></i> Terakhir diperbarui: ${dateStr}`;
    }

    renderGallery(animeCatalog);
  } catch (err) {
    console.warn('Fallback to demo/empty state:', err.message);
    gallery.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 60px; background: var(--bg-card); border-radius: var(--radius-md); border: 1px solid var(--border);">
        <i class="fa-solid fa-box-open fa-3x" style="color: var(--primary); margin-bottom: 16px;"></i>
        <h3 style="margin-bottom: 8px;">Katalog CDN Masih Kosong</h3>
        <p style="color: var(--text-muted); max-width: 500px; margin: 0 auto 20px;">
          Jalankan script <code>python deploy.py</code> untuk mulai mengumpulkan data katalog anime.
        </p>
      </div>
    `;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderGallery(items) {
  const gallery = document.getElementById('galleryGrid');
  const countText = document.getElementById('displayCountText');
  countText.innerText = `Menampilkan ${items.length} dari ${animeCatalog.length} anime`;

  if (items.length === 0) {
    gallery.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">Tidak ada anime yang cocok dengan pencarian Anda.</div>';
    return;
  }

  gallery.innerHTML = items.map(anime => {
    const customDomainUrl = anime.cdn_urls?.custom_domain || `https://cdn.animku.my.id/cdn/thumbnails/${anime.file_name}`;
    const jsdelivrUrl = anime.cdn_urls?.jsdelivr || `https://cdn.jsdelivr.net/gh/AnimkuCDN/AnimkuCDN@main/cdn/thumbnails/${anime.file_name}`;
    const localWebpUrl = `cdn/thumbnails/${anime.file_name}`;
    const safeTitle = escapeHtml(anime.title);
    const htmlImgTag = `<img src="${customDomainUrl}" alt="${safeTitle}">`;

    return `
      <div class="card">
        <div class="card-image-wrap">
          <img src="${localWebpUrl}" alt="${safeTitle}" loading="lazy">
          <span class="card-tag">${anime.type || 'TV'}</span>
        </div>
        <div class="card-body">
          <div class="card-title" title="${safeTitle}">${safeTitle}</div>
          <div class="card-meta">
            <span><i class="fa-solid fa-file"></i> ${anime.file_size_kb || 0} KB</span>
            <span><i class="fa-solid fa-image"></i> WebP</span>
          </div>
          <div class="card-actions">
            <button class="btn-copy btn-action-copy" data-copy="${escapeHtml(customDomainUrl)}" data-label="Custom Domain CDN">
              <i class="fa-solid fa-globe"></i> Copy Domain CDN
            </button>
            <button class="btn-copy jsdelivr btn-action-copy" data-copy="${escapeHtml(jsdelivrUrl)}" data-label="jsDelivr CDN URL">
              <i class="fa-solid fa-bolt"></i> Copy jsDelivr CDN
            </button>
            <button class="btn-copy btn-action-copy" style="background: rgba(255,255,255,0.05); color: var(--text-muted); border-color: var(--border);" data-copy="${escapeHtml(htmlImgTag)}" data-label="HTML Image Tag">
              <i class="fa-solid fa-code"></i> Copy HTML Tag
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function setupEventListeners() {
  const searchInput = document.getElementById('searchInput');
  const typeFilter = document.getElementById('typeFilter');

  const filterHandler = () => {
    const query = searchInput.value.toLowerCase().trim();
    const selectedType = typeFilter.value;

    const filtered = animeCatalog.filter(item => {
      const matchQuery = !query || item.title.toLowerCase().includes(query) || item.slug.toLowerCase().includes(query);
      const matchType = !selectedType || (item.type && item.type.toUpperCase() === selectedType.toUpperCase());
      return matchQuery && matchType;
    });

    renderGallery(filtered);
  };

  searchInput.addEventListener('input', filterHandler);
  typeFilter.addEventListener('change', filterHandler);
}

function setupCopyDelegation() {
  document.addEventListener('click', (e) => {
    const copyBtn = e.target.closest('.btn-action-copy');
    if (copyBtn) {
      const textToCopy = copyBtn.getAttribute('data-copy');
      const label = copyBtn.getAttribute('data-label') || 'Link';
      if (textToCopy) {
        copyToClipboard(textToCopy, label);
      }
    }
  });
}

function reloadCatalog() {
  loadCatalogData();
}

function updateEndpointPreview() {
  const currentOrigin = window.location.href.split('?')[0].replace(/\/$/, '');
  const jsonEl = document.getElementById('jsonEndpointUrl');
  if (jsonEl) {
    jsonEl.innerText = `${currentOrigin}/cdn/data/anime_catalog.json`;
  }
}

function copyToClipboard(text, label = 'Link') {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => {
      showToast(`${label} disalin ke clipboard!`);
    }).catch(err => {
      fallbackCopyTextToClipboard(text, label);
    });
  } else {
    fallbackCopyTextToClipboard(text, label);
  }
}

function fallbackCopyTextToClipboard(text, label) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.style.top = "0";
  textArea.style.left = "0";
  textArea.style.position = "fixed";
  textArea.style.opacity = "0";
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();

  try {
    const successful = document.execCommand('copy');
    if (successful) {
      showToast(`${label} disalin ke clipboard!`);
    } else {
      showToast(`Gagal menyalin ${label}`);
    }
  } catch (err) {
    console.error('Fallback copy failed:', err);
    showToast(`Gagal menyalin ${label}`);
  }

  document.body.removeChild(textArea);
}

function showToast(message) {
  const toast = document.getElementById('toast');
  const toastMsg = document.getElementById('toastMsg');
  if (toast && toastMsg) {
    toastMsg.innerText = message;
    toast.classList.add('show');

    setTimeout(() => {
      toast.classList.remove('show');
    }, 2500);
  }
}
