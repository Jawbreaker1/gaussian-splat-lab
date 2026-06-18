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
  const walkButtonLookPixels = 34;
  const orbitButtonRadians = 0.042;
  const maxButtonPanStep = 0.095;

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
  let draggingLook = false;
  let lastPointerX = 0;
  let lastPointerY = 0;
  let walkYaw = 0;
  let walkPitch = 0;
  let walkFocusDistance = 1;
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
  const walkBaseUp = new THREE.Vector3();
  const walkBaseRight = new THREE.Vector3();
  const walkYawQuat = new THREE.Quaternion();
  const walkPitchQuat = new THREE.Quaternion();
  const pressedKeys = new Set();
  const spherical = new THREE.Spherical();

  canvas.tabIndex = canvas.tabIndex >= 0 ? canvas.tabIndex : 0;

  function setOverlay(text, type = 'neutral') {
    overlay.textContent = text;
    overlay.hidden = !text;
    overlay.dataset.type = type;
    onStatus?.(text, type);
  }

  function resize() {
    const rect = canvas.parentElement.getBoundingClientRect();
    const width = Math.max(1, Math.floor(rect.width));
    const height = Math.max(1, Math.floor(rect.height));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function setWalkBasisFromCamera() {
    camera.getWorldDirection(walkBaseForward).normalize();
    walkBaseUp.copy(camera.up).normalize();
    walkBaseRight.crossVectors(walkBaseForward, walkBaseUp);
    if (walkBaseRight.lengthSq() <= 1e-10) {
      walkBaseRight.setFromMatrixColumn(camera.matrixWorld, 0);
    }
    walkBaseRight.normalize();
    walkBaseUp.crossVectors(walkBaseRight, walkBaseForward).normalize();
    walkYaw = 0;
    walkPitch = 0;
    walkFocusDistance = clamp(camera.position.distanceTo(controls.target) || 1, 0.08, 8);
  }

  function syncTargetToCamera() {
    camera.updateMatrixWorld(true);
    camera.getWorldDirection(forward).normalize();
    controls.target.copy(camera.position).add(forward.multiplyScalar(walkFocusDistance));
  }

  function applyWalkLook() {
    walkYawQuat.setFromAxisAngle(walkBaseUp, walkYaw);
    const yawedForward = walkBaseForward.clone().applyQuaternion(walkYawQuat).normalize();
    const yawedRight = walkBaseRight.clone().applyQuaternion(walkYawQuat).normalize();
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
    const sensitivity = 0.0021;
    walkYaw -= deltaX * sensitivity;
    walkPitch = clamp(walkPitch - deltaY * sensitivity, -1.42, 1.42);
    applyWalkLook();
  }

  function setNavigationMode(mode = 'walk') {
    navigationMode = mode === 'orbit' ? 'orbit' : 'walk';
    controls.enabled = navigationMode === 'orbit';
    draggingLook = false;
    pressedKeys.clear();
    if (navigationMode === 'walk') {
      setWalkBasisFromCamera();
      syncTargetToCamera();
    }
    return { mode: navigationMode };
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
    if (changed) activeCameraViewIndex = 0;
    if (activeCameraViewIndex >= cameraViews.length) activeCameraViewIndex = 0;
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
  }

  function applyCameraView(index = activeCameraViewIndex) {
    if (!fitState || !cameraViews.length) return false;
    const view = cameraViews[index];
    const rawPosition = vectorFromArray(view?.position);
    const forward = normalizeVector(view?.forward);
    const cameraUp = normalizeVector(view?.up);
    if (!rawPosition || !forward || !cameraUp) return false;

    activeCameraViewIndex = index;
    const centerOffset = fitState.center.clone().sub(rawPosition);
    let focusDistance = centerOffset.dot(forward);
    const minFocusDistance = fitState.maxExtent * 0.04;
    if (!Number.isFinite(focusDistance) || focusDistance < minFocusDistance) {
      focusDistance = Math.max(fitState.maxExtent * 0.62, 0.25);
    }

    const rawTarget = rawPosition.clone().add(forward.clone().multiplyScalar(focusDistance));
    const nextPosition = transformRawPoint(rawPosition);
    const nextTarget = transformRawPoint(rawTarget);
    camera.up.copy(cameraUp);
    camera.position.copy(nextPosition);
    camera.fov = clamp(Number(view.fovYDegrees) || 48, 20, 85);
    camera.near = 0.002;
    camera.far = 100;
    camera.updateProjectionMatrix();
    camera.lookAt(nextTarget);
    camera.updateMatrixWorld(true);
    controls.target.copy(nextTarget);
    controls.update();
    setWalkBasisFromCamera();
    return true;
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

    if (!applyCameraView(activeCameraViewIndex)) applyDefaultView();
    setNavigationMode(navigationMode);
  }

  function scaledSceneExtent() {
    if (!fitState) return 1.62;
    return clamp(fitState.maxExtent * fitState.scale, 0.6, 2.4);
  }

  function walkButtonStep() {
    return scaledSceneExtent() * 0.05;
  }

  function orbitPanStep() {
    const distance = camera.position.distanceTo(controls.target);
    if (!Number.isFinite(distance)) return walkButtonStep();
    return clamp(distance * 0.032, walkButtonStep() * 0.35, maxButtonPanStep);
  }

  function addLocalMovement(deltaRight = 0, deltaUp = 0, deltaForward = 0, step = walkButtonStep()) {
    camera.updateMatrixWorld(true);
    move.set(0, 0, 0);
    camera.getWorldDirection(forward).normalize();
    right.setFromMatrixColumn(camera.matrixWorld, 0).normalize();
    up.copy(camera.up).normalize();
    move
      .addScaledVector(right, deltaRight * step)
      .addScaledVector(up, deltaUp * step)
      .addScaledVector(forward, deltaForward * step);
    if (move.lengthSq() <= 1e-12) return false;
    camera.position.add(move);
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
    spherical.theta += deltaX * orbitButtonRadians;
    spherical.phi = clamp(spherical.phi + deltaY * orbitButtonRadians, 0.08, Math.PI - 0.08);
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
    const nextDistance = clamp(
      Number.isFinite(distance) ? distance / factor : 1,
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
    move.set(0, 0, 0);
    camera.updateMatrixWorld(true);
    camera.getWorldDirection(forward).normalize();
    right.setFromMatrixColumn(camera.matrixWorld, 0).normalize();
    up.copy(camera.up).normalize();
    if (pressedKeys.has('KeyW')) move.add(forward);
    if (pressedKeys.has('KeyS')) move.sub(forward);
    if (pressedKeys.has('KeyD')) move.add(right);
    if (pressedKeys.has('KeyA')) move.sub(right);
    if (pressedKeys.has('KeyE') || pressedKeys.has('Space')) move.add(up);
    if (pressedKeys.has('KeyQ')) move.sub(up);
    if (move.lengthSq() <= 1e-12) return;

    const fast = pressedKeys.has('ShiftLeft') || pressedKeys.has('ShiftRight');
    const slow = pressedKeys.has('ControlLeft') || pressedKeys.has('ControlRight');
    const speed = scaledSceneExtent() * 0.34 * (fast ? 3.2 : 1) * (slow ? 0.3 : 1);
    move.normalize().multiplyScalar(speed * deltaSeconds);
    camera.position.add(move);
    syncTargetToCamera();
  }

  function moveAlongView(amount) {
    if (navigationMode !== 'walk') return;
    camera.updateMatrixWorld(true);
    camera.getWorldDirection(forward).normalize();
    camera.position.addScaledVector(forward, amount);
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
    moveAlongView(event.deltaY > 0 ? -0.11 : 0.11);
  }

  function vectorSnapshot(vector) {
    return [vector.x, vector.y, vector.z].map((value) => Number(value.toFixed(6)));
  }

  function getNavigationState() {
    camera.updateMatrixWorld(true);
    return {
      mode: navigationMode,
      position: vectorSnapshot(camera.position),
      target: vectorSnapshot(controls.target),
      up: vectorSnapshot(camera.up),
      targetDistance: Number(camera.position.distanceTo(controls.target).toFixed(6)),
      walkFocusDistance: Number(walkFocusDistance.toFixed(6)),
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

  return {
    load,
    setNavigationMode,
    setCameraViews,
    previousCameraView: () => nextCameraView(-1),
    nextCameraView: () => nextCameraView(1),
    pan,
    orbit,
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
