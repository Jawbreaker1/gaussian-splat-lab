const els = {
  grid: document.querySelector('#galleryGrid'),
  empty: document.querySelector('#galleryEmpty'),
  status: document.querySelector('#galleryStatus'),
  refreshButton: document.querySelector('#refreshGalleryButton'),
  searchInput: document.querySelector('#gallerySearchInput'),
  sortSelect: document.querySelector('#gallerySortSelect'),
  sceneTitle: document.querySelector('#sceneTitle'),
  sceneStatusPill: document.querySelector('#sceneStatusPill'),
  downloadSplatLink: document.querySelector('#downloadSplatLink'),
  downloadManifestLink: document.querySelector('#downloadManifestLink'),
  deleteSceneButton: document.querySelector('#deleteSceneButton'),
  canvas: document.querySelector('#gallerySparkCanvas'),
  overlay: document.querySelector('#gallerySparkOverlay'),
  sceneMeta: document.querySelector('#gallerySceneMeta'),
  variantSwitch: document.querySelector('#galleryVariantSwitch'),
  guidedButton: document.querySelector('#galleryGuidedButton'),
  safeButton: document.querySelector('#gallerySafeButton'),
  freeButton: document.querySelector('#galleryFreeButton'),
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
  maximizeButton: document.querySelector('#galleryMaximizeButton'),
  pathPlayButton: document.querySelector('#galleryPathPlayButton'),
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
let guardrailMode = 'safe';
let guidedPathPlaying = false;
let selectedVariantId = 'viewer_default';
let navigationSensitivity = 0.55;
let searchTerm = '';
let sortMode = 'newest';
let sceneMaximized = false;

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

function formatDuration(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value < 0) return '-';
  if (value < 60) return `${Math.round(value)}s`;
  const totalSeconds = Math.round(value);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const rest = totalSeconds % 60;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return rest > 0 ? `${minutes}m ${rest}s` : `${minutes}m`;
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

function qualitySortValue(item) {
  const technical = item?.technical ?? {};
  if (technical.ssim != null) return Number(technical.ssim);
  if (technical.psnr != null) return Number(technical.psnr) / 100;
  if (technical.meanMae != null) return -Number(technical.meanMae) / 100;
  if (technical.previewScore != null) return -Number(technical.previewScore) / 100;
  return -Infinity;
}

function newestSortValue(item) {
  const timestamp = new Date(item?.updatedAt ?? item?.createdAt ?? 0).getTime();
  return Number.isFinite(timestamp) ? timestamp : 0;
}

function searchableText(item) {
  return [
    item.name,
    item.captureId,
    item.id,
    item.status,
    item.technical?.profile,
    item.technical?.backend,
    item.technical?.method,
  ].filter(Boolean).join(' ').toLowerCase();
}

function filteredItems() {
  const term = searchTerm.trim().toLowerCase();
  const result = term
    ? items.filter((item) => searchableText(item).includes(term))
    : [...items];
  result.sort((left, right) => {
    if (sortMode === 'name') {
      return String(left.name ?? '').localeCompare(String(right.name ?? ''), undefined, { sensitivity: 'base' });
    }
    if (sortMode === 'quality') {
      const leftQuality = qualitySortValue(left);
      const rightQuality = qualitySortValue(right);
      if (rightQuality === leftQuality) return 0;
      return rightQuality - leftQuality;
    }
    if (sortMode === 'splats') {
      return Number(right.artifact?.splatCount ?? -1) - Number(left.artifact?.splatCount ?? -1);
    }
    return newestSortValue(right) - newestSortValue(left);
  });
  return result;
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

function artifactSplatCount(artifact = {}) {
  return artifact?.ply?.vertexCount ?? artifact?.splatCount ?? null;
}

function artifactVariantOptions(manifest = {}, item = {}) {
  const manifestVariants = Array.isArray(manifest.artifactVariants) ? manifest.artifactVariants : [];
  if (manifestVariants.length) {
    return manifestVariants.filter((variant) => variant?.url || variant?.repoRelativePath || variant?.path);
  }
  const artifact = manifest.artifact ?? {};
  if (!artifact.url && !item.artifactUrl) return [];
  return [
    {
      id: 'viewer_default',
      label: 'Viewer default',
      url: artifact.url ?? item.artifactUrl,
      sizeBytes: artifact.sizeBytes ?? item.artifact?.sizeBytes,
      ply: artifact.ply ?? { vertexCount: item.artifact?.splatCount },
    },
  ];
}

function variantFileName(item = {}, variant = {}) {
  const base = item.artifactFileName || `${item.id || 'scene'}.ply`;
  if (variant?.role === 'archive_export' || variant?.id === 'full_export') return base;
  if (variant?.role === 'browser_viewer' || variant?.id === 'viewer_default') {
    return base.replace(/\.ply$/i, '.interactive.ply');
  }
  if (!variant?.id) return base;
  const safeId = String(variant.id).replace(/[^a-z0-9_-]+/gi, '-').toLowerCase();
  return base.replace(/\.ply$/i, `.${safeId}.ply`);
}

function renderVariantSwitch(variants = [], activeId = selectedVariantId) {
  els.variantSwitch.replaceChildren();
  els.variantSwitch.hidden = variants.length <= 1;
  for (const variant of variants) {
    const button = document.createElement('button');
    button.className = 'nav-mode-button';
    button.type = 'button';
    button.textContent = variant.label ?? variant.id ?? 'Variant';
    button.dataset.variantId = variant.id ?? 'viewer_default';
    const active = button.dataset.variantId === activeId;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
    button.addEventListener('click', () => {
      loadSelectedVariant(button.dataset.variantId).catch(showError);
    });
    els.variantSwitch.append(button);
  }
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

function renderSceneMeta(item, manifest = {}, variant = null) {
  els.sceneMeta.replaceChildren();
  if (!item) {
    els.sceneMeta.append(metaRow('Scene', 'No scene selected'));
    renderReviewPanel(null);
    return;
  }
  const artifact = variant ?? item.artifact ?? {};
  const technical = item.technical ?? {};
  const rendering = item.rendering ?? {};
  const stageSeconds = rendering.stageSeconds ?? {};
  const rows = [
    metaRow('Capture', item.captureId),
    metaRow('Variant', variant?.label ?? 'Viewer default'),
    metaRow('Profile', technical.profile),
    metaRow('Trainer', technical.backend ?? technical.method),
    metaRow('Splats', formatCount(artifactSplatCount(artifact))),
    metaRow('Size', formatBytes(artifact.sizeBytes)),
    metaRow('Iterations', formatCount(technical.iterations)),
    metaRow('Images', formatCount(technical.imagesUsed)),
    metaRow('Reference views', formatCount(technical.cameraViews ?? manifest.cameraViews?.length)),
    metaRow('Quality', compactQualityLabel(technical)),
    metaRow('Device', technical.device),
    metaRow('Generated', formatDate(rendering.generatedAt ?? item.generatedAt ?? item.updatedAt ?? item.createdAt)),
    metaRow('Total time', formatDuration(rendering.wallClockSeconds)),
    metaRow('Measured stages', formatDuration(rendering.measuredStageSeconds)),
    metaRow('Training time', formatDuration(stageSeconds.splat_training)),
    metaRow('SfM time', formatDuration(stageSeconds.sfm)),
  ];
  els.sceneMeta.append(...rows);
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
  selectedVariantId = 'viewer_default';
  els.variantSwitch.replaceChildren();
  els.variantSwitch.hidden = true;
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
  controller.setGuardrailMode(guardrailMode);
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
    metaRow('Profile', item.technical?.profile ?? '-'),
    metaRow('Splats', formatCount(item.artifact?.splatCount)),
    metaRow('Images', formatCount(item.technical?.imagesUsed)),
    metaRow('Quality', compactQualityLabel(item.technical)),
    metaRow('Generated', formatDate(item.rendering?.generatedAt ?? item.generatedAt ?? item.updatedAt)),
    metaRow('Time', formatDuration(item.rendering?.wallClockSeconds ?? item.rendering?.measuredStageSeconds)),
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
  const visibleItems = filteredItems();
  els.grid.replaceChildren(...visibleItems.map(renderCard));
  els.empty.hidden = visibleItems.length > 0;
  els.empty.textContent = items.length ? 'No scenes match the current filter.' : 'No packaged 3DGS environments yet.';
  const total = `${items.length} packaged environment${items.length === 1 ? '' : 's'}`;
  els.status.textContent = visibleItems.length === items.length
    ? total
    : `${visibleItems.length} of ${total}`;
  for (const card of els.grid.querySelectorAll('.gallery-card')) {
    card.classList.toggle('active', card.dataset.jobId === selectedId);
  }
  const activeCard = selectedId ? els.grid.querySelector(`.gallery-card[data-job-id="${CSS.escape(selectedId)}"]`) : null;
  if (activeCard) {
    const padding = 8;
    const cardTop = activeCard.offsetTop;
    const cardBottom = cardTop + activeCard.offsetHeight;
    const viewportTop = els.grid.scrollTop;
    const viewportBottom = viewportTop + els.grid.clientHeight;
    if (cardTop < viewportTop) {
      els.grid.scrollTop = Math.max(0, cardTop - padding);
    } else if (cardBottom > viewportBottom) {
      els.grid.scrollTop = cardBottom - els.grid.clientHeight + padding;
    }
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

async function loadSelectedVariant(variantId = selectedVariantId) {
  if (!selectedDetail) return;
  const manifest = selectedDetail.manifest ?? {};
  const item = selectedDetail.item ?? items.find((candidate) => candidate.id === selectedId);
  const variants = artifactVariantOptions(manifest, item);
  const variant = variants.find((candidate) => candidate.id === variantId) ?? variants[0];
  if (!variant?.url) throw new Error('selected artifact variant has no splat URL');
  selectedVariantId = variant.id ?? 'viewer_default';
  renderVariantSwitch(variants, selectedVariantId);
  setSceneStatus(`loading ${variant.label ?? 'variant'}`, 'neutral');
  setDownload(els.downloadSplatLink, variant.url, variantFileName(item, variant));
  renderSceneMeta(item, manifest, variant);
  const viewer = await ensureController();
  const result = await viewer.load({
    url: variant.url,
    cameraViews: Array.isArray(manifest.cameraViews) ? manifest.cameraViews : [],
  });
  setSceneStatus(result?.status === 'pass' || result?.status === 'cached' ? 'ready' : result?.status ?? 'loaded', 'pass');
}

async function selectScene(jobId, updateUrl = true) {
  const item = items.find((candidate) => candidate.id === jobId);
  if (!item) return;
  selectedId = jobId;
  selectedVariantId = 'viewer_default';
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
  const variants = artifactVariantOptions(manifest, payload.item ?? item);
  if (!variants.length) throw new Error('selected scene has no splat artifact');
  selectedVariantId = variants.some((variant) => variant.id === 'viewer_default')
    ? 'viewer_default'
    : variants[0].id;
  renderVariantSwitch(variants, selectedVariantId);
  setDownload(els.downloadSplatLink, variants[0].url, variantFileName(item, variants[0]));
  setDownload(els.downloadManifestLink, item.viewerManifestUrl, item.manifestFileName);
  await loadSelectedVariant(selectedVariantId);
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
  if (navigationMode === 'orbit' && guardrailMode === 'guided') {
    setGuardrailMode('safe');
  }
  els.walkButton.classList.toggle('active', navigationMode === 'walk');
  els.orbitButton.classList.toggle('active', navigationMode === 'orbit');
  els.walkButton.setAttribute('aria-pressed', String(navigationMode === 'walk'));
  els.orbitButton.setAttribute('aria-pressed', String(navigationMode === 'orbit'));
  controller?.setNavigationMode(navigationMode);
}

function setGuardrailMode(mode) {
  guardrailMode = ['guided', 'safe', 'free'].includes(mode) ? mode : 'safe';
  if (guardrailMode !== 'guided') guidedPathPlaying = false;
  els.guidedButton.classList.toggle('active', guardrailMode === 'guided');
  els.safeButton.classList.toggle('active', guardrailMode === 'safe');
  els.freeButton.classList.toggle('active', guardrailMode === 'free');
  els.guidedButton.setAttribute('aria-pressed', String(guardrailMode === 'guided'));
  els.safeButton.setAttribute('aria-pressed', String(guardrailMode === 'safe'));
  els.freeButton.setAttribute('aria-pressed', String(guardrailMode === 'free'));
  if (guardrailMode === 'guided' && navigationMode !== 'walk') {
    setNavigationMode('walk');
  }
  const result = controller?.setGuardrailMode(guardrailMode);
  if (result?.guidedPlaying != null) guidedPathPlaying = Boolean(result.guidedPlaying);
  else if (guardrailMode === 'guided') guidedPathPlaying = true;
  syncGuidedPlaybackButton();
}

function syncGuidedPlaybackButton() {
  const active = guardrailMode === 'guided' && guidedPathPlaying;
  els.pathPlayButton.textContent = active ? '⏸' : '▶';
  els.pathPlayButton.title = active ? 'Pause guided path' : 'Play guided path';
  els.pathPlayButton.setAttribute('aria-label', active ? 'Pause guided path' : 'Play guided path');
  els.pathPlayButton.setAttribute('aria-pressed', String(active));
  els.pathPlayButton.classList.toggle('active', active);
}

function setGuidedPlayback(playing) {
  if (guardrailMode !== 'guided') {
    setGuardrailMode('guided');
    if (playing === false) {
      guidedPathPlaying = false;
      controller?.setGuidedPlayback(false);
    }
  } else {
    guidedPathPlaying = Boolean(playing);
    const result = controller?.setGuidedPlayback(guidedPathPlaying);
    if (result?.guidedPlaying != null) guidedPathPlaying = Boolean(result.guidedPlaying);
  }
  syncGuidedPlaybackButton();
}

function setSensitivity(value) {
  const numeric = Number(value);
  const percent = Number.isFinite(numeric) ? Math.min(120, Math.max(20, numeric)) : 55;
  navigationSensitivity = percent / 100;
  els.sensitivityInput.value = String(Math.round(percent));
  els.sensitivityValue.textContent = `${Math.round(percent)}%`;
  controller?.setNavigationSensitivity(navigationSensitivity);
}

function setSceneMaximized(value) {
  sceneMaximized = Boolean(value);
  document.body.classList.toggle('gallery-scene-maximized', sceneMaximized);
  els.maximizeButton.textContent = sceneMaximized ? '×' : '⛶';
  els.maximizeButton.title = sceneMaximized ? 'Exit full view' : 'Maximize scene';
  els.maximizeButton.setAttribute('aria-label', sceneMaximized ? 'Exit full view' : 'Maximize scene');
  els.maximizeButton.setAttribute('aria-pressed', String(sceneMaximized));
  if (sceneMaximized) {
    els.canvas.focus({ preventScroll: true });
  }
}

function attachControls() {
  els.refreshButton.addEventListener('click', () => loadGallery().catch(showError));
  els.searchInput.addEventListener('input', (event) => {
    searchTerm = event.target.value;
    renderGallery();
  });
  els.sortSelect.addEventListener('change', (event) => {
    sortMode = event.target.value;
    renderGallery();
  });
  els.deleteSceneButton.addEventListener('click', () => deleteScene().catch(showError));
  els.guidedButton.addEventListener('click', () => setGuardrailMode('guided'));
  els.safeButton.addEventListener('click', () => setGuardrailMode('safe'));
  els.freeButton.addEventListener('click', () => setGuardrailMode('free'));
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
  els.maximizeButton.addEventListener('click', () => setSceneMaximized(!sceneMaximized));
  els.pathPlayButton.addEventListener('click', () => setGuidedPlayback(!(guardrailMode === 'guided' && guidedPathPlaying)));
  els.cameraPrevButton.addEventListener('click', () => controller?.previousCameraView());
  els.cameraNextButton.addEventListener('click', () => controller?.nextCameraView());
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && sceneMaximized) setSceneMaximized(false);
  });
}

function showError(error) {
  els.status.textContent = error.message;
  setSceneStatus('error', 'fail');
  els.overlay.hidden = false;
  els.overlay.textContent = error.message;
}

attachControls();
setGuardrailMode('safe');
syncGuidedPlaybackButton();
setSensitivity(55);
resetScenePanel();

try {
  await loadGallery();
  const requested = new URLSearchParams(window.location.search).get('scene');
  if (requested) await selectScene(requested, false);
} catch (error) {
  showError(error);
}
