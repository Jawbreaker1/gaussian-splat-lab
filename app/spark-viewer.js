import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { SparkRenderer, SplatMesh } from '@sparkjsdev/spark';

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function formatProgress(event) {
  if (!event?.lengthComputable || !event.total) return 'Loading splat artifact';
  return `Loading splat artifact ${Math.round((event.loaded / event.total) * 100)}%`;
}

function validBox(box) {
  return Number.isFinite(box.min.x)
    && Number.isFinite(box.min.y)
    && Number.isFinite(box.min.z)
    && Number.isFinite(box.max.x)
    && Number.isFinite(box.max.y)
    && Number.isFinite(box.max.z);
}

function vectorFromArray(value) {
  if (!Array.isArray(value) || value.length !== 3 || value.some((item) => !Number.isFinite(Number(item)))) {
    return null;
  }
  return new THREE.Vector3(Number(value[0]), Number(value[1]), Number(value[2]));
}

function normalizeVector(value) {
  const vector = vectorFromArray(value);
  if (!vector || vector.lengthSq() <= 1e-12) return null;
  return vector.normalize();
}

function cameraViewToken(views) {
  if (!Array.isArray(views)) return '';
  return views
    .map((view) => `${view?.selectedIndex ?? '-'}:${view?.imageName ?? '-'}:${view?.referenceKind ?? '-'}`)
    .join('|');
}

export function createSparkViewer({ canvas, overlay, onStatus }) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x05070a);

  const camera = new THREE.PerspectiveCamera(48, 1, 0.01, 100);
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: false,
    alpha: false,
    powerPreference: 'high-performance',
  });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.35));

  const spark = new SparkRenderer({
    renderer,
    sortRadial: false,
    maxPixelRadius: 384,
    minSortIntervalMs: 16,
  });
  scene.add(spark);

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.screenSpacePanning = true;
  controls.minDistance = 0.015;
  controls.maxDistance = 14;
  controls.enabled = false;
  const walkButtonLookPixels = 24;
  const walkRadiansPerPixel = 0.0016;
  const orbitButtonRadians = 0.038;
  const maxButtonPanStep = 0.095;
  const defaultNavigationSensitivity = 0.55;

  const grid = new THREE.GridHelper(2.2, 16, 0x315c66, 0x24323a);
  grid.position.y = -0.82;
  grid.material.transparent = true;
  grid.material.opacity = 0.16;
  grid.visible = false;
  scene.add(grid);

  const axes = new THREE.AxesHelper(0.9);
  axes.position.y = -0.78;
  axes.visible = false;
  scene.add(axes);

  let splat = null;
  let loadedUrl = null;
  let fitState = null;
  let cameraViews = [];
  let cameraViewsToken = '';
  let activeCameraViewIndex = 0;
  let navigationMode = 'walk';
  let guardrailMode = 'safe';
  let guardrailState = null;
  let lastGuardrailClamp = null;
  let lastGuidedKeyStepMs = 0;
  let guidedPlaying = false;
  let guidedProgress = 0;
  let guidedDirection = 1;
  let draggingLook = false;
  let lastPointerX = 0;
  let lastPointerY = 0;
  let walkYaw = 0;
  let walkPitch = 0;
  let walkFocusDistance = 1;
  let navigationSensitivity = defaultNavigationSensitivity;
  let disposed = false;
  let lastRenderMs = 0;
  const minFrameMs = 1000 / 24;
  const defaultCameraPosition = new THREE.Vector3(0.72, 0.34, 2.55);
  const right = new THREE.Vector3();
  const up = new THREE.Vector3();
  const move = new THREE.Vector3();
  const forward = new THREE.Vector3();
  const target = new THREE.Vector3();
  const offset = new THREE.Vector3();
  const walkBaseForward = new THREE.Vector3();
  const walkNavigationUp = new THREE.Vector3(0, 1, 0);
  const projectedForward = new THREE.Vector3();
  const projectedUp = new THREE.Vector3();
  const projectedCameraUp = new THREE.Vector3();
  const fallbackAxis = new THREE.Vector3();
  const cameraViewUpSum = new THREE.Vector3();
  const walkYawQuat = new THREE.Quaternion();
  const walkPitchQuat = new THREE.Quaternion();
  const pressedKeys = new Set();
  const spherical = new THREE.Spherical();
  const guardrailClosest = new THREE.Vector3();
  const guardrailCandidate = new THREE.Vector3();
  const guardrailSegment = new THREE.Vector3();
  const guardrailDelta = new THREE.Vector3();
  const guardrailHorizontal = new THREE.Vector3();
  const guardrailConstrained = new THREE.Vector3();
  const guardrailCorrection = new THREE.Vector3();
  const guidedPosition = new THREE.Vector3();
  const guidedTarget = new THREE.Vector3();
  const guidedForward = new THREE.Vector3();
  const guidedUp = new THREE.Vector3();

  canvas.tabIndex = canvas.tabIndex >= 0 ? canvas.tabIndex : 0;

  function setOverlay(text, type = 'neutral') {
    overlay.textContent = text;
    overlay.hidden = !text;
    overlay.dataset.type = type;
    onStatus?.(text, type);
  }

  function setNavigationSensitivity(value = defaultNavigationSensitivity) {
    const numeric = Number(value);
    navigationSensitivity = Number.isFinite(numeric)
      ? clamp(numeric, 0.2, 1.2)
      : defaultNavigationSensitivity;
    controls.rotateSpeed = 0.55 * navigationSensitivity;
    controls.zoomSpeed = 0.7 * navigationSensitivity;
    controls.panSpeed = 0.65 * navigationSensitivity;
    return { sensitivity: navigationSensitivity };
  }

  function resize() {
    const rect = canvas.parentElement.getBoundingClientRect();
    const width = Math.max(1, Math.floor(rect.width));
    const height = Math.max(1, Math.floor(rect.height));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function projectOnNavigationPlane(source, targetVector) {
    targetVector.copy(source).addScaledVector(walkNavigationUp, -source.dot(walkNavigationUp));
    if (targetVector.lengthSq() <= 1e-10) {
      targetVector.copy(walkBaseForward);
    }
    if (targetVector.lengthSq() <= 1e-10) {
      targetVector.setFromMatrixColumn(camera.matrixWorld, 2).multiplyScalar(-1);
      targetVector.addScaledVector(walkNavigationUp, -targetVector.dot(walkNavigationUp));
    }
    if (targetVector.lengthSq() <= 1e-10) {
      fallbackAxis.set(0, 1, 0);
      if (Math.abs(fallbackAxis.dot(walkNavigationUp)) > 0.88) fallbackAxis.set(1, 0, 0);
      targetVector.copy(fallbackAxis).addScaledVector(walkNavigationUp, -fallbackAxis.dot(walkNavigationUp));
    }
    return targetVector.normalize();
  }

  function averageCameraViewUp(views = cameraViews) {
    cameraViewUpSum.set(0, 0, 0);
    for (const view of views) {
      const viewUp = normalizeVector(view?.up);
      if (!viewUp) continue;
      if (cameraViewUpSum.lengthSq() > 1e-10 && cameraViewUpSum.dot(viewUp) < 0) {
        viewUp.negate();
      }
      cameraViewUpSum.add(viewUp);
    }
    if (cameraViewUpSum.lengthSq() <= 1e-10) return null;
    return cameraViewUpSum.clone().normalize();
  }

  function setNavigationUp(upHint = null) {
    const averagedUp = averageCameraViewUp();
    const candidate = averagedUp ?? upHint ?? camera.up;
    if (candidate && Number.isFinite(candidate.x) && Number.isFinite(candidate.y) && Number.isFinite(candidate.z) && candidate.lengthSq() > 1e-10) {
      walkNavigationUp.copy(candidate).normalize();
    } else {
      walkNavigationUp.set(0, 1, 0);
    }
    return walkNavigationUp;
  }

  function walkMovementBasis() {
    camera.updateMatrixWorld(true);
    camera.getWorldDirection(forward).normalize();
    projectOnNavigationPlane(forward, projectedForward);
    right.crossVectors(projectedForward, walkNavigationUp).normalize();
    up.copy(walkNavigationUp);
    return { horizontalForward: projectedForward, horizontalRight: right, verticalUp: up };
  }

  function setWalkBasisFromCamera() {
    camera.updateMatrixWorld(true);
    camera.getWorldDirection(forward).normalize();
    setNavigationUp(camera.up);
    projectOnNavigationPlane(forward, walkBaseForward);
    walkYaw = 0;
    walkPitch = Math.asin(clamp(forward.dot(walkNavigationUp), -0.98, 0.98));
    walkFocusDistance = clamp(camera.position.distanceTo(controls.target) || 1, 0.08, 8);
  }

  function syncTargetToCamera() {
    camera.updateMatrixWorld(true);
    camera.getWorldDirection(forward).normalize();
    controls.target.copy(camera.position).add(forward.multiplyScalar(walkFocusDistance));
  }

  function applyWalkLook() {
    walkYawQuat.setFromAxisAngle(walkNavigationUp, walkYaw);
    const yawedForward = walkBaseForward.clone().applyQuaternion(walkYawQuat).normalize();
    const yawedRight = yawedForward.clone().cross(walkNavigationUp).normalize();
    walkPitchQuat.setFromAxisAngle(yawedRight, walkPitch);
    const nextForward = yawedForward.applyQuaternion(walkPitchQuat).normalize();
    const nextUp = new THREE.Vector3().crossVectors(yawedRight, nextForward).normalize();
    camera.up.copy(nextUp);
    camera.lookAt(camera.position.clone().add(nextForward));
    camera.updateMatrixWorld(true);
    syncTargetToCamera();
  }

  function rotateWalk(deltaX, deltaY) {
    if (navigationMode !== 'walk') return;
    const sensitivity = walkRadiansPerPixel * navigationSensitivity;
    walkYaw -= deltaX * sensitivity;
    walkPitch = clamp(walkPitch - deltaY * sensitivity, -1.35, 1.35);
    applyWalkLook();
  }

  function stabilizeOrbitRoll() {
    setNavigationUp(camera.up);
    camera.up.copy(walkNavigationUp);
    camera.lookAt(controls.target);
    camera.updateMatrixWorld(true);
    controls.update();
  }

  function setNavigationMode(mode = 'walk') {
    navigationMode = mode === 'orbit' ? 'orbit' : 'walk';
    controls.enabled = navigationMode === 'orbit';
    draggingLook = false;
    pressedKeys.clear();
    if (navigationMode === 'walk') {
      setWalkBasisFromCamera();
      applyWalkLook();
    } else {
      stabilizeOrbitRoll();
    }
    return { mode: navigationMode };
  }

  function setGuardrailMode(mode = 'safe') {
    guardrailMode = ['guided', 'safe', 'free'].includes(mode) ? mode : 'safe';
    lastGuidedKeyStepMs = 0;
    if (guardrailMode === 'guided' && navigationMode !== 'walk') {
      setNavigationMode('walk');
    }
    if (guardrailMode === 'guided' && fitState && cameraViews.length) {
      const nearestIndex = nearestCameraViewIndex();
      guidedProgress = nearestIndex >= 0 ? nearestIndex : activeCameraViewIndex;
      guidedDirection = 1;
      guidedPlaying = cameraViews.length > 1;
      applyCameraView(guidedProgress);
    } else if (guardrailMode !== 'free') {
      guidedPlaying = false;
      const clamped = applyPositionGuardrail();
      if (clamped && navigationMode === 'walk') syncTargetToCamera();
    } else {
      guidedPlaying = false;
      lastGuardrailClamp = null;
    }
    return { mode: guardrailMode, guidedPlaying, guardrail: guardrailState };
  }

  function setGuidedPlayback(playing = true) {
    if (playing && guardrailMode !== 'guided') {
      setGuardrailMode('guided');
    }
    guidedPlaying = Boolean(playing) && guardrailMode === 'guided' && cameraViews.length > 1;
    return { mode: guardrailMode, guidedPlaying, activeViewIndex: activeCameraViewIndex, viewCount: cameraViews.length };
  }

  function setCameraViews(views = []) {
    const nextViews = Array.isArray(views)
      ? views.filter((view) => (
        vectorFromArray(view?.position)
        && normalizeVector(view?.forward)
        && normalizeVector(view?.up)
      ))
      : [];
    const nextToken = cameraViewToken(nextViews);
    const changed = nextToken !== cameraViewsToken;
    cameraViews = nextViews;
    cameraViewsToken = nextToken;
    setNavigationUp(camera.up);
    if (changed) activeCameraViewIndex = 0;
    if (activeCameraViewIndex >= cameraViews.length) activeCameraViewIndex = 0;
    if (fitState) buildNavigationGuardrails();
    if (changed && fitState && splat && cameraViews.length) applyCameraView(activeCameraViewIndex);
    return {
      changed,
      viewCount: cameraViews.length,
      activeViewIndex: activeCameraViewIndex,
      activeView: cameraViews[activeCameraViewIndex] ?? null,
    };
  }

  function transformRawPoint(point) {
    if (!fitState) return point.clone();
    return point.clone().sub(fitState.center).multiplyScalar(fitState.scale);
  }

  function scaledSceneExtent() {
    if (!fitState) return 1.62;
    return clamp(fitState.maxExtent * fitState.scale, 0.6, 2.4);
  }

  function buildNavigationGuardrails() {
    if (!fitState || cameraViews.length < 2) {
      guardrailState = null;
      lastGuardrailClamp = null;
      return null;
    }

    const points = cameraViews
      .map((view) => vectorFromArray(view?.position))
      .filter(Boolean)
      .map((point) => transformRawPoint(point));
    if (points.length < 2) {
      guardrailState = null;
      lastGuardrailClamp = null;
      return null;
    }

    let pathLength = 0;
    for (let index = 1; index < points.length; index += 1) {
      pathLength += points[index - 1].distanceTo(points[index]);
    }
    const extent = scaledSceneExtent();
    const averageSpacing = pathLength / Math.max(1, points.length - 1);
    const safeRadius = clamp(Math.max(averageSpacing * 5, extent * 0.085), extent * 0.055, extent * 0.18);
    const guidedRadius = clamp(Math.max(averageSpacing * 2.2, extent * 0.032), extent * 0.025, extent * 0.07);
    const verticalRadius = clamp(extent * 0.085, 0.045, 0.18);
    const guidedVerticalRadius = clamp(verticalRadius * 0.45, 0.025, 0.08);

    guardrailState = {
      points,
      pathLength,
      averageSpacing,
      safeRadius,
      guidedRadius,
      verticalRadius,
      guidedVerticalRadius,
    };
    lastGuardrailClamp = null;
    return guardrailState;
  }

  function closestPathPoint(position, out = guardrailClosest) {
    const points = guardrailState?.points ?? [];
    if (!points.length) return null;
    if (points.length === 1) {
      out.copy(points[0]);
      return { index: 0, segmentT: 0, distanceSq: position.distanceToSquared(out) };
    }

    let bestDistanceSq = Infinity;
    let bestIndex = 0;
    let bestT = 0;
    for (let index = 0; index < points.length - 1; index += 1) {
      const start = points[index];
      const end = points[index + 1];
      guardrailSegment.subVectors(end, start);
      const segmentLengthSq = guardrailSegment.lengthSq();
      guardrailDelta.subVectors(position, start);
      const t = segmentLengthSq <= 1e-12
        ? 0
        : clamp(guardrailDelta.dot(guardrailSegment) / segmentLengthSq, 0, 1);
      guardrailCandidate.copy(start).addScaledVector(guardrailSegment, t);
      const distanceSq = position.distanceToSquared(guardrailCandidate);
      if (distanceSq < bestDistanceSq) {
        bestDistanceSq = distanceSq;
        bestIndex = index;
        bestT = t;
        out.copy(guardrailCandidate);
      }
    }
    return { index: bestIndex, segmentT: bestT, distanceSq: bestDistanceSq };
  }

  function nearestCameraViewIndex(position = camera.position) {
    const points = guardrailState?.points ?? [];
    if (!points.length) return -1;
    let bestIndex = 0;
    let bestDistanceSq = Infinity;
    for (let index = 0; index < points.length; index += 1) {
      const distanceSq = position.distanceToSquared(points[index]);
      if (distanceSq < bestDistanceSq) {
        bestDistanceSq = distanceSq;
        bestIndex = index;
      }
    }
    return bestIndex;
  }

  function readCameraViewPose(index) {
    const view = cameraViews[index];
    const rawPosition = vectorFromArray(view?.position);
    const viewForward = normalizeVector(view?.forward);
    const viewUp = normalizeVector(view?.up);
    if (!rawPosition || !viewForward || !viewUp) return null;
    return {
      rawPosition,
      forward: viewForward,
      up: viewUp,
      fovYDegrees: clamp(Number(view.fovYDegrees) || 48, 20, 85),
    };
  }

  function focusDistanceForPose(rawPosition, viewForward) {
    const centerOffset = fitState.center.clone().sub(rawPosition);
    let focusDistance = centerOffset.dot(viewForward);
    const minFocusDistance = fitState.maxExtent * 0.04;
    if (!Number.isFinite(focusDistance) || focusDistance < minFocusDistance) {
      focusDistance = Math.max(fitState.maxExtent * 0.62, 0.25);
    }
    return focusDistance;
  }

  function applyCameraPose(rawPosition, viewForward, viewUp, fovYDegrees) {
    const focusDistance = focusDistanceForPose(rawPosition, viewForward);
    guidedTarget.copy(rawPosition).addScaledVector(viewForward, focusDistance);
    const nextPosition = transformRawPoint(rawPosition);
    const nextTarget = transformRawPoint(guidedTarget);
    camera.up.copy(viewUp);
    camera.position.copy(nextPosition);
    camera.fov = clamp(Number(fovYDegrees) || 48, 20, 85);
    camera.near = 0.002;
    camera.far = 100;
    camera.updateProjectionMatrix();
    camera.lookAt(nextTarget);
    camera.updateMatrixWorld(true);
    controls.target.copy(nextTarget);
    controls.update();
    setWalkBasisFromCamera();
    if (navigationMode === 'walk') applyWalkLook();
    else stabilizeOrbitRoll();
    return true;
  }

  function applyInterpolatedCameraView(progress = guidedProgress) {
    if (!fitState || !cameraViews.length) return false;
    if (cameraViews.length === 1) return applyCameraView(0);
    const maxIndex = cameraViews.length - 1;
    const boundedProgress = clamp(Number(progress) || 0, 0, maxIndex);
    const leftIndex = Math.floor(boundedProgress);
    const rightIndex = Math.min(maxIndex, leftIndex + 1);
    const t = boundedProgress - leftIndex;
    const left = readCameraViewPose(leftIndex);
    const rightPose = readCameraViewPose(rightIndex);
    if (!left || !rightPose) return false;

    guidedPosition.copy(left.rawPosition).lerp(rightPose.rawPosition, t);
    guidedForward.copy(left.forward).lerp(rightPose.forward, t);
    if (guidedForward.lengthSq() <= 1e-10) guidedForward.copy(left.forward);
    guidedForward.normalize();

    guidedUp.copy(left.up);
    const rightUp = rightPose.up.clone();
    if (guidedUp.dot(rightUp) < 0) rightUp.negate();
    guidedUp.lerp(rightUp, t);
    if (guidedUp.lengthSq() <= 1e-10) guidedUp.copy(left.up);
    guidedUp.normalize();

    guidedProgress = boundedProgress;
    activeCameraViewIndex = Math.round(boundedProgress);
    return applyCameraPose(
      guidedPosition,
      guidedForward,
      guidedUp,
      THREE.MathUtils.lerp(left.fovYDegrees, rightPose.fovYDegrees, t),
    );
  }

  function updateGuidedAnimation(deltaSeconds) {
    if (guardrailMode !== 'guided' || !guidedPlaying || cameraViews.length < 2) return;
    const maxIndex = cameraViews.length - 1;
    const viewsPerSecond = clamp(8 * navigationSensitivity, 2.5, 10);
    guidedProgress += viewsPerSecond * deltaSeconds * guidedDirection;
    if (guidedProgress >= maxIndex) {
      guidedProgress = maxIndex;
      guidedDirection = -1;
    } else if (guidedProgress <= 0) {
      guidedProgress = 0;
      guidedDirection = 1;
    }
    applyInterpolatedCameraView(guidedProgress);
  }

  function applyPositionGuardrail() {
    if (navigationMode !== 'walk' || guardrailMode === 'free' || !guardrailState) {
      lastGuardrailClamp = null;
      return false;
    }

    const nearest = closestPathPoint(camera.position, guardrailClosest);
    if (!nearest) return false;

    const radius = guardrailMode === 'guided' ? guardrailState.guidedRadius : guardrailState.safeRadius;
    const verticalRadius = guardrailMode === 'guided'
      ? guardrailState.guidedVerticalRadius
      : guardrailState.verticalRadius;
    guardrailDelta.subVectors(camera.position, guardrailClosest);
    const verticalOffset = guardrailDelta.dot(walkNavigationUp);
    guardrailHorizontal.copy(guardrailDelta).addScaledVector(walkNavigationUp, -verticalOffset);
    const horizontalLength = guardrailHorizontal.length();

    guardrailConstrained.copy(guardrailClosest);
    if (horizontalLength > 1e-10) {
      guardrailConstrained.addScaledVector(guardrailHorizontal, Math.min(horizontalLength, radius) / horizontalLength);
    }
    guardrailConstrained.addScaledVector(walkNavigationUp, clamp(verticalOffset, -verticalRadius, verticalRadius));

    guardrailCorrection.subVectors(guardrailConstrained, camera.position);
    const clamped = guardrailCorrection.lengthSq() > 1e-10;
    if (clamped) {
      camera.position.copy(guardrailConstrained);
    }
    lastGuardrailClamp = {
      clamped,
      distance: Number(Math.sqrt(nearest.distanceSq).toFixed(6)),
      radius: Number(radius.toFixed(6)),
      verticalOffset: Number(verticalOffset.toFixed(6)),
      mode: guardrailMode,
    };
    return clamped;
  }

  function applyDefaultView() {
    controls.target.set(0, 0, 0);
    camera.up.set(0, 1, 0);
    camera.position.copy(defaultCameraPosition);
    camera.fov = 48;
    camera.near = 0.01;
    camera.far = 100;
    camera.updateProjectionMatrix();
    controls.update();
    setWalkBasisFromCamera();
    applyWalkLook();
  }

  function applyCameraView(index = activeCameraViewIndex) {
    if (!fitState || !cameraViews.length) return false;
    const pose = readCameraViewPose(index);
    if (!pose) return false;
    activeCameraViewIndex = index;
    guidedProgress = index;
    return applyCameraPose(pose.rawPosition, pose.forward, pose.up, pose.fovYDegrees);
  }

  function fitSplat(mesh) {
    const box = mesh.getBoundingBox(true);
    const center = new THREE.Vector3();
    const size = new THREE.Vector3();
    let scale = 1;
    let maxExtent = 1;

    if (validBox(box)) {
      box.getCenter(center);
      box.getSize(size);
      maxExtent = Math.max(size.x, size.y, size.z, 1e-6);
      scale = 1.62 / maxExtent;
    }

    fitState = { center, scale, maxExtent };
    mesh.scale.setScalar(scale);
    mesh.position.set(-center.x * scale, -center.y * scale, -center.z * scale);
    mesh.updateMatrixWorld(true);

    buildNavigationGuardrails();
    if (!applyCameraView(activeCameraViewIndex)) applyDefaultView();
    setNavigationMode(navigationMode);
    setGuardrailMode(guardrailMode);
  }

  function walkButtonStep() {
    return scaledSceneExtent() * 0.05 * navigationSensitivity;
  }

  function orbitPanStep() {
    const distance = camera.position.distanceTo(controls.target);
    if (!Number.isFinite(distance)) return walkButtonStep();
    return clamp(distance * 0.032 * navigationSensitivity, walkButtonStep() * 0.35, maxButtonPanStep * navigationSensitivity);
  }

  function addLocalMovement(deltaRight = 0, deltaUp = 0, deltaForward = 0, step = walkButtonStep()) {
    camera.updateMatrixWorld(true);
    move.set(0, 0, 0);
    if (navigationMode === 'walk') {
      const basis = walkMovementBasis();
      forward.copy(basis.horizontalForward);
      right.copy(basis.horizontalRight);
      up.copy(basis.verticalUp);
    } else {
      camera.getWorldDirection(forward).normalize();
      right.setFromMatrixColumn(camera.matrixWorld, 0).normalize();
      up.copy(camera.up).normalize();
    }
    move
      .addScaledVector(right, deltaRight * step)
      .addScaledVector(up, deltaUp * step)
      .addScaledVector(forward, deltaForward * step);
    if (move.lengthSq() <= 1e-12) return false;
    camera.position.add(move);
    applyPositionGuardrail();
    return true;
  }

  async function load({ url, cameraViews: nextCameraViews = [] }) {
    if (!url) {
      setOverlay('No packaged splat', 'warning');
      return { status: 'missing' };
    }
    const cameraViewState = setCameraViews(nextCameraViews);
    if (loadedUrl === url && splat) {
      setOverlay('', 'pass');
      return { status: 'cached', ...cameraViewState };
    }

    setOverlay('Loading Spark renderer', 'neutral');
    if (splat) {
      scene.remove(splat);
      splat.dispose();
      splat = null;
    }

    const nextSplat = new SplatMesh({
      url,
      lod: false,
      onProgress: (event) => setOverlay(formatProgress(event), 'neutral'),
    });
    scene.add(nextSplat);
    splat = nextSplat;
    loadedUrl = url;

    await nextSplat.initialized;
    fitSplat(nextSplat);
    setOverlay('', 'pass');
    return {
      status: 'pass',
      splats: nextSplat.splats?.getNumSplats?.() ?? null,
      viewCount: cameraViews.length,
      activeViewIndex: activeCameraViewIndex,
      activeView: cameraViews[activeCameraViewIndex] ?? null,
    };
  }

  function pan(deltaX, deltaY) {
    const step = navigationMode === 'walk' ? walkButtonStep() : orbitPanStep();
    if (!addLocalMovement(deltaX, deltaY, 0, step)) return;
    if (navigationMode === 'walk') {
      syncTargetToCamera();
      return;
    }
    controls.target.add(move);
    controls.update();
  }

  function orbit(deltaX, deltaY) {
    if (navigationMode === 'walk') {
      rotateWalk(deltaX * walkButtonLookPixels, deltaY * walkButtonLookPixels);
      return;
    }
    target.copy(controls.target);
    offset.copy(camera.position).sub(target);
    spherical.setFromVector3(offset);
    spherical.theta += deltaX * orbitButtonRadians * navigationSensitivity;
    spherical.phi = clamp(spherical.phi + deltaY * orbitButtonRadians * navigationSensitivity, 0.08, Math.PI - 0.08);
    offset.setFromSpherical(spherical);
    camera.position.copy(target).add(offset);
    controls.update();
  }

  function zoom(factor) {
    if (navigationMode === 'walk') {
      moveAlongView(factor > 1 ? walkButtonStep() * 1.25 : -walkButtonStep() * 1.25);
      return;
    }
    target.copy(controls.target);
    offset.copy(camera.position).sub(target);
    const distance = offset.length();
    const adjustedFactor = 1 + ((factor - 1) * navigationSensitivity);
    const nextDistance = clamp(
      Number.isFinite(distance) ? distance / adjustedFactor : 1,
      controls.minDistance,
      Math.min(controls.maxDistance, 8),
    );
    if (offset.lengthSq() <= 1e-12) offset.set(0, 0, nextDistance);
    else offset.setLength(nextDistance);
    camera.position.copy(target).add(offset);
    controls.update();
  }

  function reset() {
    if (splat) fitSplat(splat);
    else {
      applyDefaultView();
    }
  }

  function setCameraView(index) {
    if (!cameraViews.length) return { status: 'missing', viewCount: 0 };
    const nextIndex = (index + cameraViews.length) % cameraViews.length;
    const applied = applyCameraView(nextIndex);
    return {
      status: applied ? 'pass' : 'fail',
      viewCount: cameraViews.length,
      activeViewIndex: activeCameraViewIndex,
      activeView: cameraViews[activeCameraViewIndex] ?? null,
    };
  }

  function nextCameraView(delta) {
    return setCameraView(activeCameraViewIndex + delta);
  }

  function keyboardTargetIsEditable(event) {
    const element = event.target;
    if (!(element instanceof HTMLElement)) return false;
    return ['INPUT', 'TEXTAREA', 'SELECT'].includes(element.tagName) || element.isContentEditable;
  }

  function isWalkKey(code) {
    return [
      'KeyW',
      'KeyA',
      'KeyS',
      'KeyD',
      'KeyQ',
      'KeyE',
      'Space',
      'ShiftLeft',
      'ShiftRight',
      'ControlLeft',
      'ControlRight',
    ].includes(code);
  }

  function updateGuidedKeyboard() {
    if (guardrailMode !== 'guided' || navigationMode !== 'walk' || !pressedKeys.size || !cameraViews.length) {
      return false;
    }
    const now = performance.now();
    if (now - lastGuidedKeyStepMs < 140) return true;
    let direction = 0;
    if (pressedKeys.has('KeyW') || pressedKeys.has('KeyD') || pressedKeys.has('KeyE') || pressedKeys.has('Space')) {
      direction += 1;
    }
    if (pressedKeys.has('KeyS') || pressedKeys.has('KeyA') || pressedKeys.has('KeyQ')) {
      direction -= 1;
    }
    if (direction !== 0) {
      nextCameraView(direction > 0 ? 1 : -1);
      lastGuidedKeyStepMs = now;
    }
    return true;
  }

  function canUseWalkKeyboard(event) {
    if (navigationMode !== 'walk' || keyboardTargetIsEditable(event)) return false;
    return true;
  }

  function onKeyDown(event) {
    if (!isWalkKey(event.code) || !canUseWalkKeyboard(event)) return;
    pressedKeys.add(event.code);
    event.preventDefault();
  }

  function onKeyUp(event) {
    if (!isWalkKey(event.code)) return;
    pressedKeys.delete(event.code);
  }

  function updateWalkMovement(deltaSeconds) {
    if (navigationMode !== 'walk' || !pressedKeys.size) return;
    if (updateGuidedKeyboard()) return;
    move.set(0, 0, 0);
    const basis = walkMovementBasis();
    forward.copy(basis.horizontalForward);
    right.copy(basis.horizontalRight);
    up.copy(basis.verticalUp);
    if (pressedKeys.has('KeyW')) move.add(forward);
    if (pressedKeys.has('KeyS')) move.sub(forward);
    if (pressedKeys.has('KeyD')) move.add(right);
    if (pressedKeys.has('KeyA')) move.sub(right);
    if (pressedKeys.has('KeyE') || pressedKeys.has('Space')) move.add(up);
    if (pressedKeys.has('KeyQ')) move.sub(up);
    if (move.lengthSq() <= 1e-12) return;

    const fast = pressedKeys.has('ShiftLeft') || pressedKeys.has('ShiftRight');
    const slow = pressedKeys.has('ControlLeft') || pressedKeys.has('ControlRight');
    const speed = scaledSceneExtent() * 0.24 * navigationSensitivity * (fast ? 3.2 : 1) * (slow ? 0.3 : 1);
    move.normalize().multiplyScalar(speed * deltaSeconds);
    camera.position.add(move);
    applyPositionGuardrail();
    syncTargetToCamera();
  }

  function moveAlongView(amount) {
    if (navigationMode !== 'walk') return;
    camera.updateMatrixWorld(true);
    camera.getWorldDirection(forward).normalize();
    camera.position.addScaledVector(forward, amount);
    applyPositionGuardrail();
    syncTargetToCamera();
  }

  function onPointerDown(event) {
    if (navigationMode !== 'walk' || event.button !== 0) return;
    canvas.focus({ preventScroll: true });
    draggingLook = true;
    lastPointerX = event.clientX;
    lastPointerY = event.clientY;
    canvas.setPointerCapture(event.pointerId);
  }

  function onPointerMove(event) {
    if (navigationMode !== 'walk') return;
    if (!draggingLook) return;
    rotateWalk(event.clientX - lastPointerX, event.clientY - lastPointerY);
    lastPointerX = event.clientX;
    lastPointerY = event.clientY;
  }

  function onLockedMouseMove(event) {
    if (navigationMode !== 'walk' || document.pointerLockElement !== canvas) return;
    rotateWalk(event.movementX, event.movementY);
  }

  function onPointerUp(event) {
    if (!draggingLook) return;
    draggingLook = false;
    if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
  }

  function onDoubleClick() {
    if (navigationMode === 'walk' && document.pointerLockElement !== canvas) {
      canvas.requestPointerLock?.();
    }
  }

  function onWheel(event) {
    if (navigationMode !== 'walk') return;
    event.preventDefault();
    const amount = scaledSceneExtent() * 0.065 * navigationSensitivity;
    moveAlongView(event.deltaY > 0 ? -amount : amount);
  }

  function vectorSnapshot(vector) {
    return [vector.x, vector.y, vector.z].map((value) => Number(value.toFixed(6)));
  }

  function signedCameraRollDegrees() {
    camera.updateMatrixWorld(true);
    camera.getWorldDirection(forward).normalize();
    projectedUp.copy(walkNavigationUp).addScaledVector(forward, -walkNavigationUp.dot(forward));
    projectedCameraUp.copy(camera.up).addScaledVector(forward, -camera.up.dot(forward));
    if (projectedUp.lengthSq() <= 1e-10 || projectedCameraUp.lengthSq() <= 1e-10) return 0;
    projectedUp.normalize();
    projectedCameraUp.normalize();
    const sine = forward.dot(projectedUp.clone().cross(projectedCameraUp));
    const cosine = clamp(projectedUp.dot(projectedCameraUp), -1, 1);
    return THREE.MathUtils.radToDeg(Math.atan2(sine, cosine));
  }

  function getNavigationState() {
    camera.updateMatrixWorld(true);
    return {
      mode: navigationMode,
      position: vectorSnapshot(camera.position),
      target: vectorSnapshot(controls.target),
      up: vectorSnapshot(camera.up),
      navigationUp: vectorSnapshot(walkNavigationUp),
      rollDegrees: Number(signedCameraRollDegrees().toFixed(4)),
      targetDistance: Number(camera.position.distanceTo(controls.target).toFixed(6)),
      walkFocusDistance: Number(walkFocusDistance.toFixed(6)),
      navigationSensitivity: Number(navigationSensitivity.toFixed(3)),
      guardrailMode,
      guidedPlaying,
      guidedProgress: Number(guidedProgress.toFixed(3)),
      guardrail: guardrailState ? {
        viewCount: guardrailState.points.length,
        safeRadius: Number(guardrailState.safeRadius.toFixed(6)),
        guidedRadius: Number(guardrailState.guidedRadius.toFixed(6)),
        verticalRadius: Number(guardrailState.verticalRadius.toFixed(6)),
        lastClamp: lastGuardrailClamp,
      } : null,
      fov: Number(camera.fov.toFixed(6)),
      activeCameraViewIndex,
      viewCount: cameraViews.length,
    };
  }

  function frame(now = performance.now()) {
    if (disposed) return;
    if (document.hidden) return;
    if (now - lastRenderMs < minFrameMs) return;
    const deltaSeconds = Math.min((now - lastRenderMs) / 1000, 0.08);
    lastRenderMs = now;
    resize();
    updateGuidedAnimation(deltaSeconds);
    updateWalkMovement(deltaSeconds);
    controls.update();
    renderer.render(scene, camera);
  }

  document.addEventListener('keydown', onKeyDown);
  document.addEventListener('keyup', onKeyUp);
  document.addEventListener('mousemove', onLockedMouseMove);
  canvas.addEventListener('pointerdown', onPointerDown);
  canvas.addEventListener('pointermove', onPointerMove);
  canvas.addEventListener('pointerup', onPointerUp);
  canvas.addEventListener('pointercancel', onPointerUp);
  canvas.addEventListener('dblclick', onDoubleClick);
  canvas.addEventListener('wheel', onWheel, { passive: false });
  renderer.setAnimationLoop(frame);
  setNavigationSensitivity(defaultNavigationSensitivity);

  return {
    load,
    setNavigationMode,
    setGuardrailMode,
    setGuidedPlayback,
    setNavigationSensitivity,
    setCameraViews,
    previousCameraView: () => nextCameraView(-1),
    nextCameraView: () => nextCameraView(1),
    pan,
    orbit,
    lookPixels: rotateWalk,
    zoom,
    reset,
    getNavigationState,
    dispose() {
      disposed = true;
      renderer.setAnimationLoop(null);
      if (splat) splat.dispose();
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('keyup', onKeyUp);
      document.removeEventListener('mousemove', onLockedMouseMove);
      canvas.removeEventListener('pointerdown', onPointerDown);
      canvas.removeEventListener('pointermove', onPointerMove);
      canvas.removeEventListener('pointerup', onPointerUp);
      canvas.removeEventListener('pointercancel', onPointerUp);
      canvas.removeEventListener('dblclick', onDoubleClick);
      canvas.removeEventListener('wheel', onWheel);
      controls.dispose();
      renderer.dispose();
    },
  };
}
