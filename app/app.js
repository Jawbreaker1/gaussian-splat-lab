const els = {
  machineLabel: document.querySelector('#machineLabel'),
  statusStrip: document.querySelector('#statusStrip'),
  captureSelect: document.querySelector('#captureSelect'),
  captureMeta: document.querySelector('#captureMeta'),
  planJobButton: document.querySelector('#planJobButton'),
  refreshButton: document.querySelector('#refreshButton'),
  jobBox: document.querySelector('#jobBox'),
  stageList: document.querySelector('#stageList'),
  gateCount: document.querySelector('#gateCount'),
  blockedCount: document.querySelector('#blockedCount'),
  complianceGrid: document.querySelector('#complianceGrid'),
  canvas: document.querySelector('#splatCanvas'),
};

let state = null;
let activeJob = null;
let runningStage = null;

const runnableStages = new Set(['framework_license', 'environment', 'intake', 'frame_sampling', 'sfm', 'splat_training', 'packaging', 'viewer', 'quality_report']);
const heavyStages = new Set(['sfm', 'splat_training', 'viewer']);

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

function renderStages() {
  const gates = state?.gates ?? [];
  const jobStages = activeJob?.stages ?? [];
  els.stageList.replaceChildren();
  els.gateCount.textContent = `${gates.length} gates`;

  gates.forEach((gate, index) => {
    const stage = jobStages.find((item) => item.id === gate.id);
    const item = document.createElement('article');
    item.className = 'stage-item';

    const number = document.createElement('div');
    number.className = 'stage-index';
    number.textContent = String(index);

    const body = document.createElement('div');
    const title = document.createElement('div');
    title.className = 'stage-title';
    title.textContent = gate.id.replaceAll('_', ' ');
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
      action.title = heavyStages.has(gate.id) ? `${gate.id.replaceAll('_', ' ')} requires explicit heavy-workload approval in CLI` : `Run ${gate.id.replaceAll('_', ' ')}`;
      action.addEventListener('click', () => runStage(gate.id));
      item.append(number, body, status, action);
    } else {
      item.append(number, body, status);
    }
    els.stageList.append(item);
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
}

async function loadState() {
  const response = await fetch('/api/state');
  if (!response.ok) throw new Error(`state ${response.status}`);
  state = await response.json();
  activeJob = state.latestJob ?? null;
  renderAll();
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
    renderStages();
    renderJob();
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
    renderStages();
    renderJob();
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


function drawPreview() {
  const canvas = els.canvas;
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const points = Array.from({ length: 170 }, (_, index) => {
    const angle = index * 0.37;
    const radius = 22 + (index % 31) * 4.2;
    return {
      angle,
      radius,
      size: 2 + (index % 7) * 0.45,
      hue: index % 3,
      lift: Math.sin(index * 1.7) * 34,
    };
  });

  function frame(time) {
    ctx.clearRect(0, 0, width, height);
    const gradient = ctx.createLinearGradient(0, 0, width, height);
    gradient.addColorStop(0, '#20242a');
    gradient.addColorStop(1, '#111316');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    const t = time * 0.00022;
    for (const point of points) {
      const spin = point.angle + t;
      const depth = 0.62 + 0.38 * Math.cos(spin);
      const x = width / 2 + Math.cos(spin) * point.radius * 1.55;
      const y = height / 2 + Math.sin(spin * 1.35) * point.radius * 0.72 + point.lift * depth;
      const alpha = 0.36 + depth * 0.5;
      const color = point.hue === 0 ? '15,118,110' : point.hue === 1 ? '161,92,7' : '109,91,208';
      const r = point.size * (0.8 + depth * 1.3);
      const blob = ctx.createRadialGradient(x, y, 0, x, y, r * 4.2);
      blob.addColorStop(0, `rgba(${color},${alpha})`);
      blob.addColorStop(1, `rgba(${color},0)`);
      ctx.fillStyle = blob;
      ctx.beginPath();
      ctx.arc(x, y, r * 4.2, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.strokeStyle = 'rgba(255,255,255,0.12)';
    ctx.strokeRect(18, 18, width - 36, height - 36);
    requestAnimationFrame(frame);
  }

  requestAnimationFrame(frame);
}

els.captureSelect.addEventListener('change', renderCaptureMeta);
els.planJobButton.addEventListener('click', createJob);
els.refreshButton.addEventListener('click', loadState);

loadState().catch((error) => {
  els.statusStrip.replaceChildren(pill('server error', 'fail'));
  els.jobBox.replaceChildren();
  const message = document.createElement('div');
  message.className = 'error-text';
  message.textContent = error.message;
  els.jobBox.append(message);
});
drawPreview();
