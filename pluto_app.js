let plutoCatalog = [];

document.addEventListener('DOMContentLoaded', () => {
  loadPlutoCatalog();
  setupEventListeners();
  setupCopyDelegation();
  updateEndpointPreview();
});

async function loadPlutoCatalog() {
  const gallery = document.getElementById('galleryGrid');
  gallery.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 60px; color: var(--text-muted);"><i class="fa-solid fa-spinner fa-spin fa-2x"></i><p style="margin-top: 12px;">Memuat katalog PlutoScans CDN...</p></div>';

  try {
    const res = await fetch('cdn/data/pluto_catalog.json');
    if (!res.ok) throw new Error('File metadata catalog PlutoScans belum dibuat');
    const data = await res.json();
    plutoCatalog = data.manga || [];
    
    document.getElementById('badgeTotalCount').innerHTML = `<i class="fa-solid fa-book-open"></i> ${data.total_items || plutoCatalog.length} Komik`;
    
    if (data.generated_at) {
      const dateStr = new Date(data.generated_at).toLocaleString('id-ID');
      document.getElementById('lastUpdatedText').innerHTML = `<i class="fa-solid fa-clock"></i> Terakhir diperbarui: ${dateStr}`;
    }

    renderGallery(plutoCatalog);
  } catch (err) {
    console.warn('Fallback PlutoScans empty state:', err.message);
    gallery.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 60px; background: var(--bg-card); border-radius: var(--radius-md); border: 1px solid var(--border);">
        <i class="fa-solid fa-book-open fa-3x" style="color: var(--primary); margin-bottom: 16px;"></i>
        <h3 style="margin-bottom: 8px;">Katalog PlutoScans Masih Kosong</h3>
        <p style="color: var(--text-muted); max-width: 500px; margin: 0 auto 20px;">
          Jalankan script <code>python pluto_deploy.py</code> untuk mengumpulkan katalog komik PlutoScans.
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
  countText.innerText = `Menampilkan ${items.length} dari ${plutoCatalog.length} komik`;

  if (items.length === 0) {
    gallery.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">Tidak ada komik yang cocok dengan pencarian Anda.</div>';
    return;
  }

  gallery.innerHTML = items.map(manga => {
    const customCoverUrl = manga.cover?.custom_domain_url || `https://cdn.plutoscans.my.id/cdn/pluto/comics/${manga.slug}/cover.webp`;
    const jsdelivrCoverUrl = manga.cover?.jsdelivr_url || `https://cdn.jsdelivr.net/gh/AnimkuCDN/PlutoScansCDN@main/cdn/pluto/comics/${manga.slug}/cover.webp`;
    const localCoverUrl = `cdn/pluto/comics/${manga.slug}/cover.webp`;
    const safeTitle = escapeHtml(manga.title);
    const formatTag = manga.format || 'Manhwa';

    const latestChap = manga.chapters && manga.chapters.length > 0 ? manga.chapters[0] : null;
    const samplePageUrl = latestChap && latestChap.pages && latestChap.pages.length > 0
      ? latestChap.pages[0].custom_domain_url
      : `https://cdn.plutoscans.my.id/cdn/pluto/comics/${manga.slug}/chapter-${manga.latest_chapter_number || 1}/1.webp`;

    return `
      <div class="card">
        <div class="card-image-wrap">
          <img src="${localCoverUrl}" alt="${safeTitle}" loading="lazy">
          <span class="card-tag">${formatTag}</span>
        </div>
        <div class="card-body">
          <div class="card-title" title="${safeTitle}">${safeTitle}</div>
          <div class="card-meta">
            <span><i class="fa-solid fa-folder-tree"></i> Ch. ${manga.latest_chapter_number || '?'}</span>
            <span><i class="fa-solid fa-eye"></i> ${(manga.view_count || 0).toLocaleString()}</span>
          </div>
          <div class="card-actions">
            <button class="btn-copy btn-action-copy" data-copy="${escapeHtml(customCoverUrl)}" data-label="Cover Domain CDN">
              <i class="fa-solid fa-image"></i> Copy Cover CDN
            </button>
            <button class="btn-copy jsdelivr btn-action-copy" data-copy="${escapeHtml(samplePageUrl)}" data-label="Sample Chapter Page 1 CDN">
              <i class="fa-solid fa-file-image"></i> Copy Chap 1 Page 1
            </button>
            <button class="btn-copy btn-action-copy" style="background: rgba(255,255,255,0.05); color: var(--text-muted); border-color: var(--border);" data-copy="${escapeHtml(jsdelivrCoverUrl)}" data-label="jsDelivr Cover CDN">
              <i class="fa-solid fa-bolt"></i> Copy jsDelivr Cover
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
    const selectedFormat = typeFilter.value;

    const filtered = plutoCatalog.filter(item => {
      const matchQuery = !query || item.title.toLowerCase().includes(query) || (item.slug && item.slug.toLowerCase().includes(query));
      const matchFormat = !selectedFormat || (item.format && item.format.toUpperCase() === selectedFormat.toUpperCase());
      return matchQuery && matchFormat;
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
  loadPlutoCatalog();
}

function updateEndpointPreview() {
  const currentOrigin = window.location.href.split('?')[0].replace(/\/$/, '');
  const jsonEl = document.getElementById('jsonEndpointUrl');
  if (jsonEl) {
    jsonEl.innerText = `${currentOrigin}/cdn/data/pluto_catalog.json`;
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
