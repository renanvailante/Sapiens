## TEST AGENT PROMPT – IMAGE INTEGRATION RULES

- Always use base64-encoded images for all tests and requests.
- Accepted formats: JPEG, PNG, WEBP only.
- Do not use SVG, BMP, HEIC, or other formats.
- Do not upload blank, solid-color, or uniform-variance images.
- Every image must contain real visual features (objects, edges, textures, shadows).
- Re-detect MIME after transformations. Never mislabel a PNG as JPEG.
- Extract the first frame from any animated image.
- Resize large images to reasonable bounds (avoid oversized payloads).
