# Sample Capture Candidates

Verified: 2026-06-08

The preferred golden-path input is still self-captured footage: 20-40 seconds, slow orbit, static textured scene, no people, no logos, no recognizable third-party artwork and no private documents. That gives the cleanest commercial chain of custody.

## Candidate: Pexels Empty Coffee Shop Interior

- Capture id: `pexels-empty-coffee-shop-interior-14227022`
- Source page: https://www.pexels.com/video/an-empty-coffee-shop-interior-14227022/
- License page: https://www.pexels.com/license/
- Terms page: https://www.pexels.com/terms-of-service/
- Author shown on Pexels: Connor Scott McManus
- Local target path: `data/videos/pexels-empty-coffee-shop-interior-14227022.mp4`
- Intended use: technical pipeline validation only, not commercial showcase material.

Why it is a reasonable technical candidate:

- Page is marked `Free to use`.
- Tags include empty/no people/interior/cafe/chairs/wooden floor/natural light.
- The scene appears more useful for SfM than abstract footage because it has furniture, edges and texture.

License posture:

- Pexels says photos and videos can be downloaded and used for free, attribution is not required, and modification is allowed.
- Pexels Terms describe a non-exclusive, royalty-free license for commercial and non-commercial use, subject to prohibited uses.
- Pexels also restricts uses such as standalone resale/distribution, implying endorsement, redistribution on stock platforms, and trademark/service-mark use.
- Treat this as acceptable for local technical validation only. For product demos, marketing or commercial evidence, use self-captured footage or obtain a separately reviewed asset.

Readiness check:

```bash
.venv/bin/python scripts/lab-pipeline.py list-captures --capture-manifest data/manifests/captures.example.json
```

Manual next step when ready:

1. Download the chosen Pexels quality manually from the source page.
2. Import it through the provenance-aware CLI command:

```bash
.venv/bin/python scripts/lab-pipeline.py import-video \
  --capture-manifest data/manifests/captures.example.json \
  --capture-id pexels-empty-coffee-shop-interior-14227022 \
  --input /path/to/downloaded-video.mp4 \
  --accept-warning \
  --overwrite
```

3. Run `list-captures`, then create a job and run `framework_license`, `environment`, `intake` and `frame_sampling`.
4. Do not run `sfm`, training or viewer validation until the workstation power issue is resolved and `--allow-heavy` is intentionally supplied.
