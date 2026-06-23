#!/usr/bin/env python3
"""Non-destructive Gaussian Splat PLY cleanup experiments.

The script keeps the source PLY intact and writes sibling variant PLY files plus
an analysis report. When given a viewer manifest it appends artifactVariants so
the browser gallery can switch between raw/default/cleaned results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PLY_PROPERTY_SIZES = {
    "char": 1,
    "int8": 1,
    "uchar": 1,
    "uint8": 1,
    "short": 2,
    "int16": 2,
    "ushort": 2,
    "uint16": 2,
    "int": 4,
    "int32": 4,
    "uint": 4,
    "uint32": 4,
    "float": 4,
    "float32": 4,
    "double": 8,
    "float64": 8,
}

PLY_PROPERTY_FORMATS = {
    "char": "b",
    "int8": "b",
    "uchar": "B",
    "uint8": "B",
    "short": "h",
    "int16": "h",
    "ushort": "H",
    "uint16": "H",
    "int": "i",
    "int32": "i",
    "uint": "I",
    "uint32": "I",
    "float": "f",
    "float32": "f",
    "double": "d",
    "float64": "d",
}

CLEANUP_PROFILES: dict[str, dict[str, Any]] = {
    "conservative": {
        "label": "Clean conservative",
        "minOpacity": 0.015,
        "averageScalePercentile": 0.999,
        "maxScalePercentile": 0.9995,
        "anisotropyPercentile": 0.9995,
        "boundsLowPercentile": 0.0005,
        "boundsHighPercentile": 0.9995,
        "boundsPaddingRatio": 0.4,
        "minKeepRatio": 0.9,
    },
    "balanced": {
        "label": "Clean balanced",
        "minOpacity": 0.025,
        "averageScalePercentile": 0.997,
        "maxScalePercentile": 0.998,
        "anisotropyPercentile": 0.998,
        "boundsLowPercentile": 0.001,
        "boundsHighPercentile": 0.999,
        "boundsPaddingRatio": 0.25,
        "minKeepRatio": 0.72,
    },
    "aggressive": {
        "label": "Clean aggressive",
        "minOpacity": 0.04,
        "averageScalePercentile": 0.992,
        "maxScalePercentile": 0.995,
        "anisotropyPercentile": 0.995,
        "boundsLowPercentile": 0.003,
        "boundsHighPercentile": 0.997,
        "boundsPaddingRatio": 0.18,
        "minKeepRatio": 0.45,
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def repo_relative_path(path: Path) -> str | None:
    try:
        return path.resolve().relative_to(repo_root_from_script().resolve()).as_posix()
    except ValueError:
        return None


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sigmoid(value: float) -> float:
    if value >= 0:
        exponent = math.exp(-value)
        return 1 / (1 + exponent)
    exponent = math.exp(value)
    return exponent / (1 + exponent)


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("cannot calculate percentile for empty list")
    ordered = sorted(values)
    index = round((len(ordered) - 1) * min(1.0, max(0.0, fraction)))
    return ordered[index]


def parse_binary_ply_layout(data: bytes) -> dict[str, Any]:
    marker = b"end_header"
    marker_index = data.find(marker)
    if marker_index < 0:
        raise ValueError("PLY header does not contain end_header")
    header_end = marker_index + len(marker)
    while header_end < len(data) and data[header_end] in (10, 13):
        header_end += 1

    header = data[:header_end].decode("ascii", errors="replace")
    lines = header.splitlines()
    ply_format = None
    vertex_count = None
    in_vertex = False
    properties: list[dict[str, Any]] = []
    for line in lines:
        fields = line.strip().split()
        if len(fields) >= 2 and fields[0] == "format":
            ply_format = fields[1]
        elif len(fields) >= 3 and fields[0] == "element":
            in_vertex = fields[1] == "vertex"
            if in_vertex:
                vertex_count = int(fields[2])
        elif in_vertex and len(fields) >= 3 and fields[0] == "property":
            property_type = fields[1]
            if property_type == "list":
                raise ValueError("PLY vertex list properties are not supported")
            size = PLY_PROPERTY_SIZES.get(property_type)
            fmt = PLY_PROPERTY_FORMATS.get(property_type)
            if size is None or fmt is None:
                raise ValueError(f"unsupported PLY property type {property_type}")
            properties.append({"name": fields[2], "type": property_type, "size": size, "format": fmt, "offset": 0})

    if ply_format != "binary_little_endian":
        raise ValueError(f"unsupported PLY format {ply_format or 'unknown'}")
    if vertex_count is None or vertex_count <= 0:
        raise ValueError("PLY vertex count is empty")

    stride = 0
    for prop in properties:
        prop["offset"] = stride
        stride += prop["size"]
    properties_by_name = {prop["name"]: prop for prop in properties}
    for required in ("x", "y", "z"):
        if required not in properties_by_name:
            raise ValueError(f"PLY missing {required}")

    vertex_bytes_end = header_end + vertex_count * stride
    if vertex_bytes_end > len(data):
        raise ValueError("PLY vertex data is shorter than declared vertex count")

    return {
        "header": header,
        "headerEnd": header_end,
        "vertexCount": vertex_count,
        "properties": properties,
        "propertiesByName": properties_by_name,
        "stride": stride,
        "vertexBytesEnd": vertex_bytes_end,
        "format": ply_format,
    }


def read_ply_property(view: memoryview, base: int, prop: dict[str, Any]) -> float:
    return float(struct.unpack_from("<" + prop["format"], view, base + int(prop["offset"]))[0])


def replace_ply_vertex_count(header: str, vertex_count: int) -> bytes:
    lines = []
    replaced = False
    for line in header.splitlines():
        fields = line.strip().split()
        if len(fields) >= 3 and fields[0] == "element" and fields[1] == "vertex":
            lines.append(f"element vertex {vertex_count}")
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        raise ValueError("PLY header has no vertex element")
    return ("\n".join(lines) + "\n").encode("ascii")


def ply_header_summary(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        prefix = handle.read(65536)
    marker = b"end_header"
    marker_index = prefix.find(marker)
    if marker_index < 0:
        return {"status": "fail", "summary": "PLY header does not contain end_header"}
    line_end = prefix.find(b"\n", marker_index)
    header = prefix[: line_end + 1 if line_end >= 0 else marker_index + len(marker)].decode("ascii", errors="replace")
    vertex_count = None
    ply_format = None
    properties: list[str] = []
    in_vertex = False
    for line in header.splitlines():
        fields = line.strip().split()
        if len(fields) >= 2 and fields[0] == "format":
            ply_format = fields[1]
        elif len(fields) >= 3 and fields[0] == "element":
            in_vertex = fields[1] == "vertex"
            if in_vertex:
                vertex_count = int(fields[2])
        elif in_vertex and len(fields) >= 3 and fields[0] == "property":
            properties.append(fields[-1])
    return {
        "status": "pass" if ply_format and vertex_count is not None else "fail",
        "summary": "PLY header is readable" if ply_format and vertex_count is not None else "PLY header is incomplete",
        "format": ply_format,
        "vertexCount": vertex_count,
        "properties": properties,
    }


def scan_records(data: bytes, layout: dict[str, Any]) -> dict[str, Any]:
    props = layout["propertiesByName"]
    stride = int(layout["stride"])
    header_end = int(layout["headerEnd"])
    vertex_count = int(layout["vertexCount"])
    view = memoryview(data)
    has_opacity = "opacity" in props
    has_scale = all(name in props for name in ("scale_0", "scale_1", "scale_2"))
    records: list[dict[str, float]] = []
    average_scales: list[float] = []
    max_scales: list[float] = []
    anisotropies: list[float] = []
    coordinates = {"x": [], "y": [], "z": []}
    for index in range(vertex_count):
        base = header_end + index * stride
        x = read_ply_property(view, base, props["x"])
        y = read_ply_property(view, base, props["y"])
        z = read_ply_property(view, base, props["z"])
        opacity = sigmoid(read_ply_property(view, base, props["opacity"])) if has_opacity else 1.0
        if has_scale:
            scales = [
                math.exp(read_ply_property(view, base, props["scale_0"])),
                math.exp(read_ply_property(view, base, props["scale_1"])),
                math.exp(read_ply_property(view, base, props["scale_2"])),
            ]
            average_scale = sum(scales) / 3
            max_scale = max(scales)
            min_scale = max(min(scales), 1.0e-12)
            anisotropy = max_scale / min_scale
        else:
            average_scale = 0.0
            max_scale = 0.0
            anisotropy = 1.0
        records.append(
            {
                "index": float(index),
                "x": x,
                "y": y,
                "z": z,
                "opacity": opacity,
                "averageScale": average_scale,
                "maxScale": max_scale,
                "anisotropy": anisotropy,
            }
        )
        average_scales.append(average_scale)
        max_scales.append(max_scale)
        anisotropies.append(anisotropy)
        coordinates["x"].append(x)
        coordinates["y"].append(y)
        coordinates["z"].append(z)
    return {
        "records": records,
        "averageScales": average_scales,
        "maxScales": max_scales,
        "anisotropies": anisotropies,
        "coordinates": coordinates,
        "hasOpacity": has_opacity,
        "hasScale": has_scale,
    }


def profile_thresholds(scan: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    average_scales = scan["averageScales"]
    max_scales = scan["maxScales"]
    anisotropies = scan["anisotropies"]
    coordinates = scan["coordinates"]
    bounds = {}
    for axis in ("x", "y", "z"):
        low = percentile(coordinates[axis], float(profile["boundsLowPercentile"]))
        high = percentile(coordinates[axis], float(profile["boundsHighPercentile"]))
        padding = max((high - low) * float(profile["boundsPaddingRatio"]), 1.0e-6)
        bounds[axis] = (low - padding, high + padding)
    return {
        "minOpacity": float(profile["minOpacity"]),
        "maxAverageScale": percentile(average_scales, float(profile["averageScalePercentile"])) if scan["hasScale"] else float("inf"),
        "maxScale": percentile(max_scales, float(profile["maxScalePercentile"])) if scan["hasScale"] else float("inf"),
        "maxAnisotropy": percentile(anisotropies, float(profile["anisotropyPercentile"])) if scan["hasScale"] else float("inf"),
        "bounds": bounds,
    }


def classify_record(record: dict[str, float], thresholds: dict[str, Any]) -> list[str]:
    reasons = []
    if record["opacity"] < thresholds["minOpacity"]:
        reasons.append("low_opacity")
    if record["averageScale"] > thresholds["maxAverageScale"]:
        reasons.append("large_average_scale")
    if record["maxScale"] > thresholds["maxScale"]:
        reasons.append("large_axis_scale")
    if record["anisotropy"] > thresholds["maxAnisotropy"]:
        reasons.append("extreme_anisotropy")
    bounds = thresholds["bounds"]
    for axis in ("x", "y", "z"):
        if not (bounds[axis][0] <= record[axis] <= bounds[axis][1]):
            reasons.append("spatial_outlier")
            break
    return reasons


def rounded_bounds(bounds: dict[str, tuple[float, float]]) -> dict[str, list[float]]:
    return {axis: [round(pair[0], 6), round(pair[1], 6)] for axis, pair in bounds.items()}


def write_filtered_ply(source_data: bytes, layout: dict[str, Any], target: Path, kept_indices: list[int]) -> None:
    stride = int(layout["stride"])
    header_end = int(layout["headerEnd"])
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        handle.write(replace_ply_vertex_count(str(layout["header"]), len(kept_indices)))
        for index in kept_indices:
            base = header_end + index * stride
            handle.write(source_data[base : base + stride])
        tail_start = int(layout["vertexBytesEnd"])
        if tail_start < len(source_data):
            handle.write(source_data[tail_start:])


def artifact_info(path: Path, artifact_id: str, label: str, cleanup: dict[str, Any] | None = None) -> dict[str, Any]:
    info = {
        "id": artifact_id,
        "label": label,
        "kind": "gaussian_splat_ply",
        "format": "ply",
        "path": str(path),
        "repoRelativePath": repo_relative_path(path),
        "sizeBytes": path.stat().st_size,
        "sha256": file_sha256(path),
        "ply": ply_header_summary(path),
    }
    if cleanup is not None:
        info["postProcess"] = cleanup
    return info


def run_profile(source: Path, data: bytes, layout: dict[str, Any], scan: dict[str, Any], profile_name: str, output_dir: Path) -> dict[str, Any]:
    profile = CLEANUP_PROFILES[profile_name]
    thresholds = profile_thresholds(scan, profile)
    reason_counts: dict[str, int] = {}
    kept_indices = []
    removed_indices = []
    for record in scan["records"]:
        reasons = classify_record(record, thresholds)
        if reasons:
            removed_indices.append(int(record["index"]))
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        else:
            kept_indices.append(int(record["index"]))

    vertex_count = int(layout["vertexCount"])
    min_keep = max(1000, int(vertex_count * float(profile["minKeepRatio"])))
    safety_fallback = len(kept_indices) < min_keep
    if safety_fallback:
        kept_indices = list(range(vertex_count))
        removed_indices = []
        reason_counts = {"safety_fallback_kept_original": vertex_count}

    target = output_dir / f"{source.stem}.clean-{profile_name}.ply"
    write_filtered_ply(data, layout, target, kept_indices)
    return {
        "id": f"clean_{profile_name}",
        "label": str(profile["label"]),
        "status": "warning" if safety_fallback else "pass",
        "summary": (
            "safety fallback kept the full source because pruning would remove too much"
            if safety_fallback
            else f"kept {len(kept_indices)} of {vertex_count} splats"
        ),
        "sourcePath": str(source),
        "path": str(target),
        "repoRelativePath": repo_relative_path(target),
        "originalVertexCount": vertex_count,
        "vertexCount": len(kept_indices),
        "removedVertexCount": len(removed_indices),
        "keptRatio": round(len(kept_indices) / max(vertex_count, 1), 6),
        "removedRatio": round(len(removed_indices) / max(vertex_count, 1), 6),
        "reasonCounts": reason_counts,
        "profile": profile,
        "thresholds": {
            "minOpacity": thresholds["minOpacity"],
            "maxAverageScale": thresholds["maxAverageScale"] if math.isfinite(thresholds["maxAverageScale"]) else None,
            "maxScale": thresholds["maxScale"] if math.isfinite(thresholds["maxScale"]) else None,
            "maxAnisotropy": thresholds["maxAnisotropy"] if math.isfinite(thresholds["maxAnisotropy"]) else None,
            "bounds": rounded_bounds(thresholds["bounds"]),
        },
        "artifact": artifact_info(
            target,
            f"clean_{profile_name}",
            str(profile["label"]),
            {
                "method": "splat_quality_heuristics",
                "profile": profile_name,
                "status": "warning" if safety_fallback else "pass",
                "removedVertexCount": len(removed_indices),
                "removedRatio": round(len(removed_indices) / max(vertex_count, 1), 6),
                "reasonCounts": reason_counts,
            },
        ),
    }


def resolve_source(args: argparse.Namespace) -> tuple[Path, dict[str, Any] | None, Path | None]:
    manifest = None
    manifest_path = Path(args.manifest).resolve() if args.manifest else None
    if manifest_path:
        manifest = read_json(manifest_path)
    if args.source:
        source = Path(args.source).resolve()
    elif manifest:
        raw_path = manifest.get("artifact", {}).get("path")
        if not isinstance(raw_path, str) or not raw_path:
            raise ValueError("manifest does not declare artifact.path")
        source = Path(raw_path).resolve()
    else:
        raise ValueError("provide --source or --manifest")
    if not source.exists():
        raise FileNotFoundError(source)
    return source, manifest, manifest_path


def merge_manifest_variants(
    manifest: dict[str, Any],
    manifest_path: Path,
    profile_results: list[dict[str, Any]],
    report_path: Path,
) -> dict[str, Any]:
    artifact = manifest.get("artifact") if isinstance(manifest.get("artifact"), dict) else {}
    original = manifest.get("originalArtifact") if isinstance(manifest.get("originalArtifact"), dict) else {}
    variants = []
    if artifact.get("path"):
        variants.append(artifact_info(Path(artifact["path"]), "viewer_default", "Viewer default"))
    if original.get("path") and original.get("path") != artifact.get("path"):
        variants.append(artifact_info(Path(original["path"]), "original_export", "Original export"))
    variants.extend(result["artifact"] for result in profile_results)
    unique: dict[str, dict[str, Any]] = {}
    for variant in [*manifest.get("artifactVariants", []), *variants]:
        if isinstance(variant, dict) and variant.get("id"):
            unique[str(variant["id"])] = variant
    manifest["artifactVariants"] = list(unique.values())
    manifest["postProcessing"] = {
        "generatedAt": utc_now(),
        "method": "splat_quality_heuristics",
        "reportPath": str(report_path),
        "reportRepoRelativePath": repo_relative_path(report_path),
        "profiles": [result["id"] for result in profile_results],
        "note": "Non-destructive cleanup variants. The default artifact and original export are preserved.",
    }
    export = manifest.get("export") if isinstance(manifest.get("export"), dict) else {}
    includes = export.get("includes") if isinstance(export.get("includes"), list) else []
    if "postprocessed_artifact_variants" not in includes:
        includes.append("postprocessed_artifact_variants")
    export["includes"] = includes
    manifest["export"] = export
    write_json(manifest_path, manifest)
    return manifest


def command_run(args: argparse.Namespace) -> int:
    source, manifest, manifest_path = resolve_source(args)
    profiles = args.profile or ["conservative", "balanced"]
    output_dir = Path(args.output_dir).resolve() if args.output_dir else source.parent / "postprocess"
    data = source.read_bytes()
    layout = parse_binary_ply_layout(data)
    scan = scan_records(data, layout)
    profile_results = [run_profile(source, data, layout, scan, profile, output_dir) for profile in profiles]

    if args.report:
        report_path = Path(args.report).resolve()
    elif manifest_path:
        report_path = manifest_path.parent.parent / "reports" / "splat_postprocess.json"
    else:
        report_path = output_dir / f"{source.stem}.postprocess.json"

    report = {
        "schemaVersion": 1,
        "generatedAt": utc_now(),
        "source": artifact_info(source, "source", "Source"),
        "layout": {
            "vertexCount": int(layout["vertexCount"]),
            "format": layout["format"],
            "stride": int(layout["stride"]),
            "properties": [prop["name"] for prop in layout["properties"]],
            "hasOpacity": scan["hasOpacity"],
            "hasScale": scan["hasScale"],
        },
        "profiles": profile_results,
        "nonDestructive": True,
    }
    write_json(report_path, report)
    if args.update_manifest:
        if manifest is None or manifest_path is None:
            raise ValueError("--update-manifest requires --manifest")
        merge_manifest_variants(manifest, manifest_path, profile_results, report_path)

    print(f"splat_postprocess_status=pass")
    print(f"splat_postprocess_report={report_path}")
    for result in profile_results:
        print(
            f"{result['id']}={result['vertexCount']}/{result['originalVertexCount']} "
            f"removed={result['removedVertexCount']} path={result['path']}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create non-destructive Gaussian Splat cleanup variants.")
    parser.add_argument("--source", help="Source binary little-endian Gaussian Splat PLY.")
    parser.add_argument("--manifest", help="Viewer manifest whose artifact.path should be used.")
    parser.add_argument("--output-dir", help="Directory for cleaned variant PLY files.")
    parser.add_argument("--report", help="JSON report path.")
    parser.add_argument(
        "--profile",
        action="append",
        choices=sorted(CLEANUP_PROFILES),
        help="Cleanup profile to write. Repeat for multiple profiles. Defaults to conservative and balanced.",
    )
    parser.add_argument(
        "--update-manifest",
        action="store_true",
        help="Append artifactVariants to the viewer manifest so the gallery can switch variants.",
    )
    parser.set_defaults(func=command_run)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
