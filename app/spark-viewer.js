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
  let disposed = false;
  let lastRenderMs = 0;
  const minFrameMs = 1000 / 24;
  const defaultCameraPosition = new THREE.Vector3(0.72, 0.34, 2.55);
  const right = new THREE.Vector3();
  const up = new THREE.Vector3();
  const move = new THREE.Vector3();
  const target = new THREE.Vector3();
  const offset = new THREE.Vector3();
  const spherical = new THREE.Spherical();

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
    controls.target.copy(nextTarget);
    controls.update();
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
    const distance = camera.position.distanceTo(controls.target);
    const step = distance * 0.055;
    right.setFromMatrixColumn(camera.matrix, 0).multiplyScalar(deltaX * step);
    up.setFromMatrixColumn(camera.matrix, 1).multiplyScalar(deltaY * step);
    move.copy(right).add(up);
    camera.position.add(move);
    controls.target.add(move);
    controls.update();
  }

  function orbit(deltaX, deltaY) {
    target.copy(controls.target);
    offset.copy(camera.position).sub(target);
    spherical.setFromVector3(offset);
    spherical.theta += deltaX * 0.16;
    spherical.phi = clamp(spherical.phi + deltaY * 0.16, 0.08, Math.PI - 0.08);
    offset.setFromSpherical(spherical);
    camera.position.copy(target).add(offset);
    controls.update();
  }

  function zoom(factor) {
    target.copy(controls.target);
    offset.copy(camera.position).sub(target);
    offset.multiplyScalar(1 / factor);
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

  function frame(now = performance.now()) {
    if (disposed) return;
    if (document.hidden) return;
    if (now - lastRenderMs < minFrameMs) return;
    lastRenderMs = now;
    resize();
    controls.update();
    renderer.render(scene, camera);
  }

  renderer.setAnimationLoop(frame);

  return {
    load,
    setCameraViews,
    previousCameraView: () => nextCameraView(-1),
    nextCameraView: () => nextCameraView(1),
    pan,
    orbit,
    zoom,
    reset,
    dispose() {
      disposed = true;
      renderer.setAnimationLoop(null);
      if (splat) splat.dispose();
      controls.dispose();
      renderer.dispose();
    },
  };
}
