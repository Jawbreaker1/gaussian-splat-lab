const els = {
  grid: document.querySelector('#galleryGrid'),
  empty: document.querySelector('#galleryEmpty'),
  status: document.querySelector('#galleryStatus'),
  refreshButton: document.querySelector('#refreshGalleryButton'),
  sceneTitle: document.querySelector('#sceneTitle'),
  sceneStatusPill: document.querySelector('#sceneStatusPill'),
  downloadSplatLink: document.querySelector('#downloadSplatLink'),
  downloadManifestLink: document.querySelector('#downloadManifestLink'),
  deleteSceneButton: document.querySelector('#deleteSceneButton'),
  canvas: document.querySelector('#gallerySparkCanvas'),
  overlay: document.querySelector('#gallerySparkOverlay'),
  sceneMeta: document.querySelector('#gallerySceneMeta'),
  walkButton: document.querySelector('#galleryWalkButton'),
  orbitButton: document.querySelector('#galleryOrbitButton'),
  sensitivityInput: document.querySelector('#gallerySensitivityInput'),
  sensitivityValue: document.querySelector('#gallerySensitivityValue'),
  panLeftButton: document.querySelector('#galleryPanLeftButton'),
  panRightButton: document.querySelector('#galleryPanRightButton'),
  panUpButton: document.querySelector('#galleryPanUpButton'),
  panDownButton: document.querySelector('#galleryPanDownButton'),
  resetButton: document.querySelector('#galleryResetButton'),
  zoomOutButton: document.querySelector('#galleryZoomOutButton'),
  zoomInButton: document.querySelector('#galleryZoomInButton'),
  cameraPrevButton: document.querySelector('#galleryCameraPrevButton'),
  cameraNextButton: document.querySelector('#galleryCameraNextButton'),
  reviewPanel: document.querySelector('#galleryReviewPanel'),
  reviewMetrics: document.querySelector('#galleryReviewMetrics'),
  reviewImage: document.querySelector('#galleryReviewImage'),
};

let items = [];
let selectedId = null;
let selectedDetail = null;
let controller = null;
let viewerModulePromise = null;
let navigationMode = 'walk';
let navigationSensitivity = 0.55;

function formatBytes(bytes) {
  const value = Number(bytes);
  if (!Number.isFinite(value) || value <= 0) return '-';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size >= 10 || index === 0 ? Math.round(size) : size.toFixed(1)} ${units[index]}`;
}

function formatCount(value) {
  const number = Number(value);
  return Number.isFinite(number) ? new Intl.NumberFormat().format(number) : '-';
}

function formatMetric(value, digits = 2) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : '-';
}

function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

function pillClass(status) {
  if (status === 'pass' || status === 'complete') return 'pill pass';
  if (status === 'warning') return 'pill warning';
  if (status === 'fail' || status === 'blocked') return 'pill fail';
  return 'pill neutral';
}

function setSceneStatus(text, type = 'neutral') {
  els.sceneStatusPill.textContent = text;
  els.sceneStatusPill.className = `pill ${type}`;
}

function metaRow(label, value) {
  const row = document.createElement('div');
  row.className = 'meta-row';
  const key = document.createElement('span');
  const val = document.createElement('span');
  key.textContent = label;
  val.textContent = value ?? '-';
  row.append(key, val);
  return row;
}

function reviewMetricRows(technical = {}) {
  const rows = [];
  if (technical.psnr != null) rows.push(['PSNR', formatMetric(technical.psnr, 2)]);
  if (technical.ssim != null) rows.push(['SSIM', formatMetric(technical.ssim, 3)]);
  if (technical.lpips != null) rows.push(['LPIPS', formatMetric(technical.lpips, 3)]);
  if (technical.meanMae != null) rows.push(['MAE', formatMetric(technical.meanMae, 2)]);
  if (technical.meanRmse != null) rows.push(['RMSE', formatMetric(technical.meanRmse, 2)]);
  if (technical.previewScore != null) rows.push(['Preview score', formatMetric(technical.previewScore, 2)]);
  if (technical.evalImageCount != null) rows.push(['Eval views', formatCount(technical.evalImageCount)]);
  return rows;
}

function compactQualityLabel(technical = {}) {
  if (technical.ssim != null) return `SSIM ${formatMetric(technical.ssim, 3)}`;
  if (technical.meanMae != null) return `MAE ${formatMetric(technical.meanMae, 1)}`;
  if (technical.previewScore != null) return `Score ${formatMetric(technical.previewScore, 1)}`;
  return '-';
}

function setDownload(link, url, fileName) {
  if (!url) {
    link.removeAttribute('href');
    link.removeAttribute('download');
    link.setAttribute('aria-disabled', 'true');
    return;
  }
  link.href = url;
  link.download = fileName || '';
  link.setAttribute('aria-disabled', 'false');
}

function renderReviewPanel(item, manifest = {}) {
  const preview = manifest.preview ?? item?.preview ?? {};
  const reviewUrl = preview.renderReviewUrl;
  const technical = item?.technical ?? {};
  els.reviewMetrics.replaceChildren();
  for (const [label, value] of reviewMetricRows(technical)) {
    els.reviewMetrics.append(metaRow(label, value));
  }
  if (!reviewUrl) {
    els.reviewPanel.hidden = true;
    els.reviewImage.removeAttribute('src');
    return;
  }
  els.reviewImage.src = reviewUrl;
  els.reviewPanel.hidden = false;
}

function renderSceneMeta(item, manifest = {}) {
  els.sceneMeta.replaceChildren();
  if (!item) {
    els.sceneMeta.append(metaRow('Scene', 'No scene selected'));
    renderReviewPanel(null);
    return;
  }
  const artifact = item.artifact ?? {};
  const technical = item.technical ?? {};
  els.sceneMeta.append(
    metaRow('Capture', item.captureId),
    metaRow('Profile', technical.profile),
    metaRow('Trainer', technical.backend ?? technical.method),
    metaRow('Splats', formatCount(artifact.splatCount)),
    metaRow('Size', formatBytes(artifact.sizeBytes)),
    metaRow('Iterations', formatCount(technical.iterations)),
    metaRow('Images', formatCount(technical.imagesUsed)),
    metaRow('Reference views', formatCount(technical.cameraViews ?? manifest.cameraViews?.length)),
    metaRow('Quality', compactQualityLabel(technical)),
    metaRow('Device', technical.device),
    metaRow('Created', formatDate(item.createdAt)),
  );
  renderReviewPanel(item, manifest);
}

function resetScenePanel(message = 'Choose a scene from the gallery') {
  selectedId = null;
  selectedDetail = null;
  els.sceneTitle.textContent = 'Select a Scene';
  setSceneStatus('idle', 'neutral');
  setDownload(els.downloadSplatLink, null);
  setDownload(els.downloadManifestLink, null);
  els.deleteSceneButton.disabled = true;
  els.overlay.hidden = false;
  els.overlay.textContent = message;
  renderSceneMeta(null);
}

function resetController() {
  if (!controller) return;
  controller.dispose();
  controller = null;
}

async function ensureController() {
  if (controller) return controller;
  setSceneStatus('loading viewer', 'neutral');
  viewerModulePromise ??= import('./spark-viewer.js');
  const { createSparkViewer } = await viewerModulePromise;
  controller = createSparkViewer({
    canvas: els.canvas,
    overlay: els.overlay,
    onStatus: (text, type = 'neutral') => {
      if (text) setSceneStatus(text, type);
    },
  });
  controller.setNavigationMode(navigationMode);
  controller.setNavigationSensitivity(navigationSensitivity);
  return controller;
}

function renderCard(item) {
  const card = document.createElement('article');
  card.className = 'gallery-card';
  card.dataset.jobId = item.id;
  card.tabIndex = 0;

  const thumb = document.createElement('button');
  thumb.className = 'gallery-card-thumb';
  thumb.type = 'button';
  thumb.setAttribute('aria-label', `Open ${item.name}`);
  if (item.thumbnailUrl) {
    const image = document.createElement('img');
    image.src = item.thumbnailUrl;
    image.alt = '';
    image.loading = 'lazy';
    thumb.append(image);
  } else {
    const placeholder = document.createElement('span');
    placeholder.textContent = '3DGS';
    thumb.append(placeholder);
  }

  const body = document.createElement('div');
  body.className = 'gallery-card-body';
  const title = document.createElement('h3');
  title.textContent = item.name;
  const meta = document.createElement('div');
  meta.className = 'gallery-card-meta';
  meta.append(
    metaRow('Splats', formatCount(item.artifact?.splatCount)),
    metaRow('Size', formatBytes(item.artifact?.sizeBytes)),
    metaRow('Profile', item.technical?.profile ?? '-'),
    metaRow('Images', formatCount(item.technical?.imagesUsed)),
    metaRow('Quality', compactQualityLabel(item.technical)),
  );
  const footer = document.createElement('div');
  footer.className = 'gallery-card-footer';
  const status = document.createElement('span');
  status.className = pillClass(item.status);
  status.textContent = item.status ?? 'unknown';
  const deleteButton = document.createElement('button');
  deleteButton.className = 'danger-mini-action';
  deleteButton.type = 'button';
  deleteButton.textContent = 'Delete';
  footer.append(status, deleteButton);

  body.append(title, meta, footer);
  card.append(thumb, body);

  const open = () => selectScene(item.id).catch(showError);
  thumb.addEventListener('click', open);
  card.addEventListener('click', (event) => {
    if (event.target.closest('button, a')) return;
    open();
  });
  card.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') open();
  });
  deleteButton.addEventListener('click', (event) => {
    event.stopPropagation();
    deleteScene(item.id).catch(showError);
  });
  return card;
}

function renderGallery() {
  els.grid.replaceChildren(...items.map(renderCard));
  els.empty.hidden = items.length > 0;
  els.status.textContent = `${items.length} packaged environment${items.length === 1 ? '' : 's'}`;
  for (const card of els.grid.querySelectorAll('.gallery-card')) {
    card.classList.toggle('active', card.dataset.jobId === selectedId);
  }
}

async function loadGallery() {
  els.status.textContent = 'Loading environments';
  const response = await fetch('/api/gallery', { cache: 'no-store' });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `gallery ${response.status}`);
  items = Array.isArray(payload.items) ? payload.items : [];
  renderGallery();
}

async function selectScene(jobId, updateUrl = true) {
  const item = items.find((candidate) => candidate.id === jobId);
  if (!item) return;
  selectedId = jobId;
  renderGallery();
  els.sceneTitle.textContent = item.name;
  setSceneStatus('loading', 'neutral');
  renderSceneMeta(item);
  setDownload(els.downloadSplatLink, item.artifactUrl, item.artifactFileName);
  setDownload(els.downloadManifestLink, item.viewerManifestUrl, item.manifestFileName);
  els.deleteSceneButton.disabled = false;
  if (updateUrl) {
    window.history.replaceState({}, '', `/gallery?scene=${encodeURIComponent(jobId)}`);
  }

  const response = await fetch(`/api/gallery/jobs/${encodeURIComponent(jobId)}`, { cache: 'no-store' });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `scene ${response.status}`);
  selectedDetail = payload;
  const manifest = payload.manifest ?? {};
  const artifactUrl = manifest.artifact?.url;
  if (!artifactUrl) throw new Error('selected scene has no splat artifact');
  setDownload(els.downloadSplatLink, manifest.export?.primaryAssetUrl ?? artifactUrl, item.artifactFileName);
  setDownload(els.downloadManifestLink, item.viewerManifestUrl, item.manifestFileName);
  renderSceneMeta(payload.item ?? item, manifest);
  const viewer = await ensureController();
  const result = await viewer.load({
    url: artifactUrl,
    cameraViews: Array.isArray(manifest.cameraViews) ? manifest.cameraViews : [],
  });
  setSceneStatus(result?.status === 'pass' || result?.status === 'cached' ? 'ready' : result?.status ?? 'loaded', 'pass');
}

async function deleteScene(jobId = selectedId) {
  const item = items.find((candidate) => candidate.id === jobId);
  if (!item) return;
  const confirmed = window.confirm(`Delete "${item.name}" from the local gallery? The output folder will be moved to outputs/deleted-jobs.`);
  if (!confirmed) return;
  const response = await fetch(`/api/gallery/jobs/${encodeURIComponent(jobId)}`, { method: 'DELETE' });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `delete ${response.status}`);
  if (selectedId === jobId) {
    resetController();
    resetScenePanel('Scene deleted from gallery');
    window.history.replaceState({}, '', '/gallery');
  }
  await loadGallery();
}

function setNavigationMode(mode) {
  navigationMode = mode === 'orbit' ? 'orbit' : 'walk';
  els.walkButton.classList.toggle('active', navigationMode === 'walk');
  els.orbitButton.classList.toggle('active', navigationMode === 'orbit');
  els.walkButton.setAttribute('aria-pressed', String(navigationMode === 'walk'));
  els.orbitButton.setAttribute('aria-pressed', String(navigationMode === 'orbit'));
  controller?.setNavigationMode(navigationMode);
}

function setSensitivity(value) {
  const numeric = Number(value);
  const percent = Number.isFinite(numeric) ? Math.min(120, Math.max(20, numeric)) : 55;
  navigationSensitivity = percent / 100;
  els.sensitivityInput.value = String(Math.round(percent));
  els.sensitivityValue.textContent = `${Math.round(percent)}%`;
  controller?.setNavigationSensitivity(navigationSensitivity);
}

function attachControls() {
  els.refreshButton.addEventListener('click', () => loadGallery().catch(showError));
  els.deleteSceneButton.addEventListener('click', () => deleteScene().catch(showError));
  els.walkButton.addEventListener('click', () => setNavigationMode('walk'));
  els.orbitButton.addEventListener('click', () => setNavigationMode('orbit'));
  els.sensitivityInput.addEventListener('input', (event) => setSensitivity(event.target.value));
  els.panLeftButton.addEventListener('click', () => controller?.pan(-1, 0));
  els.panRightButton.addEventListener('click', () => controller?.pan(1, 0));
  els.panUpButton.addEventListener('click', () => controller?.pan(0, 1));
  els.panDownButton.addEventListener('click', () => controller?.pan(0, -1));
  els.resetButton.addEventListener('click', () => controller?.reset());
  els.zoomOutButton.addEventListener('click', () => controller?.zoom(0.86));
  els.zoomInButton.addEventListener('click', () => controller?.zoom(1.16));
  els.cameraPrevButton.addEventListener('click', () => controller?.previousCameraView());
  els.cameraNextButton.addEventListener('click', () => controller?.nextCameraView());
}

function showError(error) {
  els.status.textContent = error.message;
  setSceneStatus('error', 'fail');
  els.overlay.hidden = false;
  els.overlay.textContent = error.message;
}

attachControls();
setSensitivity(55);
resetScenePanel();

try {
  await loadGallery();
  const requested = new URLSearchParams(window.location.search).get('scene');
  if (requested) await selectScene(requested, false);
} catch (error) {
  showError(error);
}
