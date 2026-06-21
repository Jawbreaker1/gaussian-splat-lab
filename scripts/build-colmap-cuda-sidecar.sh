#!/usr/bin/env bash
set -euo pipefail

# Build a CUDA-capable COLMAP beside the known-good apt package.
#
# This intentionally installs into outputs/tools/colmap-cuda by default so the
# Ubuntu /usr/bin/colmap CPU fallback stays untouched and easy to return to.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

colmap_ref="${COLMAP_REF:-4.0.4}"
build_root="${GSL_COLMAP_BUILD_ROOT:-${repo_root}/outputs/build/colmap-cuda}"
install_prefix="${GSL_COLMAP_PREFIX:-${repo_root}/outputs/tools/colmap-cuda}"
cuda_home="${CUDA_HOME:-/usr/local/cuda-12.8}"
cuda_architectures="${COLMAP_CUDA_ARCHITECTURES:-native}"
build_jobs="${GSL_COLMAP_BUILD_JOBS:-$(nproc)}"

src_dir="${build_root}/src"
build_dir="${build_root}/build"

missing=()
for tool in git cmake ninja g++; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    missing+=("${tool}")
  fi
done

if [[ ! -x "${cuda_home}/bin/nvcc" ]]; then
  missing+=("${cuda_home}/bin/nvcc")
fi

if [[ ! -d "/usr/include/opencv4" ]]; then
  missing+=("libopencv-dev:/usr/include/opencv4")
fi

if [[ ! -f "${cuda_home}/include/curand.h" ]]; then
  missing+=("libcurand-dev-12-8:${cuda_home}/include/curand.h")
fi

if [[ ! -e "${cuda_home}/lib64/libcurand.so" ]]; then
  missing+=("libcurand-dev-12-8:${cuda_home}/lib64/libcurand.so")
fi

if (( ${#missing[@]} > 0 )); then
  printf 'missing_build_tools=%s\n' "${missing[*]}" >&2
  printf 'Install the documented sidecar build dependencies before running this script.\n' >&2
  exit 2
fi

printf 'colmap_ref=%s\n' "${colmap_ref}"
printf 'build_root=%s\n' "${build_root}"
printf 'install_prefix=%s\n' "${install_prefix}"
printf 'cuda_home=%s\n' "${cuda_home}"
printf 'cuda_architectures=%s\n' "${cuda_architectures}"
printf 'build_jobs=%s\n' "${build_jobs}"
printf 'note=%s\n' "This compiles COLMAP from source and can keep many CPU cores busy for a long time."

mkdir -p "${build_root}" "${install_prefix}"

if [[ ! -d "${src_dir}/.git" ]]; then
  git clone --depth 1 --branch "${colmap_ref}" https://github.com/colmap/colmap.git "${src_dir}"
else
  git -C "${src_dir}" fetch --depth 1 origin "${colmap_ref}"
  git -C "${src_dir}" checkout FETCH_HEAD
fi

cmake \
  -S "${src_dir}" \
  -B "${build_dir}" \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="${install_prefix}" \
  -DCMAKE_CUDA_COMPILER="${cuda_home}/bin/nvcc" \
  -DCMAKE_CUDA_ARCHITECTURES="${cuda_architectures}" \
  -DCUDA_ENABLED=ON \
  -DONNX_ENABLED=OFF \
  -DGUI_ENABLED=OFF \
  -DOPENGL_ENABLED=OFF \
  -DCGAL_ENABLED=OFF \
  -DTESTS_ENABLED=OFF \
  -DBENCHMARK_ENABLED=OFF \
  -DIPO_ENABLED=OFF \
  -DCCACHE_ENABLED=OFF

cmake --build "${build_dir}" --parallel "${build_jobs}"
cmake --install "${build_dir}"

"${install_prefix}/bin/colmap" --help >/dev/null

printf 'colmap_cuda_binary=%s\n' "${install_prefix}/bin/colmap"
printf 'validate_cpu=%s\n' "python3 scripts/validate-colmap-binary.py --binary ${install_prefix}/bin/colmap"
printf 'validate_gpu=%s\n' "python3 scripts/validate-colmap-binary.py --binary ${install_prefix}/bin/colmap --allow-gpu --qt-offscreen"
