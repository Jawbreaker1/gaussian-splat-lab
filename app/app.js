const els = {
  machineLabel: document.querySelector('#machineLabel'),
  captureSelect: document.querySelector('#captureSelect'),
  captureSummary: document.querySelector('#captureSummary'),
  captureMeta: document.querySelector('#captureMeta'),
  videoFileInput: document.querySelector('#videoFileInput'),
  acceptCaptureWarning: document.querySelector('#acceptCaptureWarning'),
  acceptCaptureWarningRow: document.querySelector('#acceptCaptureWarningRow'),
  importVideoButton: document.querySelector('#importVideoButton'),
  importStatus: document.querySelector('#importStatus'),
  planJobButton: document.querySelector('#planJobButton'),
  wizardCaptureName: document.querySelector('#wizardCaptureName'),
  wizardSceneKind: document.querySelector('#wizardSceneKind'),
  wizardQualityPreset: document.querySelector('#wizardQualityPreset'),
  wizardStrategyEstimate: document.querySelector('#wizardStrategyEstimate'),
  wizardSelfCaptured: document.querySelector('#wizardSelfCaptured'),
  generatePipelineButton: document.querySelector('#generatePipelineButton'),
  wizardStatus: document.querySelector('#wizardStatus'),
  queueSummary: document.querySelector('#queueSummary'),
  queueWorkerStatus: document.querySelector('#queueWorkerStatus'),
  queueList: document.querySelector('#queueList'),
  renderModal: document.querySelector('#renderModal'),
  renderModalTitle: document.querySelector('#renderModalTitle'),
  renderModalSubtitle: document.querySelector('#renderModalSubtitle'),
  renderModalMeta: document.querySelector('#renderModalMeta'),
  renderModalStage: document.querySelector('#renderModalStage'),
  renderModalEta: document.querySelector('#renderModalEta'),
  renderModalProgressBar: document.querySelector('#renderModalProgressBar'),
  renderModalNote: document.querySelector('#renderModalNote'),
  renderCancelButton: document.querySelector('#renderCancelButton'),
  renderCancelAfterStageButton: document.querySelector('#renderCancelAfterStageButton'),
  renderModalMinimizeButton: document.querySelector('#renderModalMinimizeButton'),
  renderModalRestoreButton: document.querySelector('#renderModalRestoreButton'),
  jobBox: document.querySelector('#jobBox'),
  preflightList: document.querySelector('#preflightList'),
  pipelineList: document.querySelector('#pipelineList'),
  gateCount: document.querySelector('#gateCount'),
  pipelineProgressText: document.querySelector('#pipelineProgressText'),
  pipelineCurrentStage: document.querySelector('#pipelineCurrentStage'),
  pipelineEtaText: document.querySelector('#pipelineEtaText'),
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
  exportSplatLink: document.querySelector('#exportSplatLink'),
  exportManifestLink: document.querySelector('#exportManifestLink'),
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
  viewerNavWalkButton: document.querySelector('#viewerNavWalkButton'),
  viewerNavOrbitButton: document.querySelector('#viewerNavOrbitButton'),
  viewerSensitivityInput: document.querySelector('#viewerSensitivityInput'),
  viewerSensitivityValue: document.querySelector('#viewerSensitivityValue'),
  sparkViewport: document.querySelector('#sparkViewport'),
  sparkCanvas: document.querySelector('#sparkCanvas'),
  sparkOverlay: document.querySelector('#sparkOverlay'),
  debugViewport: document.querySelector('#debugViewport'),
  debugOverlay: document.querySelector('#debugOverlay'),
  canvas: document.querySelector('#splatCanvas'),
};

let state = null;
let activeJob = null;
let runningStage = null;
let autoRun = null;
let autoRunTimer = null;
let queueState = null;
let queuePollingTimer = null;
let queueActionBusy = false;
let renderModalMinimized = false;
let lastQueueSignature = '';
let wizardBusy = false;
let latestJobProgress = null;
let progressPolling = false;
let runningStageStartedAt = null;
let importingVideo = false;
let viewerLoadToken = 0;
let viewerReadyResolved = false;
let resolveViewerReady = null;
let captureSelectionTouched = false;
const debugPointBudget = 320000;
const defaultNavigationSensitivity = 0.55;
const viewerReadyPromise = new Promise((resolve) => {
  resolveViewerReady = resolve;
});

const viewerScene = {
  mode: 'spark',
  pointData: null,
  pointCount: 0,
  debugPointCount: 0,
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
  sparkNavigationMode: 'walk',
  navigationSensitivity: defaultNavigationSensitivity,
  cameraViewCount: 0,
  activeCameraView: null,
  uploadedArtifactUrl: null,
  webglFailed: false,
  debugLoadLabel: '',
  debugLoadType: 'neutral',
};

if (typeof window !== 'undefined') {
  window.__gslabViewerDebug = {
    getSparkNavigationState: () => viewerScene.sparkController?.getNavigationState?.() ?? null,
    lookPixels: (deltaX, deltaY) => viewerScene.sparkController?.lookPixels?.(deltaX, deltaY),
    pan: (deltaX, deltaY) => viewerScene.sparkController?.pan?.(deltaX, deltaY),
    zoom: (factor) => viewerScene.sparkController?.zoom?.(factor),
    getUiState: () => ({
      mode: viewerScene.mode,
      sparkNavigationMode: viewerScene.sparkNavigationMode,
      navigationSensitivity: viewerScene.navigationSensitivity,
      sparkFailed: viewerScene.sparkFailed,
      pointCount: viewerScene.pointCount,
      debugPointCount: viewerScene.debugPointCount,
      cameraViewCount: viewerScene.cameraViewCount,
      activeCameraView: viewerScene.activeCameraView?.imageName ?? null,
    }),
  };
}

const runnableStages = new Set(['framework_license', 'environment', 'intake', 'frame_sampling', 'sfm', 'splat_training', 'packaging', 'viewer', 'quality_report']);
const heavyStages = new Set(['sfm', 'splat_training', 'viewer']);
const automatedStageOrder = ['framework_license', 'environment', 'intake', 'frame_sampling', 'sfm', 'splat_training', 'packaging', 'viewer', 'quality_report'];
const defaultStageEstimates = {
  framework_license: 8,
  environment: 15,
  intake: 8,
  frame_sampling: 90,
  sfm: 12 * 60,
  packaging: 20,
  viewer: 35,
  quality_report: 10,
};
const trainingProfileEstimates = {
  smoke: 60,
  baseline: 4 * 60,
  quality_probe: 12 * 60,
  rtx_reference: 25 * 60,
  rtx_high_quality: 55 * 60,
  rtx_ultra_quality: 2 * 60 * 60,
  rtx_stable_quality: 3 * 60 * 60,
  rtx_ceiling_quality: 3 * 60 * 60,
  rtx_max_quality: 5 * 60 * 60,
  splatfacto_preview: 20 * 60,
  splatfacto_reference: 60 * 60,
  splatfacto_big_quality: 2 * 60 * 60,
  splatfacto_ceiling: 3 * 60 * 60,
};
const qualityPresetLabels = {
  quality_probe: 'Quick preview',
  rtx_high_quality: 'High quality',
  rtx_ultra_quality: 'Ultra quality',
  rtx_stable_quality: 'Max stable',
  rtx_max_quality: 'Max stress',
  splatfacto_preview: 'Splatfacto preview',
  splatfacto_reference: 'Standard 3DGS',
  splatfacto_big_quality: 'Best quality',
  splatfacto_ceiling: 'Ceiling test',
};
const fallbackSceneProfiles = {
  room: {
    label: 'Interior room',
    description: 'Balanced room-scale capture with stronger sequential matching on lighter profiles.',
    targetFpsMultiplier: 1,
    maxFramesMultiplier: 1,
    estimateMultiplier: 1,
  },
  outdoor: {
    label: 'Outdoor environment',
    description: 'Larger environment capture with more frames and a wider COLMAP matching window.',
    targetFpsMultiplier: 1.2,
    maxFramesMultiplier: 1.3,
    estimateMultiplier: 1.3,
  },
  object: {
    label: 'Object orbit',
    description: 'Object-centric orbit with a smaller frame budget and guided matching.',
    targetFpsMultiplier: 0.8,
    maxFramesMultiplier: 0.75,
    estimateMultiplier: 0.85,
  },
};
const generationStrategyDetails = {
  splatfacto_reference: {
    purpose: 'Full 3DGS scene with balanced runtime.',
    training: 'Splatfacto, 30k iterations',
  },
  splatfacto_big_quality: {
    purpose: 'Recommended when final visual quality matters.',
    training: 'Splatfacto Big, 30k iterations',
  },
  quality_probe: {
    purpose: 'Fast validation of upload, frame sampling and camera solve.',
    training: 'Short local trainer probe',
  },
  splatfacto_ceiling: {
    purpose: 'Lab run for testing the quality ceiling on strong input.',
    training: 'Splatfacto Big, full-resolution path',
  },
};
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
const stageDetails = {
  framework_license: {
    summary: 'Confirms that the runtime frameworks are allowed for the intended use.',
    inside: 'Checks dependency decisions, license notes and commercial-use conditions.',
    output: 'Dependency decision report',
  },
  environment: {
    summary: 'Checks that this workstation can run the local video-to-3DGS pipeline.',
    inside: 'Checks FFmpeg, COLMAP, Python, CUDA/PyTorch and RTX visibility.',
    output: 'Machine readiness report',
  },
  intake: {
    summary: 'Reads the uploaded video and records the source metadata.',
    inside: 'Checks file access, duration, codec, resolution and capture provenance.',
    output: 'Capture metadata',
  },
  frame_sampling: {
    summary: 'Extracts stable still frames from the video for reconstruction.',
    inside: 'Samples frames, writes timestamps, builds hashes/contact sheet and checks blur, contrast, exposure and motion risk.',
    output: 'Frame manifest',
  },
  sfm: {
    summary: 'Solves camera positions so training knows where each frame was captured.',
    inside: 'COLMAP extracts features, matches nearby frames and automatically retries with more robust matching if too few frames register.',
    output: 'Camera solve report',
  },
  splat_training: {
    summary: 'Optimizes the Gaussian splats from the solved cameras and frames.',
    inside: 'Runs the selected trainer, tracks iterations and exports render evidence.',
    output: 'Training report and splat export',
  },
  packaging: {
    summary: 'Turns the training output into files the web viewer and exports can use.',
    inside: 'Copies artifacts, writes hashes, records size/format and prepares gallery metadata.',
    output: 'Viewer artifact manifest',
  },
  viewer: {
    summary: 'Checks that the generated scene can be opened and navigated in the browser.',
    inside: 'Loads the artifact, checks the canvas and validates orbit, pan, zoom and reset.',
    output: 'Viewer validation report',
  },
  quality_report: {
    summary: 'Collects all stage results into one final usability verdict.',
    inside: 'Summarizes pass, warning and failure boundaries for the finished generation.',
    output: 'Quality report',
  },
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

function selectedTrainingProfile() {
  return els.wizardQualityPreset?.value || 'splatfacto_reference';
}

function selectedSceneProfileKey() {
  return els.wizardSceneKind?.value || 'room';
}

function activeQueueItem() {
  return queueState?.active
    ?? queueState?.items?.find((item) => item.status === 'running' || item.status === 'cancel_requested')
    ?? null;
}

function queueHasLiveWork() {
  return Boolean(queueState?.items?.some((item) => ['queued', 'running', 'cancel_requested'].includes(item.status)));
}

function queueItemLabel(item) {
  return item?.displayName || item?.captureId || item?.id || 'Render job';
}

function queueStatusType(status) {
  if (status === 'complete') return 'pass';
  if (status === 'running' || status === 'cancel_requested') return 'warning';
  if (status === 'failed' || status === 'cancelled') return 'fail';
  return 'neutral';
}

function sceneProfileFor(sceneKey = selectedSceneProfileKey()) {
  return state?.sceneProfiles?.[sceneKey] ?? fallbackSceneProfiles[sceneKey] ?? fallbackSceneProfiles.room;
}

function qualityPresetFor(profile = selectedTrainingProfile()) {
  return state?.qualityPresets?.[profile] ?? null;
}

function effectiveCapturePlan(profile = selectedTrainingProfile(), sceneKey = selectedSceneProfileKey()) {
  const quality = qualityPresetFor(profile);
  const scene = sceneProfileFor(sceneKey);
  if (!quality || !scene) return null;
  const fps = Number(quality.targetFps) * Number(scene.targetFpsMultiplier ?? 1);
  const rawMaxFrames = Math.round(Number(quality.maxFrames) * Number(scene.maxFramesMultiplier ?? 1));
  const minFrames = Number.isFinite(Number(scene.minimumMaxFrames)) ? Number(scene.minimumMaxFrames) : null;
  const maxFramesCap = Number.isFinite(Number(scene.maximumMaxFrames)) ? Number(scene.maximumMaxFrames) : null;
  let maxFrames = rawMaxFrames;
  if (minFrames !== null) maxFrames = Math.max(maxFrames, minFrames);
  if (maxFramesCap !== null) maxFrames = Math.min(maxFrames, maxFramesCap);
  const sfm = { ...(quality.sfm ?? {}) };
  for (const [key, value] of Object.entries(scene.sfm ?? {})) {
    if (Number.isInteger(value) && Number.isInteger(sfm[key])) {
      sfm[key] = sceneKey === 'object' ? value : Math.max(sfm[key], value);
    } else {
      sfm[key] = value;
    }
  }
  return {
    targetFps: Math.round(fps * 100) / 100,
    maxFrames,
    sequentialOverlap: sfm.sequentialOverlap,
    featureMaxNumFeatures: sfm.featureMaxNumFeatures,
    guidedMatching: Boolean(sfm.guidedMatching),
  };
}

function formatDuration(seconds) {
  const value = Math.max(0, Math.round(Number(seconds) || 0));
  if (value < 60) return '<1 min';
  const minutes = Math.round(value / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours}h ${rest}m` : `${hours}h`;
}

function sceneEstimateMultiplier(sceneKey = selectedSceneProfileKey()) {
  return Number(sceneProfileFor(sceneKey)?.estimateMultiplier) || 1;
}

function stageEstimateSeconds(stage, profile = selectedTrainingProfile(), sceneKey = selectedSceneProfileKey()) {
  const sceneWeightedStages = new Set(['frame_sampling', 'sfm', 'splat_training']);
  const multiplier = sceneWeightedStages.has(stage) ? sceneEstimateMultiplier(sceneKey) : 1;
  const baseEstimate = stage === 'splat_training'
    ? trainingProfileEstimates[profile] ?? trainingProfileEstimates.quality_probe
    : defaultStageEstimates[stage] ?? 30;
  return baseEstimate * multiplier;
}

function totalEstimateSeconds(profile = selectedTrainingProfile(), sceneKey = selectedSceneProfileKey()) {
  return automatedStageOrder.reduce((total, stage) => total + stageEstimateSeconds(stage, profile, sceneKey), 0);
}

function activeTrainingProfile() {
  return activeQueueItem()?.qualityPreset || autoRun?.trainingProfile || selectedTrainingProfile();
}

function activeSceneProfileKey() {
  return activeQueueItem()?.sceneKind || autoRun?.sceneKind || selectedSceneProfileKey();
}

function activeStageId() {
  return runningStage || autoRun?.currentStage || activeQueueItem()?.currentStage || null;
}

function stageElapsedSeconds(stage) {
  const queueItem = activeQueueItem();
  if (queueItem?.currentStage === stage && queueItem.stageStartedAt) {
    const started = Date.parse(queueItem.stageStartedAt);
    if (Number.isFinite(started)) return Math.max(0, (Date.now() - started) / 1000);
  }
  if (autoRun?.active && autoRun.currentStage === stage && autoRun.stageStartedAt) {
    return Math.max(0, (Date.now() - autoRun.stageStartedAt) / 1000);
  }
  if (runningStage === stage && runningStageStartedAt) {
    return Math.max(0, (Date.now() - runningStageStartedAt) / 1000);
  }
  return 0;
}

function stageProgress(stage, trainingProgress = null) {
  const estimate = stageEstimateSeconds(stage, activeTrainingProfile(), activeSceneProfileKey());
  if (stage === 'splat_training' && trainingProgress?.status === 'running') {
    const elapsed = Number(trainingProgress.elapsedSeconds || stageElapsedSeconds(stage));
    const total = Number(trainingProgress.estimatedTotalSeconds || estimate);
    const percent = clamp(Number(trainingProgress.percent || 0), 0, 99.9);
    return {
      elapsed,
      total,
      remaining: Math.max(0, total - elapsed),
      percent,
      source: trainingProgress.progressSource === 'nerfstudio_log' ? 'trainer log' : 'elapsed time',
      iteration: Number(trainingProgress.iteration || 0),
      iterations: Number(trainingProgress.iterations || 0),
      etaText: trainingProgress.etaText || '',
    };
  }
  const elapsed = stageElapsedSeconds(stage);
  return {
    elapsed,
    total: estimate,
    remaining: Math.max(0, estimate - elapsed),
    percent: clamp((elapsed / Math.max(estimate, 1)) * 100, elapsed ? 2 : 0, 96),
    source: 'elapsed time',
    iteration: 0,
    iterations: 0,
    etaText: '',
  };
}

function stageReportSummary(stage) {
  return latestJobProgress?.reports?.[stage] ?? activeJob?.reportSummaries?.[stage] ?? null;
}

function stageIssueText(stage, summary = stageReportSummary(stage)) {
  const check = summary?.problemCheck;
  if (!check) return '';
  if (stage === 'sfm' && check.id === 'registered_frames') {
    const registered = Number(check.registeredImages ?? 0);
    const total = Number(check.frameCount ?? 0);
    const threshold = Math.round(Number(check.passThreshold ?? 0.7) * 100);
    const frameText = registered && total ? `${registered}/${total} frames registered` : check.summary;
    return `Camera solve failed: ${frameText}. Need about ${threshold}% for a robust 3DGS. Try a slower capture with more overlap, clearer texture and less motion blur.`;
  }
  const label = stageDisplayName({ id: stage });
  return `${label}: ${check.summary || summary.status || 'needs attention'}`;
}

function stageFailureMessage(stage, payload = {}) {
  const summary = payload.reportSummary ?? summarizeInlineReport(payload.report);
  const issue = stageIssueText(stage, summary);
  if (issue) return issue;
  return payload.stderr || payload.stdout || `${stageDisplayName({ id: stage })} failed`;
}

function summarizeInlineReport(report) {
  if (!report || typeof report !== 'object') return null;
  const stage = report.stage && typeof report.stage === 'object' ? report.stage : {};
  const checks = Array.isArray(report.checks) ? report.checks : [];
  const problem = checks.find((check) => ['fail', 'blocked', 'blocked_license', 'blocked_workload', 'setup_gap'].includes(check?.status))
    ?? checks.find((check) => check?.status === 'warning')
    ?? null;
  return {
    status: stage.status,
    generatedAt: stage.generatedAt,
    problemCheck: problem,
  };
}

function estimateRemainingSeconds() {
  if (!autoRun?.active) return totalEstimateSeconds(selectedTrainingProfile(), selectedSceneProfileKey());
  const profile = autoRun.trainingProfile;
  const sceneKey = autoRun.sceneKind || selectedSceneProfileKey();
  const currentIndex = Math.max(0, autoRun.currentIndex ?? 0);
  let remaining = 0;
  for (let index = currentIndex; index < automatedStageOrder.length; index += 1) {
    const stage = automatedStageOrder[index];
    const estimate = stageEstimateSeconds(stage, profile, sceneKey);
    if (index === currentIndex && autoRun.stageStartedAt) {
      const elapsed = (Date.now() - autoRun.stageStartedAt) / 1000;
      remaining += Math.max(15, estimate - elapsed);
    } else {
      remaining += estimate;
    }
  }
  return remaining;
}

function setWizardStatus(text, type = 'neutral') {
  els.wizardStatus.textContent = text;
  els.wizardStatus.dataset.type = type;
}

function updateWizardStrategyEstimate() {
  if (!els.wizardStrategyEstimate) return;
  const profile = selectedTrainingProfile();
  const sceneKey = selectedSceneProfileKey();
  const scene = sceneProfileFor(sceneKey);
  const label = qualityPresetLabels[profile] ?? profile;
  const detail = generationStrategyDetails[profile] ?? {};
  const plan = effectiveCapturePlan(profile, sceneKey);
  const estimate = formatDuration(totalEstimateSeconds(profile, sceneKey));

  const kicker = document.createElement('span');
  kicker.textContent = `${scene.label} profile`;

  const value = document.createElement('strong');
  value.textContent = `${estimate} · ${label}`;

  const description = document.createElement('small');
  const planText = plan
    ? `${plan.targetFps} fps target, up to ${plan.maxFrames} selected keyframes from scored candidates across the full clip, COLMAP overlap ${plan.sequentialOverlap}, ${plan.guidedMatching ? 'guided matching on' : 'guided matching off'}.`
    : '';
  description.textContent = [scene.description, planText, detail.training, detail.purpose].filter(Boolean).join(' ');

  els.wizardStrategyEstimate.replaceChildren(kicker, value, description);
}

function updateWizardControls() {
  updateWizardStrategyEstimate();
  const file = els.videoFileInput.files?.[0] ?? null;
  const hasName = Boolean(els.wizardCaptureName.value.trim());
  const hasRights = els.wizardSelfCaptured.checked;
  const busy = Boolean(wizardBusy);
  els.generatePipelineButton.disabled = busy || !file || !hasName || !hasRights;
  els.generatePipelineButton.textContent = busy ? 'Adding' : 'Add to Queue';
  if (!busy) {
    if (!file) {
      setWizardStatus('No video selected.');
    } else if (!hasRights) {
      setWizardStatus('Confirm that you have rights to process this video.', 'fail');
    } else if (!hasName) {
      setWizardStatus('Name the scene before generation.');
    } else {
      const profile = selectedTrainingProfile();
      const scene = sceneProfileFor(selectedSceneProfileKey());
      const label = qualityPresetLabels[profile] ?? profile;
      setWizardStatus(`Ready to generate ${scene.label} with ${label}. Estimated full run ${formatDuration(totalEstimateSeconds(profile, selectedSceneProfileKey()))}.`);
    }
  }
  updateImportControls();
}

function handleVideoFileChange() {
  const file = els.videoFileInput.files?.[0] ?? null;
  if (file && !els.wizardCaptureName.value.trim()) {
    els.wizardCaptureName.value = file.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ');
  }
  updateWizardControls();
}

function updateImportControls() {
  const capture = selectedCapture();
  const file = els.videoFileInput.files?.[0] ?? null;
  const licenseStatus = selectedLicenseCheck()?.status;
  const needsWarningAcceptance = licenseStatus === 'warning';
  const running = Boolean(autoRun?.active) || Boolean(activeQueueItem());
  els.acceptCaptureWarningRow.hidden = !needsWarningAcceptance;
  els.importVideoButton.disabled = running || !capture || !file || importingVideo || (needsWarningAcceptance && !els.acceptCaptureWarning.checked);
  els.importVideoButton.textContent = importingVideo ? 'Importing' : 'Import video';
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
  const current = activeStageId() === gate.id;
  item.className = `stage-item stage-${statusType(stageStatus)}${current ? ' stage-running' : ''}`;

  const number = document.createElement('div');
  number.className = 'stage-index';
  number.textContent = String(index);

  const body = document.createElement('div');
  body.className = 'stage-body';
  const title = document.createElement('div');
  title.className = 'stage-title';
  title.textContent = stageDisplayName(gate);

  const detail = stageDetails[gate.id] ?? {};
  const summary = document.createElement('div');
  summary.className = 'stage-summary';
  summary.textContent = detail.summary || gate.validation || `${gate.inputContract} to ${gate.outputContract}`;

  const inside = document.createElement('div');
  inside.className = 'stage-inside';
  inside.textContent = detail.inside || gate.validation || '';

  const meta = document.createElement('div');
  meta.className = 'stage-meta';
  const estimate = document.createElement('span');
  estimate.textContent = `Typical ${formatDuration(stageEstimateSeconds(gate.id, activeTrainingProfile()))}`;
  const output = document.createElement('span');
  output.textContent = `Output: ${detail.output || gate.outputContract}`;
  meta.append(estimate, output);

  body.append(title, summary, inside, meta);

  const issue = stageIssueText(gate.id);
  if (issue && ['fail', 'blocked', 'blocked_license', 'blocked_workload', 'setup_gap'].includes(stageStatus)) {
    const issueElement = document.createElement('div');
    issueElement.className = 'stage-issue';
    issueElement.textContent = issue;
    body.append(issueElement);
  }

  if (current) {
    const trainingProgress = latestJobProgress?.trainingProgress ?? null;
    const progress = stageProgress(gate.id, trainingProgress);
    const live = document.createElement('div');
    live.className = 'stage-live';
    if (gate.id === 'splat_training' && progress.iteration && progress.iterations) {
      live.textContent = `Running: ${progress.percent.toFixed(1)}% · ${progress.iteration}/${progress.iterations} iterations · elapsed ${formatDuration(progress.elapsed)} · remaining ${formatDuration(progress.remaining)} · source ${progress.source}`;
    } else {
      live.textContent = `Running: elapsed ${formatDuration(progress.elapsed)} · estimated remaining ${formatDuration(progress.remaining)}`;
    }

    const track = document.createElement('div');
    track.className = 'stage-mini-track';
    track.setAttribute('aria-hidden', 'true');
    const bar = document.createElement('div');
    bar.className = 'stage-mini-bar';
    bar.style.width = `${Math.round(progress.percent)}%`;
    track.append(bar);
    body.append(live, track);
  }

  const status = pill(stage?.status ?? 'planned', statusType(stage?.status ?? 'planned'));
  if (runnableStages.has(gate.id)) {
    const action = document.createElement('button');
    action.className = 'stage-action';
    action.type = 'button';
    action.textContent = runningStage === gate.id ? 'Running' : heavyStages.has(gate.id) ? 'Heavy run' : 'Run';
    action.disabled = !activeJob || Boolean(runningStage) || Boolean(autoRun?.active) || Boolean(activeQueueItem());
    action.title = heavyStages.has(gate.id) ? `${stageDisplayName(gate)} can place sustained load on CPU/GPU` : `Run ${stageDisplayName(gate)}`;
    action.addEventListener('click', () => runStage(gate.id, {
      acceptWarning: true,
      allowHeavy: heavyStages.has(gate.id),
      trainingProfile: gate.id === 'splat_training' ? selectedTrainingProfile() : null,
    }));
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
    els.pipelineEtaText.textContent = `Estimated full run: ${formatDuration(totalEstimateSeconds())}`;
    els.pipelineProgressBar.style.width = '0%';
    return;
  }

  const stageById = new Map(jobStages.map((stage) => [stage.id, stage]));
  let passed = 0;
  let warnings = 0;
  let blocked = 0;
  let currentGate = null;
  const currentStageId = activeStageId();
  const trainingProgress = latestJobProgress?.trainingProgress ?? null;
  for (const gate of gates) {
    const status = stageById.get(gate.id)?.status ?? 'planned';
    if (status === 'pass') passed += 1;
    else if (status === 'warning') warnings += 1;
    else if (['fail', 'blocked', 'blocked_license', 'blocked_workload', 'setup_gap'].includes(status)) blocked += 1;
    if (!currentGate && status !== 'pass' && status !== 'warning') currentGate = gate;
  }

  const total = Math.max(1, gates.length);
  let progressUnits = passed;
  if (
    currentStageId === 'splat_training'
    && trainingProgress
    && trainingProgress.status === 'running'
    && Number.isFinite(Number(trainingProgress.percent))
  ) {
    progressUnits += clamp(Number(trainingProgress.percent) / 100, 0, 0.98);
  }
  const percent = Math.round((progressUnits / total) * 100);
  els.pipelineProgressText.textContent = `${passed}/${gates.length} passed${warnings ? `, ${warnings} warning` : ''}`;
  els.pipelineProgressBar.style.width = `${percent}%`;

  const queueItem = activeQueueItem();
  if (queueItem) {
    const current = currentStageId;
    const queueLabel = queueItemLabel(queueItem);
    if (current) {
      const detail = stageDetails[current] ?? {};
      const progress = stageProgress(current, trainingProgress);
      if (current === 'splat_training' && progress.iteration && progress.iterations) {
        els.pipelineCurrentStage.textContent = `${queueLabel}: training ${progress.percent.toFixed(1)}% (${progress.iteration}/${progress.iterations})`;
        els.pipelineEtaText.textContent = `Elapsed ${formatDuration(progress.elapsed)} · remaining ${formatDuration(progress.remaining)} · ${progress.source}`;
      } else {
        els.pipelineCurrentStage.textContent = `${queueLabel}: ${stageDisplayName({ id: current })}`;
        els.pipelineEtaText.textContent = `${detail.summary ?? 'Running'} · elapsed ${formatDuration(progress.elapsed)} · remaining ${formatDuration(progress.remaining)}`;
      }
    } else if (queueItem.status === 'cancel_requested') {
      els.pipelineCurrentStage.textContent = `${queueLabel}: cancellation requested`;
      els.pipelineEtaText.textContent = 'Waiting for the active process to stop';
    } else {
      els.pipelineCurrentStage.textContent = `${queueLabel}: starting`;
      els.pipelineEtaText.textContent = `Estimated full run: ${formatDuration(queueItem.estimatedSeconds)}`;
    }
  } else if (autoRun?.active) {
    const current = currentStageId;
    if (current) {
      const detail = stageDetails[current] ?? {};
      const progress = stageProgress(current, trainingProgress);
      if (current === 'splat_training' && progress.iteration && progress.iterations) {
        const message = `Training splats ${progress.percent.toFixed(1)}% (${progress.iteration}/${progress.iterations})`;
        els.pipelineCurrentStage.textContent = message;
        els.pipelineEtaText.textContent = `Elapsed ${formatDuration(progress.elapsed)} · remaining ${formatDuration(progress.remaining)} · ${progress.source}`;
        setWizardStatus(`${stageDisplayName({ id: current })}: ${message}`, 'neutral');
      } else {
        els.pipelineCurrentStage.textContent = `${stageDisplayName({ id: current })}: ${detail.summary ?? 'running'}`;
        els.pipelineEtaText.textContent = `Elapsed ${formatDuration(progress.elapsed)} · estimated remaining ${formatDuration(progress.remaining)}`;
      }
    } else {
      els.pipelineCurrentStage.textContent = 'Preparing automatic run';
      els.pipelineEtaText.textContent = `ETA ${formatDuration(estimateRemainingSeconds())}`;
    }
  } else if (runningStage) {
    const progress = stageProgress(runningStage, trainingProgress);
    const detail = stageDetails[runningStage] ?? {};
    els.pipelineCurrentStage.textContent = `${stageDisplayName({ id: runningStage })}: ${detail.summary ?? 'running'}`;
    els.pipelineEtaText.textContent = `Elapsed ${formatDuration(progress.elapsed)} · estimated remaining ${formatDuration(progress.remaining)}`;
  } else if (blocked) {
    els.pipelineCurrentStage.textContent = `Needs attention: ${stageDisplayName(currentGate ?? gates[0])}`;
    els.pipelineEtaText.textContent = stageIssueText(currentGate?.id) || 'Paused until the blocking check is resolved';
  } else if (currentGate) {
    els.pipelineCurrentStage.textContent = `Next: ${stageDisplayName(currentGate)}`;
    els.pipelineEtaText.textContent = `Estimated full run: ${formatDuration(totalEstimateSeconds())}`;
  } else {
    els.pipelineCurrentStage.textContent = 'Pipeline complete';
    els.pipelineEtaText.textContent = 'Generation finished';
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

function queueOverallProgress(item) {
  if (!item) return { percent: 0, elapsed: 0, remaining: 0 };
  const reports = item.reports ?? {};
  const completed = automatedStageOrder.filter((stage) => ['pass', 'warning'].includes(reports[stage]?.status)).length;
  let units = completed;
  const current = item.currentStage;
  if (current && automatedStageOrder.includes(current)) {
    const progress = stageProgress(current, item.trainingProgress ?? null);
    units = Math.max(units, automatedStageOrder.indexOf(current) + clamp(progress.percent / 100, 0, 0.98));
  }
  const percent = item.status === 'complete' ? 100 : clamp((units / automatedStageOrder.length) * 100, item.status === 'running' ? 1 : 0, 99);
  const started = Date.parse(item.startedAt || item.stageStartedAt || '');
  const elapsed = Number.isFinite(started) ? Math.max(0, (Date.now() - started) / 1000) : 0;
  const remaining = Math.max(0, Number(item.estimatedSeconds || 0) - elapsed);
  return { percent, elapsed, remaining };
}

function renderQueueMeta(container, entries) {
  container.replaceChildren();
  for (const [label, value] of entries) {
    container.append(row(label, value));
  }
}

function renderQueueItem(item) {
  const article = document.createElement('article');
  article.className = `queue-item queue-${queueStatusType(item.status)}`;
  const head = document.createElement('div');
  head.className = 'queue-item-head';
  const title = document.createElement('strong');
  title.textContent = queueItemLabel(item);
  head.append(title, pill(item.status, queueStatusType(item.status)));

  const meta = document.createElement('div');
  meta.className = 'queue-item-meta';
  meta.append(
    row('Strategy', qualityPresetLabels[item.qualityPreset] ?? item.qualityPreset),
    row('Scene', sceneProfileFor(item.sceneKind)?.label ?? item.sceneKind),
    row('ETA', formatDuration(item.estimatedSeconds)),
  );
  if (item.currentStage) {
    meta.append(row('Current', stageDisplayName({ id: item.currentStage })));
  }
  if (item.error) {
    const error = document.createElement('div');
    error.className = 'queue-error';
    error.textContent = item.error;
    meta.append(error);
  }

  const actions = document.createElement('div');
  actions.className = 'queue-actions';

  if (item.status === 'queued') {
    const nameInput = document.createElement('input');
    nameInput.type = 'text';
    nameInput.value = item.displayName || '';
    nameInput.ariaLabel = 'Queue job name';
    nameInput.addEventListener('change', () => patchQueueItem(item.id, { displayName: nameInput.value }));

    const sceneSelect = document.createElement('select');
    sceneSelect.ariaLabel = 'Queue scene profile';
    for (const [key, profile] of Object.entries(state?.sceneProfiles ?? fallbackSceneProfiles)) {
      const option = document.createElement('option');
      option.value = key;
      option.textContent = profile.label ?? key;
      sceneSelect.append(option);
    }
    sceneSelect.value = item.sceneKind;
    sceneSelect.addEventListener('change', () => patchQueueItem(item.id, { sceneKind: sceneSelect.value }));

    const qualitySelect = document.createElement('select');
    qualitySelect.ariaLabel = 'Queue generation strategy';
    for (const key of ['splatfacto_reference', 'splatfacto_big_quality', 'quality_probe', 'splatfacto_ceiling']) {
      const option = document.createElement('option');
      option.value = key;
      option.textContent = qualityPresetLabels[key] ?? key;
      qualitySelect.append(option);
    }
    qualitySelect.value = item.qualityPreset;
    qualitySelect.addEventListener('change', () => patchQueueItem(item.id, { qualityPreset: qualitySelect.value }));

    const moveUp = document.createElement('button');
    moveUp.className = 'secondary-mini-action';
    moveUp.type = 'button';
    moveUp.textContent = 'Up';
    moveUp.addEventListener('click', () => moveQueueItem(item.id, 'up'));

    const moveDown = document.createElement('button');
    moveDown.className = 'secondary-mini-action';
    moveDown.type = 'button';
    moveDown.textContent = 'Down';
    moveDown.addEventListener('click', () => moveQueueItem(item.id, 'down'));

    const remove = document.createElement('button');
    remove.className = 'danger-mini-action';
    remove.type = 'button';
    remove.textContent = 'Remove';
    remove.addEventListener('click', () => removeQueueItem(item.id));

    actions.append(nameInput, sceneSelect, qualitySelect, moveUp, moveDown, remove);
  } else if (item.status === 'running' || item.status === 'cancel_requested') {
    const progress = queueOverallProgress(item);
    const track = document.createElement('div');
    track.className = 'stage-mini-track queue-track';
    const bar = document.createElement('div');
    bar.className = 'stage-mini-bar';
    bar.style.width = `${Math.round(progress.percent)}%`;
    track.append(bar);
    meta.append(track);

    const cancel = document.createElement('button');
    cancel.className = 'danger-mini-action';
    cancel.type = 'button';
    cancel.textContent = item.status === 'cancel_requested' ? 'Cancelling' : 'Cancel';
    cancel.disabled = item.status === 'cancel_requested' || queueActionBusy;
    cancel.addEventListener('click', () => cancelQueueItem(item.id, false));

    const afterStage = document.createElement('button');
    afterStage.className = 'secondary-mini-action';
    afterStage.type = 'button';
    afterStage.textContent = 'Stop after step';
    afterStage.disabled = item.status === 'cancel_requested' || queueActionBusy;
    afterStage.addEventListener('click', () => cancelQueueItem(item.id, true));
    actions.append(cancel, afterStage);
  } else {
    if (item.jobId && item.status === 'complete') {
      const open = document.createElement('a');
      open.className = 'secondary-mini-action link-action';
      open.href = `/gallery?scene=${encodeURIComponent(item.jobId)}`;
      open.textContent = 'Open';
      actions.append(open);
    }
    const remove = document.createElement('button');
    remove.className = 'secondary-mini-action';
    remove.type = 'button';
    remove.textContent = 'Clear';
    remove.addEventListener('click', () => removeQueueItem(item.id));
    actions.append(remove);
  }

  article.append(head, meta, actions);
  return article;
}

function renderQueue() {
  const items = queueState?.items ?? [];
  const counts = queueState?.counts ?? {};
  const running = counts.running || counts.cancel_requested || 0;
  const queued = counts.queued || 0;
  const complete = counts.complete || 0;
  els.queueSummary.textContent = running || queued
    ? `${running ? `${running} running · ` : ''}${queued} queued · ${formatDuration(items.filter((item) => item.status === 'queued').reduce((sum, item) => sum + Number(item.estimatedSeconds || 0), 0))} queued ETA`
    : complete
      ? `${complete} completed in history`
      : 'No queued jobs';
  els.queueWorkerStatus.textContent = activeQueueItem() ? 'running' : queued ? 'queued' : 'idle';
  els.queueWorkerStatus.className = `pill ${activeQueueItem() ? 'warning' : queued ? 'neutral' : 'pass'}`;
  els.queueList.replaceChildren();
  if (!items.length) {
    const empty = document.createElement('div');
    empty.className = 'muted queue-empty';
    empty.textContent = 'Queue is empty.';
    els.queueList.append(empty);
    return;
  }
  for (const item of items.slice(0, 16)) {
    els.queueList.append(renderQueueItem(item));
  }
}

function renderRenderModal() {
  const item = activeQueueItem();
  if (!item) {
    els.renderModal.hidden = true;
    els.renderModalRestoreButton.hidden = true;
    renderModalMinimized = false;
    return;
  }
  const progress = queueOverallProgress(item);
  const current = item.currentStage;
  const label = queueItemLabel(item);
  els.renderModalTitle.textContent = item.status === 'cancel_requested' ? 'Cancelling render' : 'Rendering in progress';
  els.renderModalSubtitle.textContent = label;
  renderQueueMeta(els.renderModalMeta, [
    ['Strategy', qualityPresetLabels[item.qualityPreset] ?? item.qualityPreset],
    ['Scene', sceneProfileFor(item.sceneKind)?.label ?? item.sceneKind],
    ['Job', item.jobId ?? item.id],
    ['Elapsed', formatDuration(progress.elapsed)],
  ]);
  els.renderModalStage.textContent = current ? `${stageDisplayName({ id: current })}: ${stageDetails[current]?.summary ?? 'running'}` : 'Preparing render job';
  if (current === 'splat_training' && item.trainingProgress?.status === 'running' && item.trainingProgress.iteration) {
    els.renderModalEta.textContent = `${Number(item.trainingProgress.percent || 0).toFixed(1)}% · ${item.trainingProgress.iteration}/${item.trainingProgress.iterations} iterations · remaining ${formatDuration(item.trainingProgress.remainingSeconds ?? progress.remaining)}`;
  } else {
    els.renderModalEta.textContent = `Overall ${Math.round(progress.percent)}% · estimated remaining ${formatDuration(progress.remaining)}`;
  }
  els.renderModalProgressBar.style.width = `${Math.round(progress.percent)}%`;
  els.renderModalNote.textContent = item.status === 'cancel_requested'
    ? 'Stop has been requested. The current process is stopping, or this step is being allowed to finish before the next one starts.'
    : 'The server worker owns this render. You can leave the page open, add more jobs to the queue, or cancel this job.';
  els.renderCancelButton.disabled = queueActionBusy || item.status === 'cancel_requested';
  els.renderCancelAfterStageButton.disabled = queueActionBusy || item.status === 'cancel_requested';
  els.renderModal.hidden = renderModalMinimized;
  els.renderModalRestoreButton.hidden = !renderModalMinimized;
  els.renderModalRestoreButton.textContent = `${current ? stageDisplayName({ id: current }) : 'Rendering'} · ${Math.round(progress.percent)}%`;
}

function renderAll() {
  els.machineLabel.textContent = state?.machineLabel ?? 'RTX workstation';
  renderCaptures();
  updateWizardControls();
  renderStages();
  renderCompliance();
  renderJob();
  renderQueue();
  renderRenderModal();
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
  queueState = state.renderQueue ?? null;
  const activeItem = activeQueueItem();
  activeJob = activeItem?.job ?? state.latestJob ?? null;
  latestJobProgress = activeItem
    ? { job: activeItem.job, reports: activeItem.reports, trainingProgress: activeItem.trainingProgress }
    : null;
  renderAll();
}

function applyQueueState(nextQueue) {
  const previousSignature = lastQueueSignature;
  queueState = nextQueue;
  const activeItem = activeQueueItem();
  activeJob = activeItem?.job ?? activeJob ?? state?.latestJob ?? null;
  latestJobProgress = activeItem
    ? { job: activeItem.job, reports: activeItem.reports, trainingProgress: activeItem.trainingProgress }
    : null;
  const nextSignature = JSON.stringify((queueState?.items ?? []).map((item) => [
    item.id,
    item.status,
    item.currentStage,
    item.jobId,
    item.updatedAt,
  ]));
  lastQueueSignature = nextSignature;
  renderQueue();
  renderRenderModal();
  renderStages();
  renderJob();
  if (previousSignature && previousSignature !== nextSignature && !activeItem && !queueHasLiveWork()) {
    loadState().catch(() => {});
  }
}

async function pollQueue() {
  try {
    const response = await fetch('/api/queue', { cache: 'no-store' });
    if (!response.ok) return;
    applyQueueState(await response.json());
  } catch {
    // Queue polling is best-effort; the server-side queue remains authoritative.
  }
}

function startQueuePolling() {
  if (queuePollingTimer) return;
  queuePollingTimer = window.setInterval(pollQueue, 2000);
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

async function createJob(captureId = null, options = {}) {
  const capture = captureId ? { id: captureId } : selectedCapture();
  if (!capture) return null;
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
    latestJobProgress = null;
    await loadState();
    return activeJob;
  } catch (error) {
    if (!options.silent) {
      els.jobBox.replaceChildren();
      const message = document.createElement('div');
      message.className = 'error-text';
      message.textContent = error.message;
      els.jobBox.append(message);
    }
    if (options.silent) throw error;
    return null;
  } finally {
    els.planJobButton.disabled = false;
  }
}

async function queueRequest(url, options = {}) {
  queueActionBusy = true;
  renderQueue();
  renderRenderModal();
  try {
    const response = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
      ...options,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `queue ${response.status}`);
    if (payload.queue) applyQueueState(payload.queue);
    return payload;
  } finally {
    queueActionBusy = false;
    renderQueue();
    renderRenderModal();
  }
}

async function enqueueCapture(captureId, profile, sceneKind, displayName) {
  return queueRequest('/api/queue/items', {
    method: 'POST',
    body: JSON.stringify({
      captureId,
      qualityPreset: profile,
      sceneKind,
      displayName,
    }),
  });
}

async function patchQueueItem(itemId, patch) {
  return queueRequest(`/api/queue/items/${encodeURIComponent(itemId)}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  });
}

async function moveQueueItem(itemId, direction) {
  return queueRequest(`/api/queue/items/${encodeURIComponent(itemId)}/move`, {
    method: 'POST',
    body: JSON.stringify({ direction }),
  });
}

async function removeQueueItem(itemId) {
  return queueRequest(`/api/queue/items/${encodeURIComponent(itemId)}`, {
    method: 'DELETE',
  });
}

async function cancelQueueItem(itemId, afterCurrentStage = false) {
  return queueRequest(`/api/queue/items/${encodeURIComponent(itemId)}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ afterCurrentStage }),
  });
}

async function runStage(stage, options = {}) {
  if (!activeJob || runningStage) return;
  runningStage = stage;
  runningStageStartedAt = Date.now();
  latestJobProgress = null;
  const manualProgressTimer = autoRun?.active ? null : window.setInterval(() => {
    pollJobProgress();
    renderStages();
  }, 1000);
  renderStages();
  try {
    const response = await fetch('/api/jobs/run-stage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jobPath: activeJob.jobPath,
        stage,
        acceptWarning: Boolean(options.acceptWarning),
        allowHeavy: Boolean(options.allowHeavy),
        trainingProfile: options.trainingProfile ?? null,
      }),
    });
    const payload = await response.json();
    if (payload.job) {
      activeJob = payload.job;
      renderStages();
      renderJob();
    }
    if (!response.ok) throw new Error(payload.error || `stage ${response.status}`);
    if (payload.returnCode && payload.returnCode !== 0) {
      const message = stageFailureMessage(stage, payload);
      await loadState().catch(() => {});
      throw new Error(message);
    }
    await loadState();
    return payload;
  } catch (error) {
    if (!options.silent) {
      els.jobBox.replaceChildren();
      const message = document.createElement('div');
      message.className = 'error-text';
      message.textContent = error.message;
      els.jobBox.append(message);
    }
    if (options.silent) throw error;
    return null;
  } finally {
    runningStage = null;
    runningStageStartedAt = null;
    if (manualProgressTimer) window.clearInterval(manualProgressTimer);
    renderStages();
  }
}

async function pollJobProgress() {
  if ((!autoRun?.active && !runningStage) || !activeJob?.jobPath || progressPolling) return;
  progressPolling = true;
  try {
    const params = new URLSearchParams({ jobPath: activeJob.jobPath });
    const response = await fetch(`/api/jobs/progress?${params.toString()}`, { cache: 'no-store' });
    if (!response.ok) return;
    const payload = await response.json();
    latestJobProgress = payload;
    if (payload.job) activeJob = payload.job;
    renderStages();
    renderJob();
  } catch {
    // Progress polling is best-effort; the blocking stage request remains authoritative.
  } finally {
    progressPolling = false;
  }
}

async function uploadWizardCapture(file, profile) {
  const params = new URLSearchParams({
    displayName: els.wizardCaptureName.value.trim(),
    sceneKind: els.wizardSceneKind.value,
    qualityPreset: profile,
  });
  const response = await fetch(`/api/captures/create-upload?${params.toString()}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/octet-stream',
      'X-Filename': file.name,
    },
    body: file,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || payload.report?.checks?.[0]?.summary || `upload ${response.status}`);
  return payload;
}

function startAutoRunTimer() {
  window.clearInterval(autoRunTimer);
  autoRunTimer = window.setInterval(() => {
    if (!autoRun?.active) {
      window.clearInterval(autoRunTimer);
      autoRunTimer = null;
      return;
    }
    pollJobProgress();
    renderStages();
  }, 1000);
}

async function generatePipeline() {
  const file = els.videoFileInput.files?.[0] ?? null;
  if (!file || wizardBusy) return;
  const profile = selectedTrainingProfile();
  const sceneKind = selectedSceneProfileKey();
  wizardBusy = true;
  updateWizardControls();
  setWizardStatus(`Uploading ${file.name}`, 'neutral');
  try {
    const upload = await uploadWizardCapture(file, profile);
    captureSelectionTouched = true;
    await loadState();
    els.captureSelect.value = upload.capture.id;
    setWizardStatus('Adding render job to queue', 'neutral');
    await enqueueCapture(upload.capture.id, profile, sceneKind, els.wizardCaptureName.value.trim());
    setWizardStatus('Added to render queue. You can add another video while the worker runs.', 'pass');
    els.videoFileInput.value = '';
  } catch (error) {
    setWizardStatus(error.message, 'fail');
    els.jobBox.replaceChildren();
    const message = document.createElement('div');
    message.className = 'error-text';
    message.textContent = error.message;
    els.jobBox.append(message);
  } finally {
    wizardBusy = false;
    updateWizardControls();
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

function setDebugLoadStatus(text = '', type = 'neutral') {
  viewerScene.debugLoadLabel = text;
  viewerScene.debugLoadType = type;
  if (!els.debugOverlay) return;
  els.debugOverlay.hidden = !text;
  els.debugOverlay.textContent = text;
  els.debugOverlay.dataset.type = type;
  if (viewerScene.mode === 'debug' && text) setViewerStatus(text, type);
}

function formatDebugDownloadProgress(progress = {}) {
  const percent = Number(progress.percent);
  if (Number.isFinite(percent)) return `Loading debug PLY ${Math.round(clamp(percent, 0, 100))}%`;
  if (Number.isFinite(progress.loaded)) return `Loading debug PLY ${formatBytes(progress.loaded)}`;
  return 'Loading debug PLY';
}

function waitForViewerPaint() {
  return new Promise((resolve) => {
    if (typeof requestAnimationFrame === 'function') requestAnimationFrame(() => resolve());
    else setTimeout(resolve, 0);
  });
}

async function fetchArrayBufferWithProgress(url, onProgress = null) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`artifact ${response.status}`);
  const contentLength = Number.parseInt(response.headers.get('Content-Length') ?? '', 10);
  const total = Number.isFinite(contentLength) && contentLength > 0 ? contentLength : 0;
  if (!response.body?.getReader) {
    onProgress?.({ loaded: 0, total, percent: total ? 0 : null });
    const buffer = await response.arrayBuffer();
    onProgress?.({ loaded: buffer.byteLength, total: total || buffer.byteLength, percent: 100 });
    return buffer;
  }

  const reader = response.body.getReader();
  const chunks = total ? null : [];
  const output = total ? new Uint8Array(total) : null;
  let loaded = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    if (!value?.byteLength) continue;
    if (output) output.set(value, loaded);
    else chunks.push(value);
    loaded += value.byteLength;
    onProgress?.({
      loaded,
      total,
      percent: total ? (loaded / total) * 100 : null,
    });
  }
  onProgress?.({ loaded, total: total || loaded, percent: 100 });
  if (output) return loaded === output.byteLength ? output.buffer : output.buffer.slice(0, loaded);

  const merged = new Uint8Array(loaded);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return merged.buffer;
}

function setExportLink(link, url, fileName) {
  if (!link) return;
  if (!url) {
    link.removeAttribute('href');
    link.removeAttribute('download');
    link.setAttribute('aria-disabled', 'true');
    return;
  }
  link.href = url;
  link.download = fileName;
  link.removeAttribute('aria-disabled');
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
  if (profile === 'rtx_high_quality') {
    return { text: training.renderReview?.status === 'pass' ? 'high inspect' : 'high warning', type: training.renderReview?.status === 'pass' ? 'pass' : 'warning' };
  }
  if (profile === 'rtx_ultra_quality') {
    return { text: training.renderReview?.status === 'pass' ? 'ultra inspect' : 'ultra warning', type: training.renderReview?.status === 'pass' ? 'pass' : 'warning' };
  }
  if (profile === 'rtx_stable_quality') {
    return { text: training.renderReview?.status === 'pass' ? 'max stable inspect' : 'max stable warning', type: training.renderReview?.status === 'pass' ? 'pass' : 'warning' };
  }
  if (profile === 'splatfacto_preview' || profile === 'splatfacto_reference' || profile === 'splatfacto_big_quality' || profile === 'splatfacto_ceiling') {
    return { text: training.renderReview?.status === 'pass' ? 'splatfacto inspect' : 'splatfacto warning', type: training.renderReview?.status === 'pass' ? 'pass' : 'warning' };
  }
  if (profile === 'rtx_ceiling_quality') {
    return { text: training.renderReview?.status === 'pass' ? 'ceiling inspect' : 'ceiling warning', type: training.renderReview?.status === 'pass' ? 'pass' : 'warning' };
  }
  if (profile === 'rtx_max_quality') {
    return { text: training.renderReview?.status === 'pass' ? 'max inspect' : 'max warning', type: training.renderReview?.status === 'pass' ? 'pass' : 'warning' };
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
  const exportInfo = manifest?.export ?? {};
  const cameraViews = Array.isArray(manifest?.cameraViews) ? manifest.cameraViews : [];
  const activeView = extra?.activeCameraView ?? viewerScene.activeCameraView;
  renderSampleComparison(manifest?.preview ?? {});
  const status = viewer.viewerStatus ?? viewer.packagingStatus ?? 'packaged';
  const quality = viewerQuality(status, training, runConfig);
  setViewerStatus(quality.text, quality.type);
  if (viewerScene.mode === 'debug' && viewerScene.debugLoadLabel) {
    setViewerStatus(viewerScene.debugLoadLabel, viewerScene.debugLoadType);
  }
  setExportLink(els.exportSplatLink, exportInfo.primaryAssetUrl ?? artifact.url, exportInfo.recommendedSplatFileName ?? `gaussian-splat-${training.profile ?? runConfig.profile ?? 'artifact'}.ply`);
  setExportLink(els.exportManifestLink, viewer.viewerManifestUrl, exportInfo.recommendedManifestFileName ?? 'viewer-manifest.json');
  els.viewerMeta.append(
    row('Artifact', artifact.format ?? 'ply'),
    row('Renderer', activeRendererLabel()),
    row('Profile', training.profile ?? runConfig.profile ?? '-'),
    row('Strategy', training.densifyStrategy ?? runConfig.densifyStrategy ?? '-'),
    row('Gaussians', formatCount(extra?.pointCount ?? (viewerScene.pointCount || ply.vertexCount))),
    row('Debug points', viewerScene.debugPointCount ? formatCount(viewerScene.debugPointCount) : '-'),
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

function parseBinaryPly(buffer, maxDebugPoints = debugPointBudget) {
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
  const sampleStride = Math.max(1, Math.ceil(vertexCount / maxDebugPoints));
  for (let index = 0; index < vertexCount; index += sampleStride) {
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
  return { points, vertexCount, debugPointCount: points.length, sampleStride, properties };
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
    viewerScene.debugPointCount = 0;
    viewerScene.artifactUrl = null;
    viewerScene.uploadedArtifactUrl = null;
    setDebugLoadStatus('');
    markViewerReady();
    renderViewerMeta();
    return;
  }
  if (viewerScene.artifactUrl === url && viewerScene.pointData) {
    setDebugLoadStatus('');
    renderViewerMeta({ pointCount: viewerScene.pointCount });
    return;
  }

  const token = ++viewerLoadToken;
  setDebugLoadStatus('Loading debug PLY 0%', 'neutral');
  try {
    const buffer = await fetchArrayBufferWithProgress(url, (progress) => {
      if (token !== viewerLoadToken) return;
      setDebugLoadStatus(formatDebugDownloadProgress(progress), 'neutral');
    });
    if (token !== viewerLoadToken) return;
    setDebugLoadStatus('Parsing debug PLY', 'neutral');
    await waitForViewerPaint();
    const parsed = parseBinaryPly(buffer);
    if (token !== viewerLoadToken) return;
    setDebugLoadStatus('Preparing debug points', 'neutral');
    await waitForViewerPaint();
    if (token !== viewerLoadToken) return;
    viewerScene.pointData = buildPointData(normalizePoints(parsed.points));
    viewerScene.pointCount = parsed.vertexCount;
    viewerScene.debugPointCount = parsed.debugPointCount;
    viewerScene.artifactUrl = url;
    viewerScene.uploadedArtifactUrl = null;
    uploadPointData();
    setDebugLoadStatus('');
    renderViewerMeta({ pointCount: parsed.vertexCount });
    markViewerReady();
  } catch (error) {
    if (token !== viewerLoadToken) return;
    viewerScene.pointData = null;
    viewerScene.pointCount = 0;
    viewerScene.debugPointCount = 0;
    viewerScene.artifactUrl = null;
    viewerScene.uploadedArtifactUrl = null;
    setDebugLoadStatus(`Debug load failed: ${error.message}`, 'fail');
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
  viewerScene.sparkController.setNavigationMode(viewerScene.sparkNavigationMode);
  viewerScene.sparkController.setNavigationSensitivity(viewerScene.navigationSensitivity);
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
  const step = (0.09 * viewerScene.navigationSensitivity) / viewerScene.zoom;
  viewerScene.panX += deltaX * step;
  viewerScene.panY += deltaY * step;
}

function orbitViewer(deltaX, deltaY) {
  viewerScene.rotationY += deltaX * 0.16 * viewerScene.navigationSensitivity;
  viewerScene.rotationX = clamp(viewerScene.rotationX + deltaY * 0.16 * viewerScene.navigationSensitivity, -1.4, 1.4);
}

function zoomViewer(factor) {
  const adjustedFactor = 1 + ((factor - 1) * viewerScene.navigationSensitivity);
  viewerScene.zoom = clamp(viewerScene.zoom * adjustedFactor, 0.35, 5);
}

function setViewerMode(mode) {
  viewerScene.mode = mode;
  const isSpark = mode === 'spark';
  els.sparkViewport.hidden = !isSpark;
  els.debugViewport.hidden = isSpark;
  els.viewerModeSparkButton.classList.toggle('active', isSpark);
  els.viewerModeDebugButton.classList.toggle('active', !isSpark);
  els.viewerModeSparkButton.setAttribute('aria-pressed', String(isSpark));
  els.viewerModeDebugButton.setAttribute('aria-pressed', String(!isSpark));
  if (isSpark) loadSparkArtifact();
  else loadViewerArtifact();
  renderViewerMeta({ pointCount: viewerScene.pointCount });
}

function setSparkNavigationMode(mode) {
  viewerScene.sparkNavigationMode = mode === 'orbit' ? 'orbit' : 'walk';
  els.viewerNavWalkButton.classList.toggle('active', viewerScene.sparkNavigationMode === 'walk');
  els.viewerNavOrbitButton.classList.toggle('active', viewerScene.sparkNavigationMode === 'orbit');
  els.viewerNavWalkButton.setAttribute('aria-pressed', String(viewerScene.sparkNavigationMode === 'walk'));
  els.viewerNavOrbitButton.setAttribute('aria-pressed', String(viewerScene.sparkNavigationMode === 'orbit'));
  if (viewerScene.sparkController && !viewerScene.sparkFailed) {
    viewerScene.sparkController.setNavigationMode(viewerScene.sparkNavigationMode);
  }
}

function setNavigationSensitivity(value = defaultNavigationSensitivity * 100) {
  const numeric = Number(value);
  const percent = Number.isFinite(numeric)
    ? clamp(numeric, 20, 120)
    : defaultNavigationSensitivity * 100;
  viewerScene.navigationSensitivity = percent / 100;
  els.viewerSensitivityInput.value = String(Math.round(percent));
  els.viewerSensitivityValue.textContent = `${Math.round(percent)}%`;
  if (viewerScene.sparkController && !viewerScene.sparkFailed) {
    viewerScene.sparkController.setNavigationSensitivity(viewerScene.navigationSensitivity);
  }
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
    const panScale = (0.0018 * viewerScene.navigationSensitivity) / viewerScene.zoom;
    viewerScene.panX -= dx * panScale;
    viewerScene.panY += dy * panScale;
  } else {
    viewerScene.rotationY += dx * 0.008 * viewerScene.navigationSensitivity;
    viewerScene.rotationX = clamp(viewerScene.rotationX + dy * 0.008 * viewerScene.navigationSensitivity, -1.4, 1.4);
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
els.viewerNavWalkButton.addEventListener('click', () => setSparkNavigationMode('walk'));
els.viewerNavOrbitButton.addEventListener('click', () => setSparkNavigationMode('orbit'));
els.viewerSensitivityInput.addEventListener('input', (event) => setNavigationSensitivity(event.target.value));

els.captureSelect.addEventListener('change', () => {
  captureSelectionTouched = true;
  els.acceptCaptureWarning.checked = false;
  els.importStatus.textContent = '';
  renderCaptureMeta();
});
els.videoFileInput.addEventListener('change', handleVideoFileChange);
els.wizardCaptureName.addEventListener('input', updateWizardControls);
els.wizardSceneKind.addEventListener('change', updateWizardControls);
els.wizardQualityPreset.addEventListener('change', updateWizardControls);
els.wizardSelfCaptured.addEventListener('change', updateWizardControls);
els.generatePipelineButton.addEventListener('click', generatePipeline);
els.acceptCaptureWarning.addEventListener('change', updateImportControls);
els.importVideoButton.addEventListener('click', importVideo);
els.planJobButton.addEventListener('click', () => createJob());
els.renderCancelButton.addEventListener('click', () => {
  const item = activeQueueItem();
  if (item) cancelQueueItem(item.id, false);
});
els.renderCancelAfterStageButton.addEventListener('click', () => {
  const item = activeQueueItem();
  if (item) cancelQueueItem(item.id, true);
});
els.renderModalMinimizeButton.addEventListener('click', () => {
  renderModalMinimized = true;
  renderRenderModal();
});
els.renderModalRestoreButton.addEventListener('click', () => {
  renderModalMinimized = false;
  renderRenderModal();
});

requestAnimationFrame(drawPreviewFrame);
setNavigationSensitivity(defaultNavigationSensitivity * 100);
const bootPromise = loadState().catch((error) => {
  els.jobBox.replaceChildren();
  const message = document.createElement('div');
  message.className = 'error-text';
  message.textContent = error.message;
  els.jobBox.append(message);
});
startQueuePolling();

if (new URLSearchParams(window.location.search).has('waitForViewer')) {
  await bootPromise;
  await viewerReadyPromise;
  document.documentElement.dataset.viewerReady = 'true';
}
