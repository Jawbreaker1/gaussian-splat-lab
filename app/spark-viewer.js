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
  controls.minDistance = 0.25;
  controls.maxDistance = 8;

  const grid = new THREE.GridHelper(2.2, 16, 0x315c66, 0x24323a);
  grid.position.y = -0.82;
  grid.material.transparent = true;
  grid.material.opacity = 0.42;
  scene.add(grid);

  const axes = new THREE.AxesHelper(0.9);
  axes.position.y = -0.78;
  scene.add(axes);

  let splat = null;
  let loadedUrl = null;
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

  function fitSplat(mesh) {
    const box = mesh.getBoundingBox(true);
    const center = new THREE.Vector3();
    const size = new THREE.Vector3();
    let scale = 1;

    if (validBox(box)) {
      box.getCenter(center);
      box.getSize(size);
      const maxExtent = Math.max(size.x, size.y, size.z, 1e-6);
      scale = 1.62 / maxExtent;
    }

    mesh.scale.setScalar(scale);
    mesh.position.set(-center.x * scale, -center.y * scale, -center.z * scale);
    mesh.updateMatrixWorld(true);

    controls.target.set(0, 0, 0);
    camera.position.copy(defaultCameraPosition);
    camera.near = 0.01;
    camera.far = 100;
    camera.updateProjectionMatrix();
    controls.update();
  }

  async function load({ url }) {
    if (!url) {
      setOverlay('No packaged splat', 'warning');
      return { status: 'missing' };
    }
    if (loadedUrl === url && splat) {
      setOverlay('', 'pass');
      return { status: 'cached' };
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
      controls.target.set(0, 0, 0);
      camera.position.copy(defaultCameraPosition);
      controls.update();
    }
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
