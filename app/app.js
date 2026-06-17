const els = {
  machineLabel: document.querySelector('#machineLabel'),
  statusStrip: document.querySelector('#statusStrip'),
  captureSelect: document.querySelector('#captureSelect'),
  captureSummary: document.querySelector('#captureSummary'),
  captureMeta: document.querySelector('#captureMeta'),
  videoFileInput: document.querySelector('#videoFileInput'),
  acceptCaptureWarning: document.querySelector('#acceptCaptureWarning'),
  acceptCaptureWarningRow: document.querySelector('#acceptCaptureWarningRow'),
  importVideoButton: document.querySelector('#importVideoButton'),
  importStatus: document.querySelector('#importStatus'),
  planJobButton: document.querySelector('#planJobButton'),
  refreshButton: document.querySelector('#refreshButton'),
  jobBox: document.querySelector('#jobBox'),
  preflightList: document.querySelector('#preflightList'),
  pipelineList: document.querySelector('#pipelineList'),
  gateCount: document.querySelector('#gateCount'),
  pipelineProgressText: document.querySelector('#pipelineProgressText'),
  pipelineCurrentStage: document.querySelector('#pipelineCurrentStage'),
  pipelineProgressBar: document.querySelector('#pipelineProgressBar'),
  blockedCount: document.querySelector('#blockedCount'),
  complianceGrid: document.querySelector('#complianceGrid'),
  viewerStatusPill: document.querySelector('#viewerStatusPill'),
  viewerPanLeftButton: document.querySelector('#viewerPanLeftButton'),
  viewerPanRightButton: document.querySelector('#viewerPanRightButton'),
  viewerPanUpButton: document.querySelector('#viewerPanUpButton'),
  viewerPanDownButton: document.querySelector('#viewerPanDownButton'),
  viewerOrbitLeftButton: document.querySelector('#viewerOrbitLeftButton'),
  viewerOrbitRightButton: document.querySelector('#viewerOrbitRightButton'),
  viewerOrbitUpButton: document.querySelector('#viewerOrbitUpButton'),
  viewerOrbitDownButton: document.querySelector('#viewerOrbitDownButton'),
  viewerResetButton: document.querySelector('#viewerResetButton'),
  viewerZoomOutButton: document.querySelector('#viewerZoomOutButton'),
  viewerZoomInButton: document.querySelector('#viewerZoomInButton'),
  viewerCameraPrevButton: document.querySelector('#viewerCameraPrevButton'),
  viewerCameraNextButton: document.querySelector('#viewerCameraNextButton'),
  renderCompare: document.querySelector('#renderCompare'),
  sampleRenderFigure: document.querySelector('#sampleRenderFigure'),
  sampleTargetFigure: document.querySelector('#sampleTargetFigure'),
  renderReviewFigure: document.querySelector('#renderReviewFigure'),
  sampleRenderImage: document.querySelector('#sampleRenderImage'),
  sampleTargetImage: document.querySelector('#sampleTargetImage'),
  renderReviewImage: document.querySelector('#renderReviewImage'),
  viewerMeta: document.querySelector('#viewerMeta'),
  viewerModeSparkButton: document.querySelector('#viewerModeSparkButton'),
  viewerModeDebugButton: document.querySelector('#viewerModeDebugButton'),
  sparkViewport: document.querySelector('#sparkViewport'),
  sparkCanvas: document.querySelector('#sparkCanvas'),
  sparkOverlay: document.querySelector('#sparkOverlay'),
  canvas: document.querySelector('#splatCanvas'),
};

let state = null;
let activeJob = null;
let runningStage = null;
let importingVideo = false;
let viewerLoadToken = 0;
let viewerReadyResolved = false;
let resolveViewerReady = null;
let captureSelectionTouched = false;
const viewerReadyPromise = new Promise((resolve) => {
  resolveViewerReady = resolve;
});

const viewerScene = {
  mode: 'spark',
  pointData: null,
  pointCount: 0,
  artifactUrl: null,
  status: 'pending',
  rotationX: -0.28,
  rotationY: 0.62,
  panX: 0,
  panY: 0,
  zoom: 1.05,
  dragging: false,
  panning: false,
  lastX: 0,
  lastY: 0,
  renderer: null,
  sparkController: null,
  sparkArtifactUrl: null,
  sparkFailed: false,
  cameraViewCount: 0,
  activeCameraView: null,
  uploadedArtifactUrl: null,
  webglFailed: false,
};

const runnableStages = new Set(['framework_license', 'environment', 'intake', 'frame_sampling', 'sfm', 'splat_training', 'packaging', 'viewer', 'quality_report']);
const heavyStages = new Set(['sfm', 'splat_training', 'viewer']);
const fallbackStageNames = {
  framework_license: 'Dependency Review',
  environment: 'Workstation Check',
  intake: 'Video Intake',
  frame_sampling: 'Frame Sampling',
  sfm: 'SfM Camera Solve',
  splat_training: 'Splat Training',
  packaging: 'Artifact Packaging',
  viewer: 'Viewer Validation',
  quality_report: 'Quality Report',
};

function statusType(status) {
  if (status === 'pass' || status === 'accepted' || status === 'preferred') return 'pass';
  if (status === 'warning' || status === 'conditional' || status === 'deferred' || status === 'setup_gap') return 'warning';
  if (status === 'fail' || status === 'blocked' || status === 'blocked_license' || status === 'blocked_workload') return 'fail';
  return 'neutral';
}

function pill(text, type = 'neutral') {
  const span = document.createElement('span');
  span.className = `pill ${type}`;
  span.textContent = text;
  return span;
}

function sourceSummary(title, value) {
  const div = document.createElement('div');
  div.className = 'source-summary-item';
  const label = document.createElement('span');
  const text = document.createElement('strong');
  label.textContent = title;
  text.textContent = value ?? '-';
  div.append(label, text);
  return div;
}

function row(label, value) {
  const div = document.createElement('div');
  div.className = 'meta-row';
  const a = document.createElement('span');
  const b = document.createElement('span');
  a.textContent = label;
  b.textContent = value ?? '-';
  div.append(a, b);
  return div;
}

function selectedCapture() {
  const id = els.captureSelect.value;
  return state?.captures?.find((capture) => capture.id === id) ?? null;
}

function selectedCaptureReadiness() {
  const id = els.captureSelect.value;
  return state?.captureReadiness?.find((capture) => capture.id === id) ?? null;
}

function selectedLicenseCheck() {
  return selectedCaptureReadiness()?.checks?.find((check) => check.id === 'source_license') ?? null;
}

function updateImportControls() {
  const capture = selectedCapture();
  const file = els.videoFileInput.files?.[0] ?? null;
  const licenseStatus = selectedLicenseCheck()?.status;
  const needsWarningAcceptance = licenseStatus === 'warning';
  els.acceptCaptureWarningRow.hidden = !needsWarningAcceptance;
  els.importVideoButton.disabled = !capture || !file || importingVideo || (needsWarningAcceptance && !els.acceptCaptureWarning.checked);
  els.importVideoButton.textContent = importingVideo ? 'Importing' : 'Import video';
}

function renderStatus() {
  els.statusStrip.replaceChildren();
  const validation = state?.validation ?? {};
  els.statusStrip.append(
    pill(validation.architecture ? 'architecture pass' : 'architecture missing', validation.architecture ? 'pass' : 'warning'),
    pill(validation.phase1 ? 'contracts pass' : 'contracts missing', validation.phase1 ? 'pass' : 'warning'),
    pill(validation.rtxVisible ? 'RTX visible' : 'RTX pending', validation.rtxVisible ? 'pass' : 'warning'),
  );
}

function renderCaptures() {
  const captures = state?.captures ?? [];
  const previousCaptureId = els.captureSelect.value;
  const activeCaptureId = activeJob?.job?.captureId;
  els.captureSelect.replaceChildren();
  for (const capture of captures) {
    const option = document.createElement('option');
    option.value = capture.id;
    option.textContent = capture.displayName || capture.id;
    els.captureSelect.append(option);
  }
  const captureIds = new Set(captures.map((capture) => capture.id));
  if (!captureSelectionTouched && activeCaptureId && captureIds.has(activeCaptureId)) {
    els.captureSelect.value = activeCaptureId;
  } else if (captureIds.has(previousCaptureId)) {
    els.captureSelect.value = previousCaptureId;
  }
  els.planJobButton.disabled = captures.length === 0;
  renderCaptureMeta();
}

function renderCaptureSummary(capture, readiness) {
  els.captureSummary.replaceChildren();
  if (!capture) {
    els.captureSummary.append(sourceSummary('State', 'No source selected'));
    return;
  }

  const header = document.createElement('div');
  header.className = 'source-summary-head';
  const name = document.createElement('strong');
  name.textContent = capture.displayName || capture.id;
  header.append(name, pill(readiness?.status ?? capture.status ?? 'unknown', statusType(readiness?.status ?? capture.status)));

  const source = capture.source?.license === 'local-test-only'
    ? 'Technical baseline only'
    : capture.source?.license ?? 'License unknown';
  els.captureSummary.append(
    header,
    sourceSummary('Use', source),
    sourceSummary('Scene', capture.capture?.subject ?? '-'),
    sourceSummary('Motion', capture.capture?.motion ?? '-'),
  );
}

function renderCaptureMeta() {
  const capture = selectedCapture();
  els.captureMeta.replaceChildren();
  if (!capture) {
    renderCaptureSummary(null, null);
    els.captureMeta.append(row('Status', 'No capture'));
    return;
  }

  const readiness = selectedCaptureReadiness();
  renderCaptureSummary(capture, readiness);
  updateImportControls();
  els.captureMeta.append(
    row('Capture ID', capture.id),
    row('File', readiness?.status ?? 'unknown'),
    row('Target', readiness?.sourcePath),
    row('Source', capture.source?.sourceUrl),
    row('Posture', readiness?.commercialPosture),
    row('License', capture.source?.license),
    row('Verified', capture.source?.licenseVerifiedAt),
    row('Motion', capture.capture?.motion),
    row('Duration', capture.capture?.expectedDurationSeconds ? `${capture.capture.expectedDurationSeconds}s` : null),
    row('Resolution', capture.capture?.expectedResolution),
    row('Pipeline', capture.pipeline?.training?.backend ?? 'planned'),
  );
}

function stageDisplayName(gate) {
  return gate.displayName || fallbackStageNames[gate.id] || gate.id.replaceAll('_', ' ');
}

function stageGroup(gate) {
  if (gate.group) return gate.group;
  return gate.id === 'framework_license' || gate.id === 'environment' ? 'preflight' : 'media_pipeline';
}

function buildStageItem(gate, index, jobStages) {
  const stage = jobStages.find((item) => item.id === gate.id);
  const item = document.createElement('article');
  const stageStatus = stage?.status ?? 'planned';
  item.className = `stage-item stage-${statusType(stageStatus)}`;

  const number = document.createElement('div');
  number.className = 'stage-index';
  number.textContent = String(index);

  const body = document.createElement('div');
  const title = document.createElement('div');
  title.className = 'stage-title';
  title.textContent = stageDisplayName(gate);
  const contract = document.createElement('div');
  contract.className = 'stage-contract';
  contract.textContent = `${gate.inputContract} → ${gate.outputContract}`;
  body.append(title, contract);

  const status = pill(stage?.status ?? 'planned', statusType(stage?.status ?? 'planned'));
  if (runnableStages.has(gate.id)) {
    const action = document.createElement('button');
    action.className = 'stage-action';
    action.type = 'button';
    action.textContent = runningStage === gate.id ? 'Running' : heavyStages.has(gate.id) ? 'Guarded' : 'Run';
    action.disabled = !activeJob || Boolean(runningStage);
    action.title = heavyStages.has(gate.id) ? `${stageDisplayName(gate)} requires explicit heavy-workload approval in CLI` : `Run ${stageDisplayName(gate)}`;
    action.addEventListener('click', () => runStage(gate.id));
    item.append(number, body, status, action);
  } else {
    item.append(number, body, status);
  }
  return item;
}

function renderPipelineProgress(gates, jobStages) {
  if (!activeJob) {
    els.pipelineProgressText.textContent = 'No job planned';
    els.pipelineCurrentStage.textContent = 'Select a source and plan a job';
    els.pipelineProgressBar.style.width = '0%';
    return;
  }

  const stageById = new Map(jobStages.map((stage) => [stage.id, stage]));
  let passed = 0;
  let warnings = 0;
  let blocked = 0;
  let currentGate = null;
  for (const gate of gates) {
    const status = stageById.get(gate.id)?.status ?? 'planned';
    if (status === 'pass') passed += 1;
    else if (status === 'warning') warnings += 1;
    else if (['fail', 'blocked', 'blocked_license', 'blocked_workload', 'setup_gap'].includes(status)) blocked += 1;
    if (!currentGate && status !== 'pass' && status !== 'warning') currentGate = gate;
  }

  const total = Math.max(1, gates.length);
  const percent = Math.round((passed / total) * 100);
  els.pipelineProgressText.textContent = `${passed}/${gates.length} passed${warnings ? `, ${warnings} warning` : ''}`;
  els.pipelineProgressBar.style.width = `${percent}%`;

  if (runningStage) {
    els.pipelineCurrentStage.textContent = `Running ${stageDisplayName({ id: runningStage })}`;
  } else if (blocked) {
    els.pipelineCurrentStage.textContent = `Needs attention: ${stageDisplayName(currentGate ?? gates[0])}`;
  } else if (currentGate) {
    els.pipelineCurrentStage.textContent = `Next: ${stageDisplayName(currentGate)}`;
  } else {
    els.pipelineCurrentStage.textContent = 'Pipeline complete';
  }
}

function renderStages() {
  const gates = state?.gates ?? [];
  const jobStages = activeJob?.stages ?? [];
  const preflight = gates.filter((gate) => stageGroup(gate) === 'preflight');
  const pipeline = gates.filter((gate) => stageGroup(gate) !== 'preflight');
  els.preflightList.replaceChildren();
  els.pipelineList.replaceChildren();
  els.gateCount.textContent = `${preflight.length} preflight / ${pipeline.length} pipeline`;
  renderPipelineProgress(gates, jobStages);

  preflight.forEach((gate, index) => {
    els.preflightList.append(buildStageItem(gate, index + 1, jobStages));
  });
  pipeline.forEach((gate, index) => {
    els.pipelineList.append(buildStageItem(gate, index + 1, jobStages));
  });
}

function renderCompliance() {
  const frameworks = state?.frameworks ?? [];
  const blocked = frameworks.filter((item) => item.decision === 'blocked').length;
  const conditional = frameworks.filter((item) => item.decision === 'conditional').length;
  els.blockedCount.textContent = `${blocked} blocked`;
  els.blockedCount.className = blocked > 0 ? 'pill blocked' : 'pill pass';

  els.complianceGrid.replaceChildren();
  els.complianceGrid.append(row('Accepted', String(frameworks.filter((item) => item.decision === 'accepted').length)));
  els.complianceGrid.append(row('Conditional', String(conditional)));
  els.complianceGrid.append(row('Preferred', String(frameworks.filter((item) => item.decision === 'preferred').length)));
  els.complianceGrid.append(row('Blocked', String(blocked)));

  for (const item of frameworks.slice(0, 8)) {
    const div = document.createElement('div');
    div.className = 'compliance-row';
    const name = document.createElement('span');
    const decision = pill(item.decision, item.decision);
    name.textContent = item.name;
    div.append(name, decision);
    els.complianceGrid.append(div);
  }
}

function renderJob() {
  els.jobBox.replaceChildren();
  if (!activeJob) {
    const empty = document.createElement('div');
    empty.className = 'muted';
    empty.textContent = 'No active job';
    els.jobBox.append(empty);
    return;
  }

  const job = activeJob.job;
  els.jobBox.append(
    row('Job', job.id),
    row('Status', job.status),
    row('Capture', job.captureId),
    row('Manifest', activeJob.jobPath),
  );
}

function renderAll() {
  els.machineLabel.textContent = state?.machineLabel ?? 'RTX workstation';
  renderStatus();
  renderCaptures();
  renderStages();
  renderCompliance();
  renderJob();
  renderViewerMeta();
  loadActiveViewerArtifact();
}

function markViewerReady() {
  if (viewerReadyResolved) return;
  viewerReadyResolved = true;
  resolveViewerReady?.();
}

async function loadState() {
  const response = await fetch('/api/state');
  if (!response.ok) throw new Error(`state ${response.status}`);
  state = await response.json();
  activeJob = state.latestJob ?? null;
  renderAll();
}

async function importVideo() {
  const capture = selectedCapture();
  const file = els.videoFileInput.files?.[0] ?? null;
  if (!capture || !file || importingVideo) return;
  importingVideo = true;
  els.importStatus.textContent = '';
  updateImportControls();
  try {
    const params = new URLSearchParams({
      captureId: capture.id,
      acceptWarning: String(els.acceptCaptureWarning.checked),
      overwrite: 'true',
    });
    const response = await fetch(`/api/captures/import-video?${params.toString()}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/octet-stream',
        'X-Filename': file.name,
      },
      body: file,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || payload.report?.checks?.[0]?.summary || `import ${response.status}`);
    els.videoFileInput.value = '';
    els.importStatus.textContent = `Imported ${file.name}`;
    await loadState();
  } catch (error) {
    els.importStatus.textContent = error.message;
  } finally {
    importingVideo = false;
    updateImportControls();
  }
}

async function createJob() {
  const capture = selectedCapture();
  if (!capture) return;
  els.planJobButton.disabled = true;
  try {
    const response = await fetch('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ captureId: capture.id }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `job ${response.status}`);
    activeJob = payload.job;
    await loadState();
  } catch (error) {
    els.jobBox.replaceChildren();
    const message = document.createElement('div');
    message.className = 'error-text';
    message.textContent = error.message;
    els.jobBox.append(message);
  } finally {
    els.planJobButton.disabled = false;
  }
}

async function runStage(stage) {
  if (!activeJob || runningStage) return;
  runningStage = stage;
  renderStages();
  try {
    const response = await fetch('/api/jobs/run-stage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jobPath: activeJob.jobPath, stage, acceptWarning: false, allowHeavy: false }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `stage ${response.status}`);
    activeJob = payload.job;
    await loadState();
  } catch (error) {
    els.jobBox.replaceChildren();
    const message = document.createElement('div');
    message.className = 'error-text';
    message.textContent = error.message;
    els.jobBox.append(message);
  } finally {
    runningStage = null;
    renderStages();
  }
}


function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function sigmoid(value) {
  return 1 / (1 + Math.exp(-value));
}

function formatBytes(value) {
  if (!Number.isFinite(value)) return '-';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function setViewerStatus(text, type = 'neutral') {
  els.viewerStatusPill.textContent = text;
  els.viewerStatusPill.className = `pill ${type}`;
}

function formatCount(value) {
  const number = Number(value);
  return Number.isFinite(number) ? new Intl.NumberFormat('en-US').format(number) : '-';
}

function formatGrowth(training = {}) {
  const initial = Number(training.initialGaussianCount);
  const final = Number(training.gaussianCount);
  if (!Number.isFinite(initial) || !Number.isFinite(final)) return '-';
  const factor = Number(training.gaussianGrowthFactor);
  const suffix = Number.isFinite(factor) ? ` (${factor.toFixed(2)}x)` : '';
  return `${formatCount(initial)} -> ${formatCount(final)}${suffix}`;
}

function viewerQuality(status, training = {}, runConfig = {}) {
  if (status !== 'pass') {
    return { text: status, type: status === 'warning' ? 'warning' : 'neutral' };
  }
  const profile = training.profile || runConfig.profile || 'unknown';
  const strategy = training.densifyStrategy || runConfig.densifyStrategy || 'none';
  const gaussianCount = Number(training.gaussianCount);
  if (profile === 'smoke' || strategy === 'none') return { text: 'smoke inspect', type: 'warning' };
  if (Number.isFinite(gaussianCount) && gaussianCount < 10000) return { text: 'thin inspect', type: 'warning' };
  if (profile === 'quality_probe') {
    return { text: training.renderReview?.status === 'pass' ? 'quality inspect' : 'quality warning', type: training.renderReview?.status === 'pass' ? 'pass' : 'warning' };
  }
  if (profile === 'rtx_reference') {
    return { text: training.renderReview?.status === 'pass' ? 'reference inspect' : 'reference warning', type: training.renderReview?.status === 'pass' ? 'pass' : 'warning' };
  }
  return { text: 'baseline inspect', type: 'pass' };
}

function setSampleImage(image, figure, url) {
  figure.hidden = !url;
  if (!url) {
    image.removeAttribute('src');
    return;
  }
  if (image.getAttribute('src') !== url) image.src = url;
}

function renderSampleComparison(preview = {}) {
  const renderUrl = preview.sampleRenderUrl;
  const targetUrl = preview.sampleTargetUrl;
  const reviewUrl = preview.renderReviewUrl;
  const hasSample = Boolean(renderUrl || targetUrl);
  els.renderCompare.hidden = !hasSample;
  setSampleImage(els.sampleRenderImage, els.sampleRenderFigure, renderUrl);
  setSampleImage(els.sampleTargetImage, els.sampleTargetFigure, targetUrl);
  setSampleImage(els.renderReviewImage, els.renderReviewFigure, reviewUrl);
}

function activeRendererLabel() {
  if (viewerScene.mode === 'spark') {
    if (viewerScene.sparkController && !viewerScene.sparkFailed) return 'Spark 3DGS render';
    if (viewerScene.sparkFailed) return 'Spark unavailable';
    return 'Spark loading';
  }
  return viewerScene.renderer ? 'PLY point debug' : 'debug loading';
}

function renderViewerMeta(extra = null) {
  els.viewerMeta.replaceChildren();
  const viewer = state?.viewerArtifact;
  const manifest = viewer?.manifest;
  const artifact = manifest?.artifact;
  if (!artifact) {
    renderSampleComparison();
    setViewerStatus('pending', 'neutral');
    els.viewerMeta.append(row('Artifact', 'No packaged splat'));
    return;
  }

  const ply = artifact.ply ?? {};
  const training = manifest?.training ?? {};
  const runConfig = manifest?.runConfig ?? {};
  const cameraViews = Array.isArray(manifest?.cameraViews) ? manifest.cameraViews : [];
  const activeView = extra?.activeCameraView ?? viewerScene.activeCameraView;
  renderSampleComparison(manifest?.preview ?? {});
  const status = viewer.viewerStatus ?? viewer.packagingStatus ?? 'packaged';
  const quality = viewerQuality(status, training, runConfig);
  setViewerStatus(quality.text, quality.type);
  els.viewerMeta.append(
    row('Artifact', artifact.format ?? 'ply'),
    row('Renderer', activeRendererLabel()),
    row('Profile', training.profile ?? runConfig.profile ?? '-'),
    row('Strategy', training.densifyStrategy ?? runConfig.densifyStrategy ?? '-'),
    row('Gaussians', formatCount(extra?.pointCount ?? (viewerScene.pointCount || ply.vertexCount))),
    row('Reference views', cameraViews.length ? `${formatCount(cameraViews.length)}${activeView?.imageName ? ` (${activeView.imageName})` : ''}` : '-'),
    row('Growth', formatGrowth(training)),
    row('Review MAE', training.renderReview?.meanMae ?? '-'),
    row('Size', formatBytes(artifact.sizeBytes)),
    row('Device', manifest?.device?.name ?? '-'),
  );
}

function propertySize(type) {
  return {
    char: 1,
    int8: 1,
    uchar: 1,
    uint8: 1,
    short: 2,
    int16: 2,
    ushort: 2,
    uint16: 2,
    int: 4,
    int32: 4,
    uint: 4,
    uint32: 4,
    float: 4,
    float32: 4,
    double: 8,
    float64: 8,
  }[type] ?? 0;
}

function readProperty(view, offset, type) {
  switch (type) {
    case 'char':
    case 'int8':
      return view.getInt8(offset);
    case 'uchar':
    case 'uint8':
      return view.getUint8(offset);
    case 'short':
    case 'int16':
      return view.getInt16(offset, true);
    case 'ushort':
    case 'uint16':
      return view.getUint16(offset, true);
    case 'int':
    case 'int32':
      return view.getInt32(offset, true);
    case 'uint':
    case 'uint32':
      return view.getUint32(offset, true);
    case 'double':
    case 'float64':
      return view.getFloat64(offset, true);
    case 'float':
    case 'float32':
    default:
      return view.getFloat32(offset, true);
  }
}

function parseBinaryPly(buffer) {
  const bytes = new Uint8Array(buffer);
  const decoder = new TextDecoder('ascii');
  const prefix = decoder.decode(bytes.slice(0, Math.min(bytes.length, 65536)));
  const endIndex = prefix.indexOf('end_header');
  if (endIndex < 0) throw new Error('PLY header missing end_header');
  let headerBytes = endIndex + 'end_header'.length;
  while (headerBytes < bytes.length && (bytes[headerBytes] === 10 || bytes[headerBytes] === 13)) headerBytes += 1;

  const header = decoder.decode(bytes.slice(0, headerBytes));
  const lines = header.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  let vertexCount = 0;
  let plyFormat = null;
  let inVertex = false;
  const properties = [];
  for (const line of lines) {
    const parts = line.split(/\s+/);
    if (parts[0] === 'format') plyFormat = parts[1];
    if (parts[0] === 'element') {
      inVertex = parts[1] === 'vertex';
      if (inVertex) vertexCount = Number.parseInt(parts[2], 10);
    } else if (inVertex && parts[0] === 'property' && parts.length >= 3) {
      const type = parts[1];
      properties.push({ type, name: parts[2], offset: 0, size: propertySize(type) });
    }
  }
  if (plyFormat !== 'binary_little_endian') throw new Error(`Unsupported PLY format ${plyFormat ?? 'unknown'}`);
  if (!Number.isFinite(vertexCount) || vertexCount <= 0) throw new Error('PLY vertex count is empty');

  let stride = 0;
  for (const property of properties) {
    if (!property.size) throw new Error(`Unsupported PLY property type ${property.type}`);
    property.offset = stride;
    stride += property.size;
  }
  const byName = new Map(properties.map((property) => [property.name, property]));
  for (const required of ['x', 'y', 'z']) {
    if (!byName.has(required)) throw new Error(`PLY missing ${required}`);
  }

  const view = new DataView(buffer);
  const shC0 = 0.28209479177387814;
  const points = [];
  for (let index = 0; index < vertexCount; index += 1) {
    const base = headerBytes + index * stride;
    const read = (name, fallback = 0) => {
      const property = byName.get(name);
      return property ? readProperty(view, base + property.offset, property.type) : fallback;
    };
    const r = byName.has('red') ? read('red') / 255 : read('f_dc_0', 0) * shC0 + 0.5;
    const g = byName.has('green') ? read('green') / 255 : read('f_dc_1', 0) * shC0 + 0.5;
    const b = byName.has('blue') ? read('blue') / 255 : read('f_dc_2', 0) * shC0 + 0.5;
    const scale = Math.exp((read('scale_0', -4) + read('scale_1', -4) + read('scale_2', -4)) / 3);
    points.push({
      x: read('x'),
      y: read('y'),
      z: read('z'),
      r: clamp(r, 0, 1),
      g: clamp(g, 0, 1),
      b: clamp(b, 0, 1),
      alpha: clamp(sigmoid(read('opacity', 0)), 0.08, 0.9),
      size: clamp(scale, 0.003, 0.08),
    });
  }
  return { points, vertexCount, properties };
}

function normalizePoints(points) {
  const bounds = points.reduce(
    (acc, point) => ({
      minX: Math.min(acc.minX, point.x),
      minY: Math.min(acc.minY, point.y),
      minZ: Math.min(acc.minZ, point.z),
      maxX: Math.max(acc.maxX, point.x),
      maxY: Math.max(acc.maxY, point.y),
      maxZ: Math.max(acc.maxZ, point.z),
    }),
    { minX: Infinity, minY: Infinity, minZ: Infinity, maxX: -Infinity, maxY: -Infinity, maxZ: -Infinity },
  );
  const centerX = (bounds.minX + bounds.maxX) / 2;
  const centerY = (bounds.minY + bounds.maxY) / 2;
  const centerZ = (bounds.minZ + bounds.maxZ) / 2;
  const extent = Math.max(bounds.maxX - bounds.minX, bounds.maxY - bounds.minY, bounds.maxZ - bounds.minZ, 1e-6);
  return points.map((point) => ({
    ...point,
    x: (point.x - centerX) / extent,
    y: (point.y - centerY) / extent,
    z: (point.z - centerZ) / extent,
  }));
}

async function loadViewerArtifact() {
  const artifact = state?.viewerArtifact?.manifest?.artifact;
  const url = artifact?.url;
  if (!url) {
    viewerScene.pointData = null;
    viewerScene.pointCount = 0;
    viewerScene.artifactUrl = null;
    viewerScene.uploadedArtifactUrl = null;
    markViewerReady();
    renderViewerMeta();
    return;
  }
  if (viewerScene.artifactUrl === url && viewerScene.pointData) {
    renderViewerMeta({ pointCount: viewerScene.pointCount });
    return;
  }

  const token = ++viewerLoadToken;
  setViewerStatus('loading', 'neutral');
  try {
    const response = await fetch(url, { cache: 'no-store' });
    if (!response.ok) throw new Error(`artifact ${response.status}`);
    const parsed = parseBinaryPly(await response.arrayBuffer());
    if (token !== viewerLoadToken) return;
    viewerScene.pointData = buildPointData(normalizePoints(parsed.points));
    viewerScene.pointCount = parsed.vertexCount;
    viewerScene.artifactUrl = url;
    viewerScene.uploadedArtifactUrl = null;
    uploadPointData();
    renderViewerMeta({ pointCount: parsed.vertexCount });
  } catch (error) {
    if (token !== viewerLoadToken) return;
    viewerScene.pointData = null;
    viewerScene.pointCount = 0;
    viewerScene.artifactUrl = null;
    viewerScene.uploadedArtifactUrl = null;
    setViewerStatus('viewer error', 'fail');
    els.viewerMeta.replaceChildren(row('Error', error.message));
    markViewerReady();
  }
}

function loadActiveViewerArtifact() {
  if (viewerScene.mode === 'spark') {
    loadSparkArtifact();
    return;
  }
  loadViewerArtifact();
}

async function ensureSparkController() {
  if (viewerScene.sparkController) return viewerScene.sparkController;
  if (viewerScene.sparkFailed) throw new Error('Spark renderer failed to initialize');
  const module = await import('./spark-viewer.js');
  viewerScene.sparkController = module.createSparkViewer({
    canvas: els.sparkCanvas,
    overlay: els.sparkOverlay,
    onStatus: (text, type = 'neutral') => {
      if (viewerScene.mode === 'spark' && text) setViewerStatus(text, type);
    },
  });
  renderViewerMeta({ pointCount: viewerScene.pointCount });
  return viewerScene.sparkController;
}

async function loadSparkArtifact() {
  const artifact = state?.viewerArtifact?.manifest?.artifact;
  const cameraViews = Array.isArray(state?.viewerArtifact?.manifest?.cameraViews) ? state.viewerArtifact.manifest.cameraViews : [];
  const url = artifact?.url;
  if (!url) {
    markViewerReady();
    return;
  }
  if (viewerScene.mode !== 'spark') return;
  try {
    setViewerStatus('Spark loading', 'neutral');
    const controller = await ensureSparkController();
    if (viewerScene.sparkArtifactUrl === url) {
      const viewState = controller.setCameraViews(cameraViews);
      viewerScene.cameraViewCount = viewState?.viewCount ?? cameraViews.length;
      viewerScene.activeCameraView = viewState?.activeView ?? null;
      const quality = viewerQuality(
        state?.viewerArtifact?.viewerStatus ?? 'pass',
        state?.viewerArtifact?.manifest?.training ?? {},
        state?.viewerArtifact?.manifest?.runConfig ?? {},
      );
      setViewerStatus(quality.text, quality.type);
      renderViewerMeta({ pointCount: viewerScene.pointCount, activeCameraView: viewerScene.activeCameraView });
      markViewerReady();
      return;
    }
    const result = await controller.load({ url, cameraViews });
    viewerScene.sparkArtifactUrl = url;
    viewerScene.sparkFailed = false;
    if (result?.splats) viewerScene.pointCount = result.splats;
    viewerScene.cameraViewCount = result?.viewCount ?? cameraViews.length;
    viewerScene.activeCameraView = result?.activeView ?? null;
    const status = state?.viewerArtifact?.viewerStatus ?? 'pass';
    const training = state?.viewerArtifact?.manifest?.training ?? {};
    const runConfig = state?.viewerArtifact?.manifest?.runConfig ?? {};
    const quality = viewerQuality(status, training, runConfig);
    setViewerStatus(quality.text, quality.type);
    renderViewerMeta({ pointCount: viewerScene.pointCount, activeCameraView: viewerScene.activeCameraView });
    markViewerReady();
  } catch (error) {
    viewerScene.sparkFailed = true;
    els.sparkOverlay.hidden = false;
    els.sparkOverlay.textContent = `Spark unavailable: ${error.message}`;
    setViewerStatus('Spark unavailable', 'warning');
    renderViewerMeta({ pointCount: viewerScene.pointCount });
    markViewerReady();
  }
}

function buildPointData(points) {
  const positions = new Float32Array(points.length * 3);
  const colors = new Float32Array(points.length * 4);
  const sizes = new Float32Array(points.length);
  for (let index = 0; index < points.length; index += 1) {
    const point = points[index];
    positions[index * 3] = point.x;
    positions[index * 3 + 1] = point.y;
    positions[index * 3 + 2] = point.z;
    colors[index * 4] = point.r;
    colors[index * 4 + 1] = point.g;
    colors[index * 4 + 2] = point.b;
    colors[index * 4 + 3] = point.alpha;
    sizes[index] = clamp(6 + point.size * 180, 4, 28);
  }
  return { positions, colors, sizes, count: points.length };
}

function resizeCanvasToDisplaySize(canvas) {
  const rect = canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  const width = Math.max(1, Math.round(rect.width * scale));
  const height = Math.max(1, Math.round(rect.height * scale));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  return { width, height, scale };
}

function compileShader(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const message = gl.getShaderInfoLog(shader) || 'shader compile failed';
    gl.deleteShader(shader);
    throw new Error(message);
  }
  return shader;
}

function createProgram(gl, vertexSource, fragmentSource) {
  const vertex = compileShader(gl, gl.VERTEX_SHADER, vertexSource);
  const fragment = compileShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
  const program = gl.createProgram();
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  gl.deleteShader(vertex);
  gl.deleteShader(fragment);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const message = gl.getProgramInfoLog(program) || 'program link failed';
    gl.deleteProgram(program);
    throw new Error(message);
  }
  return program;
}

function createSceneLines() {
  const positions = [];
  const colors = [];
  const pushLine = (a, b, color) => {
    positions.push(...a, ...b);
    colors.push(...color, ...color);
  };
  const gridColor = [0.42, 0.46, 0.49, 0.28];
  for (let step = -8; step <= 8; step += 1) {
    const value = step / 8;
    pushLine([-1, -0.58, value], [1, -0.58, value], gridColor);
    pushLine([value, -0.58, -1], [value, -0.58, 1], gridColor);
  }
  pushLine([-1.08, 0, 0], [1.08, 0, 0], [0.94, 0.28, 0.24, 0.78]);
  pushLine([0, -0.72, 0], [0, 0.72, 0], [0.28, 0.78, 0.48, 0.78]);
  pushLine([0, 0, -1.08], [0, 0, 1.08], [0.36, 0.56, 0.96, 0.78]);
  return {
    positions: new Float32Array(positions),
    colors: new Float32Array(colors),
    count: positions.length / 3,
  };
}

function initWebGLScene() {
  if (viewerScene.renderer || viewerScene.webglFailed) return viewerScene.renderer;
  const gl = els.canvas.getContext('webgl', { antialias: true, alpha: false, depth: true })
    || els.canvas.getContext('experimental-webgl', { antialias: true, alpha: false, depth: true });
  if (!gl) {
    viewerScene.webglFailed = true;
    setViewerStatus('no webgl', 'warning');
    return null;
  }

  try {
    const pointProgram = createProgram(
      gl,
      `
        attribute vec3 aPosition;
        attribute vec4 aColor;
        attribute float aSize;
        uniform mat4 uViewProjection;
        uniform float uPixelRatio;
        varying vec4 vColor;
        void main() {
          vec4 clip = uViewProjection * vec4(aPosition, 1.0);
          gl_Position = clip;
          float depthScale = clamp(1.7 / max(0.45, clip.w), 0.55, 3.2);
          gl_PointSize = clamp(aSize * uPixelRatio * depthScale, 2.0, 44.0);
          vColor = aColor;
        }
      `,
      `
        precision mediump float;
        varying vec4 vColor;
        void main() {
          vec2 coord = gl_PointCoord * 2.0 - 1.0;
          float dist = dot(coord, coord);
          if (dist > 1.0) discard;
          float alpha = vColor.a * smoothstep(1.0, 0.12, dist);
          gl_FragColor = vec4(vColor.rgb, alpha);
        }
      `,
    );
    const lineProgram = createProgram(
      gl,
      `
        attribute vec3 aPosition;
        attribute vec4 aColor;
        uniform mat4 uViewProjection;
        varying vec4 vColor;
        void main() {
          gl_Position = uViewProjection * vec4(aPosition, 1.0);
          vColor = aColor;
        }
      `,
      `
        precision mediump float;
        varying vec4 vColor;
        void main() {
          gl_FragColor = vColor;
        }
      `,
    );
    const renderer = {
      gl,
      pointProgram,
      lineProgram,
      pointLocations: {
        position: gl.getAttribLocation(pointProgram, 'aPosition'),
        color: gl.getAttribLocation(pointProgram, 'aColor'),
        size: gl.getAttribLocation(pointProgram, 'aSize'),
        viewProjection: gl.getUniformLocation(pointProgram, 'uViewProjection'),
        pixelRatio: gl.getUniformLocation(pointProgram, 'uPixelRatio'),
      },
      lineLocations: {
        position: gl.getAttribLocation(lineProgram, 'aPosition'),
        color: gl.getAttribLocation(lineProgram, 'aColor'),
        viewProjection: gl.getUniformLocation(lineProgram, 'uViewProjection'),
      },
      positionBuffer: gl.createBuffer(),
      colorBuffer: gl.createBuffer(),
      sizeBuffer: gl.createBuffer(),
      linePositionBuffer: gl.createBuffer(),
      lineColorBuffer: gl.createBuffer(),
      lineCount: 0,
    };
    viewerScene.renderer = renderer;
    const lines = createSceneLines();
    gl.bindBuffer(gl.ARRAY_BUFFER, renderer.linePositionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, lines.positions, gl.STATIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER, renderer.lineColorBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, lines.colors, gl.STATIC_DRAW);
    renderer.lineCount = lines.count;
    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    uploadPointData();
    renderViewerMeta({ pointCount: viewerScene.pointCount });
    return renderer;
  } catch (error) {
    viewerScene.webglFailed = true;
    setViewerStatus('webgl error', 'fail');
    els.viewerMeta.replaceChildren(row('Error', error.message));
    return null;
  }
}

function uploadPointData() {
  const renderer = viewerScene.renderer;
  const data = viewerScene.pointData;
  if (!renderer || !data || viewerScene.uploadedArtifactUrl === viewerScene.artifactUrl) return;
  const { gl } = renderer;
  gl.bindBuffer(gl.ARRAY_BUFFER, renderer.positionBuffer);
  gl.bufferData(gl.ARRAY_BUFFER, data.positions, gl.STATIC_DRAW);
  gl.bindBuffer(gl.ARRAY_BUFFER, renderer.colorBuffer);
  gl.bufferData(gl.ARRAY_BUFFER, data.colors, gl.STATIC_DRAW);
  gl.bindBuffer(gl.ARRAY_BUFFER, renderer.sizeBuffer);
  gl.bufferData(gl.ARRAY_BUFFER, data.sizes, gl.STATIC_DRAW);
  viewerScene.uploadedArtifactUrl = viewerScene.artifactUrl;
}

function mat4Perspective(fovyRadians, aspect, near, far) {
  const f = 1 / Math.tan(fovyRadians / 2);
  const out = new Float32Array(16);
  out[0] = f / aspect;
  out[5] = f;
  out[10] = (far + near) / (near - far);
  out[11] = -1;
  out[14] = (2 * far * near) / (near - far);
  return out;
}

function vec3Normalize(vector) {
  const length = Math.hypot(vector[0], vector[1], vector[2]) || 1;
  return [vector[0] / length, vector[1] / length, vector[2] / length];
}

function vec3Cross(a, b) {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
}

function vec3Dot(a, b) {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

function mat4LookAt(eye, center, up) {
  const z = vec3Normalize([eye[0] - center[0], eye[1] - center[1], eye[2] - center[2]]);
  const x = vec3Normalize(vec3Cross(up, z));
  const y = vec3Cross(z, x);
  const out = new Float32Array(16);
  out[0] = x[0];
  out[1] = y[0];
  out[2] = z[0];
  out[3] = 0;
  out[4] = x[1];
  out[5] = y[1];
  out[6] = z[1];
  out[7] = 0;
  out[8] = x[2];
  out[9] = y[2];
  out[10] = z[2];
  out[11] = 0;
  out[12] = -vec3Dot(x, eye);
  out[13] = -vec3Dot(y, eye);
  out[14] = -vec3Dot(z, eye);
  out[15] = 1;
  return out;
}

function mat4Multiply(a, b) {
  const out = new Float32Array(16);
  for (let column = 0; column < 4; column += 1) {
    for (let rowIndex = 0; rowIndex < 4; rowIndex += 1) {
      out[column * 4 + rowIndex] =
        a[0 * 4 + rowIndex] * b[column * 4 + 0]
        + a[1 * 4 + rowIndex] * b[column * 4 + 1]
        + a[2 * 4 + rowIndex] * b[column * 4 + 2]
        + a[3 * 4 + rowIndex] * b[column * 4 + 3];
    }
  }
  return out;
}

function viewProjectionMatrix(width, height) {
  const aspect = width / Math.max(1, height);
  const distance = 2.15 / viewerScene.zoom;
  const cosPitch = Math.cos(viewerScene.rotationX);
  const target = [viewerScene.panX, viewerScene.panY, 0];
  const eye = [
    target[0] + Math.sin(viewerScene.rotationY) * cosPitch * distance,
    target[1] + Math.sin(viewerScene.rotationX) * distance,
    target[2] + Math.cos(viewerScene.rotationY) * cosPitch * distance,
  ];
  const view = mat4LookAt(eye, target, [0, 1, 0]);
  const projection = mat4Perspective(Math.PI / 4.2, aspect, 0.03, 12);
  return mat4Multiply(projection, view);
}

function bindAttribute(gl, buffer, location, size) {
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.enableVertexAttribArray(location);
  gl.vertexAttribPointer(location, size, gl.FLOAT, false, 0, 0);
}

function drawPreviewFrame() {
  if (viewerScene.mode !== 'debug') {
    requestAnimationFrame(drawPreviewFrame);
    return;
  }
  const renderer = initWebGLScene();
  const { width, height, scale } = resizeCanvasToDisplaySize(els.canvas);
  if (!renderer) {
    requestAnimationFrame(drawPreviewFrame);
    return;
  }

  const { gl } = renderer;
  const viewProjection = viewProjectionMatrix(width, height);
  gl.viewport(0, 0, width, height);
  gl.clearColor(0.08, 0.09, 0.105, 1);
  gl.clearDepth(1);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

  gl.useProgram(renderer.lineProgram);
  gl.uniformMatrix4fv(renderer.lineLocations.viewProjection, false, viewProjection);
  bindAttribute(gl, renderer.linePositionBuffer, renderer.lineLocations.position, 3);
  bindAttribute(gl, renderer.lineColorBuffer, renderer.lineLocations.color, 4);
  gl.lineWidth(1);
  gl.drawArrays(gl.LINES, 0, renderer.lineCount);

  if (viewerScene.pointData?.count) {
    uploadPointData();
    gl.useProgram(renderer.pointProgram);
    gl.uniformMatrix4fv(renderer.pointLocations.viewProjection, false, viewProjection);
    gl.uniform1f(renderer.pointLocations.pixelRatio, scale);
    bindAttribute(gl, renderer.positionBuffer, renderer.pointLocations.position, 3);
    bindAttribute(gl, renderer.colorBuffer, renderer.pointLocations.color, 4);
    bindAttribute(gl, renderer.sizeBuffer, renderer.pointLocations.size, 1);
    gl.drawArrays(gl.POINTS, 0, viewerScene.pointData.count);
  }

  requestAnimationFrame(drawPreviewFrame);
}

function resetViewer() {
  viewerScene.rotationX = -0.28;
  viewerScene.rotationY = 0.62;
  viewerScene.panX = 0;
  viewerScene.panY = 0;
  viewerScene.zoom = 1.05;
}

function panViewer(deltaX, deltaY) {
  const step = 0.09 / viewerScene.zoom;
  viewerScene.panX += deltaX * step;
  viewerScene.panY += deltaY * step;
}

function orbitViewer(deltaX, deltaY) {
  viewerScene.rotationY += deltaX * 0.16;
  viewerScene.rotationX = clamp(viewerScene.rotationX + deltaY * 0.16, -1.4, 1.4);
}

function zoomViewer(factor) {
  viewerScene.zoom = clamp(viewerScene.zoom * factor, 0.35, 5);
}

function setViewerMode(mode) {
  viewerScene.mode = mode;
  const isSpark = mode === 'spark';
  els.sparkViewport.hidden = !isSpark;
  els.canvas.hidden = isSpark;
  els.viewerModeSparkButton.classList.toggle('active', isSpark);
  els.viewerModeDebugButton.classList.toggle('active', !isSpark);
  els.viewerModeSparkButton.setAttribute('aria-pressed', String(isSpark));
  els.viewerModeDebugButton.setAttribute('aria-pressed', String(!isSpark));
  if (isSpark) loadSparkArtifact();
  renderViewerMeta({ pointCount: viewerScene.pointCount });
}

function panActiveViewer(deltaX, deltaY) {
  if (viewerScene.mode === 'spark' && viewerScene.sparkController && !viewerScene.sparkFailed) {
    viewerScene.sparkController.pan(deltaX, deltaY);
    return;
  }
  panViewer(deltaX, deltaY);
}

function orbitActiveViewer(deltaX, deltaY) {
  if (viewerScene.mode === 'spark' && viewerScene.sparkController && !viewerScene.sparkFailed) {
    viewerScene.sparkController.orbit(deltaX, deltaY);
    return;
  }
  orbitViewer(deltaX, deltaY);
}

function zoomActiveViewer(factor) {
  if (viewerScene.mode === 'spark' && viewerScene.sparkController && !viewerScene.sparkFailed) {
    viewerScene.sparkController.zoom(factor);
    return;
  }
  zoomViewer(factor);
}

function resetActiveViewer() {
  if (viewerScene.mode === 'spark' && viewerScene.sparkController && !viewerScene.sparkFailed) {
    viewerScene.sparkController.reset();
    return;
  }
  resetViewer();
}

function stepReferenceCamera(delta) {
  if (viewerScene.mode !== 'spark' || !viewerScene.sparkController || viewerScene.sparkFailed) return;
  const result = delta < 0
    ? viewerScene.sparkController.previousCameraView()
    : viewerScene.sparkController.nextCameraView();
  viewerScene.cameraViewCount = result?.viewCount ?? viewerScene.cameraViewCount;
  viewerScene.activeCameraView = result?.activeView ?? viewerScene.activeCameraView;
  renderViewerMeta({ pointCount: viewerScene.pointCount, activeCameraView: viewerScene.activeCameraView });
}

els.canvas.addEventListener('contextmenu', (event) => event.preventDefault());
els.canvas.addEventListener('pointerdown', (event) => {
  viewerScene.dragging = true;
  viewerScene.panning = event.shiftKey || event.button === 1 || event.button === 2;
  viewerScene.lastX = event.clientX;
  viewerScene.lastY = event.clientY;
  els.canvas.setPointerCapture(event.pointerId);
});
els.canvas.addEventListener('pointermove', (event) => {
  if (!viewerScene.dragging) return;
  const dx = event.clientX - viewerScene.lastX;
  const dy = event.clientY - viewerScene.lastY;
  if (viewerScene.panning || event.shiftKey) {
    const panScale = 0.0018 / viewerScene.zoom;
    viewerScene.panX -= dx * panScale;
    viewerScene.panY += dy * panScale;
  } else {
    viewerScene.rotationY += dx * 0.008;
    viewerScene.rotationX = clamp(viewerScene.rotationX + dy * 0.008, -1.4, 1.4);
  }
  viewerScene.lastX = event.clientX;
  viewerScene.lastY = event.clientY;
});
els.canvas.addEventListener('pointerup', (event) => {
  viewerScene.dragging = false;
  viewerScene.panning = false;
  els.canvas.releasePointerCapture(event.pointerId);
});
els.canvas.addEventListener('wheel', (event) => {
  event.preventDefault();
  zoomViewer(event.deltaY > 0 ? 0.9 : 1.1);
}, { passive: false });
els.viewerPanLeftButton.addEventListener('click', () => panActiveViewer(-1, 0));
els.viewerPanRightButton.addEventListener('click', () => panActiveViewer(1, 0));
els.viewerPanUpButton.addEventListener('click', () => panActiveViewer(0, 1));
els.viewerPanDownButton.addEventListener('click', () => panActiveViewer(0, -1));
els.viewerOrbitLeftButton.addEventListener('click', () => orbitActiveViewer(-1, 0));
els.viewerOrbitRightButton.addEventListener('click', () => orbitActiveViewer(1, 0));
els.viewerOrbitUpButton.addEventListener('click', () => orbitActiveViewer(0, -1));
els.viewerOrbitDownButton.addEventListener('click', () => orbitActiveViewer(0, 1));
els.viewerResetButton.addEventListener('click', resetActiveViewer);
els.viewerCameraPrevButton.addEventListener('click', () => stepReferenceCamera(-1));
els.viewerCameraNextButton.addEventListener('click', () => stepReferenceCamera(1));
els.viewerZoomOutButton.addEventListener('click', () => {
  zoomActiveViewer(0.86);
});
els.viewerZoomInButton.addEventListener('click', () => {
  zoomActiveViewer(1.16);
});
els.viewerModeSparkButton.addEventListener('click', () => setViewerMode('spark'));
els.viewerModeDebugButton.addEventListener('click', () => setViewerMode('debug'));

els.captureSelect.addEventListener('change', () => {
  captureSelectionTouched = true;
  els.acceptCaptureWarning.checked = false;
  els.importStatus.textContent = '';
  renderCaptureMeta();
});
els.videoFileInput.addEventListener('change', updateImportControls);
els.acceptCaptureWarning.addEventListener('change', updateImportControls);
els.importVideoButton.addEventListener('click', importVideo);
els.planJobButton.addEventListener('click', createJob);
els.refreshButton.addEventListener('click', loadState);

requestAnimationFrame(drawPreviewFrame);
const bootPromise = loadState().catch((error) => {
  els.statusStrip.replaceChildren(pill('server error', 'fail'));
  els.jobBox.replaceChildren();
  const message = document.createElement('div');
  message.className = 'error-text';
  message.textContent = error.message;
  els.jobBox.append(message);
});

if (new URLSearchParams(window.location.search).has('waitForViewer')) {
  await bootPromise;
  await viewerReadyPromise;
  document.documentElement.dataset.viewerReady = 'true';
}
