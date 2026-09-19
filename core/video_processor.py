"""
Ultra-Advanced Visual Perceptual Hash (pHash) Disruption Engine.
Applies multi-layer geometric, chromatic, spatial, and temporal transformations.
"""

import math

def build_video_filter_graph(video_config: dict, is_vertical_source: bool = False) -> str:
    """
    Constructs an ultra-deep visual transformation filtergraph:
    1. Sub-degree Micro-Tilt (Breaks rectangular boundary object detection)
    2. Dynamic Zoom & Center Crop (Invalidates spatial pixel hash grid)
    3. Multi-Channel Perceptual Noise / Film Grain (Luma & Chroma dither)
    4. RGB Spectral Vector Shift (Colorbalance shifts RGB centroids)
    5. Subtle Vignette (Peripheral luminance gradient)
    6. Micro Unsharp Masking (Crisp edge contrast enhancement)
    7. Gamma & Color EQ Curve Shifts
    8. Frame-Rate Normalization & safe 8-bit YUV420P
    """
    zoom = float(video_config.get("zoom", 1.045))
    rotate_deg = float(video_config.get("rotate_deg", 0.45))
    contrast = float(video_config.get("contrast", 1.03))
    brightness = float(video_config.get("brightness", 0.01))
    saturation = float(video_config.get("saturation", 1.04))
    noise_grain = float(video_config.get("noise_grain", 2.2))
    vignette = video_config.get("vignette", True)
    sharpen = video_config.get("sharpen", True)
    fps_target = float(video_config.get("fps_target", 29.97))
    
    filters = []
    
    # 1. Micro-Rotation (Breaks rectangular coordinate matrix)
    if rotate_deg > 0.0:
        rad = rotate_deg * (math.pi / 180.0)
        filters.append(f"rotate={rad:.6f}:bilinear=1:fillcolor=black")
    
    # 2. Dynamic Zoom & Center Crop with even pixel dimensions (trunc(x/2)*2)
    if zoom > 1.0:
        filters.append(f"crop=w='2*trunc(iw/(2*{zoom:.4f}))':h='2*trunc(ih/(2*{zoom:.4f}))'")
        filters.append("scale=w='2*trunc(iw/2)':h='2*trunc(ih/2)'")
    
    # 3. Multi-Channel Perceptual Noise / Film Grain (Alters pHash byte distances)
    if noise_grain > 0:
        luma_grain = int(noise_grain * 4)
        chroma_grain = max(1, int(luma_grain / 2))
        filters.append(f"noise=c0s={luma_grain}:c0f=t+u:c1s={chroma_grain}:c1f=t+u:c2s={chroma_grain}:c2f=t+u")
    
    # 4. Color EQ curve shift (Modifies histogram peak distribution)
    filters.append(f"eq=contrast={contrast:.3f}:brightness={brightness:.3f}:saturation={saturation:.3f}")
    
    # 5. RGB Spectral Balance Shift (Perturbs deep-learning visual embeddings)
    filters.append("colorbalance=rs=0.015:gs=-0.008:bs=0.02:rm=0.01:bm=0.015")
    
    # 6. Subtle Vignette (Peripheral luminance curve alteration)
    if vignette:
        filters.append("vignette=angle=PI/90")
        
    # 7. Unsharp Mask (Sharpens edges so video appears enhanced while altering edge gradients)
    if sharpen:
        filters.append("unsharp=3:3:0.6")
    
    # 8. FPS Standardization (skip if 0 to avoid unnecessary re-mux)
    if fps_target > 0:
        filters.append(f"fps={fps_target}")
    
    # 9. Clean standard pixel format
    filters.append("format=yuv420p")
    
    return ",".join(filters)
