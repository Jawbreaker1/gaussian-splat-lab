const els = {
  machineLabel: document.querySelector('#machineLabel'),
  statusStrip: document.querySelector('#statusStrip'),
  captureSelect: document.querySelector('#captureSelect'),
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
  blockedCount: document.querySelector('#blockedCount'),
  complianceGrid: document.querySelector('#complianceGrid'),
  viewerStatusPill: document.querySelector('#viewerStatusPill'),
  viewerResetButton: document.querySelector('#viewerResetButton'),
  viewerZoomOutButton: document.querySelector('#viewerZoomOutButton'),
  viewerZoomInButton: document.querySelector('#viewerZoomInButton'),
  viewerMeta: document.querySelector('#viewerMeta'),
  canvas: document.querySelector('#splatCanvas'),
};

let state = null;
let activeJob = null;
let runningStage = null;
let importingVideo = false;
let viewerLoadToken = 0;

const viewerScene = {
  points: [],
  artifactUrl: null,
  status: 'pending',
  rotationX: -0.28,
  rotationY: 0.62,
  zoom: 1.05,
  dragging: false,
  lastX: 0,
  lastY: 0,
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

function pill(text, type = 'neutral') {
  const span = document.createElement('span');
  span.className = `pill ${type}`;
  span.textContent = text;
  return span;
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
  els.captureSelect.replaceChildren();
  for (const capture of captures) {
    const option = document.createElement('option');
    option.value = capture.id;
    option.textContent = capture.displayName || capture.id;
    els.captureSelect.append(option);
  }
  els.planJobButton.disabled = captures.length === 0;
  renderCaptureMeta();
}

function renderCaptureMeta() {
  const capture = selectedCapture();
  els.captureMeta.replaceChildren();
  if (!capture) {
    els.captureMeta.append(row('Status', 'No capture'));
    return;
  }

  const readiness = selectedCaptureReadiness();
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
  item.className = 'stage-item';

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

  const status = pill(stage?.status ?? 'gate', stage?.status ?? 'neutral');
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

function renderStages() {
  const gates = state?.gates ?? [];
  const jobStages = activeJob?.stages ?? [];
  const preflight = gates.filter((gate) => stageGroup(gate) === 'preflight');
  const pipeline = gates.filter((gate) => stageGroup(gate) !== 'preflight');
  els.preflightList.replaceChildren();
  els.pipelineList.replaceChildren();
  els.gateCount.textContent = `${preflight.length} preflight / ${pipeline.length} pipeline`;

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
  loadViewerArtifact();
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

function renderViewerMeta(extra = null) {
  els.viewerMeta.replaceChildren();
  const viewer = state?.viewerArtifact;
  const manifest = viewer?.manifest;
  const artifact = manifest?.artifact;
  if (!artifact) {
    setViewerStatus('pending', 'neutral');
    els.viewerMeta.append(row('Artifact', 'No packaged splat'));
    return;
  }

  const ply = artifact.ply ?? {};
  const status = viewer.viewerStatus ?? viewer.packagingStatus ?? 'packaged';
  const statusType = status === 'pass' ? 'pass' : status === 'warning' ? 'warning' : 'neutral';
  setViewerStatus(status, statusType);
  els.viewerMeta.append(
    row('Artifact', artifact.format ?? 'ply'),
    row('Points', String(extra?.pointCount ?? ply.vertexCount ?? '-')),
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
    viewerScene.points = [];
    viewerScene.artifactUrl = null;
    renderViewerMeta();
    return;
  }
  if (viewerScene.artifactUrl === url && viewerScene.points.length > 0) {
    renderViewerMeta({ pointCount: viewerScene.points.length });
    return;
  }

  const token = ++viewerLoadToken;
  setViewerStatus('loading', 'neutral');
  try {
    const response = await fetch(url, { cache: 'no-store' });
    if (!response.ok) throw new Error(`artifact ${response.status}`);
    const parsed = parseBinaryPly(await response.arrayBuffer());
    if (token !== viewerLoadToken) return;
    viewerScene.points = normalizePoints(parsed.points);
    viewerScene.artifactUrl = url;
    renderViewerMeta({ pointCount: parsed.vertexCount });
    setViewerStatus('loaded', 'pass');
  } catch (error) {
    if (token !== viewerLoadToken) return;
    viewerScene.points = [];
    viewerScene.artifactUrl = null;
    setViewerStatus('viewer error', 'fail');
    els.viewerMeta.replaceChildren(row('Error', error.message));
  }
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

function drawPreviewFrame() {
  const canvas = els.canvas;
  const ctx = canvas.getContext('2d');
  const { width, height } = resizeCanvasToDisplaySize(canvas);
  ctx.clearRect(0, 0, width, height);
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, '#17191d');
  gradient.addColorStop(1, '#24282d');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  const points = viewerScene.points;
  if (!points.length) {
    ctx.fillStyle = 'rgba(255,255,255,0.72)';
    ctx.font = `${Math.max(12, Math.round(width / 42))}px Inter, system-ui, sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillText('No splat artifact', width / 2, height / 2);
    requestAnimationFrame(drawPreviewFrame);
    return;
  }

  const cosY = Math.cos(viewerScene.rotationY);
  const sinY = Math.sin(viewerScene.rotationY);
  const cosX = Math.cos(viewerScene.rotationX);
  const sinX = Math.sin(viewerScene.rotationX);
  const scale = Math.min(width, height) * 1.55 * viewerScene.zoom;
  const projected = points.map((point) => {
    const x1 = point.x * cosY - point.z * sinY;
    const z1 = point.x * sinY + point.z * cosY;
    const y1 = point.y * cosX - z1 * sinX;
    const z2 = point.y * sinX + z1 * cosX;
    const perspective = 1 / (1.55 + z2 * 0.42);
    return {
      x: width / 2 + x1 * scale * perspective,
      y: height / 2 - y1 * scale * perspective,
      depth: z2,
      radius: clamp(1.1 + point.size * scale * 0.05 * perspective, 1.1, 4.8),
      point,
    };
  }).sort((a, b) => a.depth - b.depth);

  for (const item of projected) {
    const { point } = item;
    const red = Math.round(point.r * 255);
    const green = Math.round(point.g * 255);
    const blue = Math.round(point.b * 255);
    ctx.fillStyle = `rgba(${red},${green},${blue},${point.alpha})`;
    ctx.beginPath();
    ctx.arc(item.x, item.y, item.radius, 0, Math.PI * 2);
    ctx.fill();
  }

  requestAnimationFrame(drawPreviewFrame);
}

function resetViewer() {
  viewerScene.rotationX = -0.28;
  viewerScene.rotationY = 0.62;
  viewerScene.zoom = 1.05;
}

els.canvas.addEventListener('pointerdown', (event) => {
  viewerScene.dragging = true;
  viewerScene.lastX = event.clientX;
  viewerScene.lastY = event.clientY;
  els.canvas.setPointerCapture(event.pointerId);
});
els.canvas.addEventListener('pointermove', (event) => {
  if (!viewerScene.dragging) return;
  const dx = event.clientX - viewerScene.lastX;
  const dy = event.clientY - viewerScene.lastY;
  viewerScene.rotationY += dx * 0.008;
  viewerScene.rotationX = clamp(viewerScene.rotationX + dy * 0.008, -1.4, 1.4);
  viewerScene.lastX = event.clientX;
  viewerScene.lastY = event.clientY;
});
els.canvas.addEventListener('pointerup', (event) => {
  viewerScene.dragging = false;
  els.canvas.releasePointerCapture(event.pointerId);
});
els.canvas.addEventListener('wheel', (event) => {
  event.preventDefault();
  viewerScene.zoom = clamp(viewerScene.zoom * (event.deltaY > 0 ? 0.9 : 1.1), 0.35, 5);
}, { passive: false });
els.viewerResetButton.addEventListener('click', resetViewer);
els.viewerZoomOutButton.addEventListener('click', () => {
  viewerScene.zoom = clamp(viewerScene.zoom * 0.86, 0.35, 5);
});
els.viewerZoomInButton.addEventListener('click', () => {
  viewerScene.zoom = clamp(viewerScene.zoom * 1.16, 0.35, 5);
});

els.captureSelect.addEventListener('change', () => {
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
loadState().catch((error) => {
  els.statusStrip.replaceChildren(pill('server error', 'fail'));
  els.jobBox.replaceChildren();
  const message = document.createElement('div');
  message.className = 'error-text';
  message.textContent = error.message;
  els.jobBox.append(message);
});
