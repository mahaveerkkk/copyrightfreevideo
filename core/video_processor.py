"""
Ultra-Advanced Visual Perceptual Hash (pHash) Disruption Engine.
Features:
1. Dynamic 5-Style Camera Randomizer (Zoom 5-11%, random 4-8s intervals, no mirror flip)
2. Procedural Color & Grain Engine (Teal-Orange, Warm Amber, Cool Slate, Deep Cinema)
3. Micro-RGB Centroid Shifts to poison automated neural matching
4. Frame-rate normalization and clean 8-bit YUV420P formatting
"""

import math
import random

def build_dynamic_camera_filtergraph(style: str = "random", seed: int = 42) -> str:
    """
    Constructs an expression-based dynamic camera motion filter.
    Breaks continuous frame matching without requiring mirror flip.
    
    Styles:
    1. center_punch: Alternates between 1.0x and 1.08x zoom every 6 seconds
    2. slow_creep: Smooth breathing zoom push-in
    3. subtle_pan: 2% coordinate translation
    4. macro_focus: 11% expression zoom cut
    5. micro_pulse: Periodic 5s pixel grid shift
    """
    rng = random.Random(seed)
    
    if style == "random" or style not in ["center_punch", "slow_creep", "subtle_pan", "macro_focus", "micro_pulse"]:
        style = rng.choice(["center_punch", "slow_creep", "subtle_pan", "macro_focus", "micro_pulse"])
        
    zoom_scale = round(rng.uniform(1.05, 1.10), 3)
    interval = rng.choice([5, 6, 7, 8])
    double_interval = interval * 2

    if style == "center_punch":
        # Every 'interval' seconds, punch in zoom_scale, then return to normal
        return (
            rf"crop=w='if(lt(mod(t\,{double_interval})\,{interval})\,2*trunc(iw/(2*{zoom_scale}))\,2*trunc(iw/2))':"
            rf"h='if(lt(mod(t\,{double_interval})\,{interval})\,2*trunc(ih/(2*{zoom_scale}))\,2*trunc(ih/2))',"
            rf"scale=w='2*trunc(iw/2)':h='2*trunc(ih/2)'"
        )
    elif style == "slow_creep":
        # Smooth cyclic sinusoidal push-in between 1.0x and zoom_scale
        return (
            rf"crop=w='2*trunc(iw/(2*(1.0 + {zoom_scale - 1.0:.3f} * (0.5 + 0.5*sin(2*PI*t/{interval*3})))))':"
            rf"h='2*trunc(ih/(2*(1.0 + {zoom_scale - 1.0:.3f} * (0.5 + 0.5*sin(2*PI*t/{interval*3})))))',"
            rf"scale=w='2*trunc(iw/2)':h='2*trunc(ih/2)'"
        )
    elif style == "macro_focus":
        # 11% macro zoom cut on odd intervals
        return (
            rf"crop=w='if(lt(mod(t\,{interval*2})\,{interval})\,2*trunc(iw/(2*1.11))\,2*trunc(iw/2))':"
            rf"h='if(lt(mod(t\,{interval*2})\,{interval})\,2*trunc(ih/(2*1.11))\,2*trunc(ih/2))',"
            rf"scale=w='2*trunc(iw/2)':h='2*trunc(ih/2)'"
        )
    elif style == "subtle_pan":
        # Dynamic coordinate shift
        return (
            rf"crop=w='2*trunc(iw/(2*1.05))':h='2*trunc(ih/(2*1.05))':"
            rf"x='(in_w-out_w)/2 + (in_w*0.02)*sin(2*PI*t/{interval*2})':"
            rf"y='(in_h-out_h)/2',"
            rf"scale=w='2*trunc(iw/2)':h='2*trunc(ih/2)'"
        )
    else: # micro_pulse
        return (
            rf"crop=w='if(lt(mod(t\,6)\,1)\,2*trunc(iw/(2*1.06))\,2*trunc(iw/2))':"
            rf"h='if(lt(mod(t\,6)\,1)\,2*trunc(ih/(2*1.06))\,2*trunc(ih/2))',"
            rf"scale=w='2*trunc(iw/2)':h='2*trunc(ih/2)'"
        )

def build_procedural_color_filtergraph(color_mood: str = "auto", seed: int = 42) -> str:
    """
    Applies cinematic color shading & RGB centroid shifts to destroy pHash color matches.
    Profiles:
    - teal_orange: Hollywood blockbuster aesthetic
    - warm_amber: Golden hour dramatic cinema
    - cool_slate: Suspense/Mystery tension
    - deep_cinema: Netflix high-contrast film
    """
    rng = random.Random(seed)
    if color_mood == "auto" or color_mood not in ["teal_orange", "warm_amber", "cool_slate", "deep_cinema"]:
        color_mood = rng.choice(["teal_orange", "warm_amber", "cool_slate", "deep_cinema"])

    # Subtle randomized RGB perturbations (+-0.005 to +-0.02)
    dr = rng.uniform(0.008, 0.018)
    dg = rng.uniform(-0.010, -0.004)
    db = rng.uniform(0.010, 0.022)

    filters = []
    if color_mood == "teal_orange":
        filters.append(f"colorbalance=rs={dr:.3f}:gs={dg:.3f}:bs={db:.3f}:rm=0.015:bm=-0.010:rh=0.010:bh=-0.012")
        filters.append("eq=contrast=1.04:saturation=1.05:brightness=0.01")
    elif color_mood == "warm_amber":
        filters.append(f"colorbalance=rs={dr+0.01:.3f}:gs={dg+0.005:.3f}:bs={db-0.01:.3f}:rm=0.020:gm=0.008:bm=-0.015")
        filters.append("eq=contrast=1.03:saturation=1.06:brightness=0.012")
    elif color_mood == "cool_slate":
        filters.append(f"colorbalance=rs={dr-0.01:.3f}:gs={dg:.3f}:bs={db+0.015:.3f}:rm=-0.010:gm=0.005:bm=0.020")
        filters.append("eq=contrast=1.05:saturation=0.98:brightness=-0.005")
    else: # deep_cinema
        filters.append(f"colorbalance=rs={dr:.3f}:gs={dg:.3f}:bs={db:.3f}:rm=0.012:bm=0.012")
        filters.append("eq=contrast=1.06:saturation=1.03:gamma=0.98")

    return ",".join(filters)

def build_video_filter_graph(video_config: dict, is_vertical_source: bool = False, seed: int = 42) -> str:
    """
    Master visual transformation pipeline:
    1. Dynamic 5-Style Camera Motion (breaks 10s continuous match)
    2. Procedural Color & Contrast Grading (alters histogram & perceptual hash)
    3. Multi-Channel Perceptual Noise / Film Grain (dithers byte distances)
    4. Micro Unsharp Masking (crisp edge contrast enhancement)
    5. Clean standard pixel format YUV420P
    """
    contrast = float(video_config.get("contrast", 1.03))
    brightness = float(video_config.get("brightness", 0.01))
    saturation = float(video_config.get("saturation", 1.04))
    noise_grain = float(video_config.get("noise_grain", 2.2))
    vignette = video_config.get("vignette", True)
    sharpen = video_config.get("sharpen", True)
    fps_target = float(video_config.get("fps_target", 29.97))
    dynamic_camera = video_config.get("dynamic_camera", True)
    camera_style = video_config.get("camera_style", "random")
    color_mood = video_config.get("color_mood", "auto")
    
    filters = []

    # 1. Horizontal Mirror Flip (OFF BY DEFAULT to keep movies natural & text readable)
    mirror_flip = video_config.get("mirror_flip", False)
    if mirror_flip:
        filters.append("hflip")

    # 2. Dynamic 5-Style Camera Motion (Auto-Chop / Zoom Cuts every 5-8s)
    if dynamic_camera:
        cam_filter = build_dynamic_camera_filtergraph(style=camera_style, seed=seed)
        filters.append(cam_filter)
    else:
        # Fallback static zoom if dynamic is disabled
        zoom = float(video_config.get("zoom", 1.045))
        if zoom > 1.0:
            filters.append(f"crop=w='2*trunc(iw/(2*{zoom:.4f}))':h='2*trunc(ih/(2*{zoom:.4f}))'")
            filters.append("scale=w='2*trunc(iw/2)':h='2*trunc(ih/2)'")

    # 3. Micro-Rotation (Breaks rectangular coordinate matrix - subtle 0.35 deg)
    rotate_deg = float(video_config.get("rotate_deg", 0.35))
    if rotate_deg > 0.0:
        rad = rotate_deg * (math.pi / 180.0)
        filters.append(f"rotate={rad:.6f}:bilinear=1:fillcolor=black")

    # 4. Procedural Cinematic Color Grading
    color_filter = build_procedural_color_filtergraph(color_mood=color_mood, seed=seed)
    filters.append(color_filter)

    # 5. Multi-Channel Perceptual Noise / Film Grain (Alters pHash byte distances)
    if noise_grain > 0:
        luma_grain = int(noise_grain * 4)
        chroma_grain = max(1, int(luma_grain / 2))
        filters.append(f"noise=c0s={luma_grain}:c0f=t+u:c1s={chroma_grain}:c1f=t+u:c2s={chroma_grain}:c2f=t+u")

    # 6. Subtle Vignette (Peripheral luminance curve alteration)
    if vignette:
        filters.append("vignette=angle=PI/90")
        
    # 7. Unsharp Mask (Sharpens edges so video appears enhanced)
    if sharpen:
        filters.append("unsharp=3:3:0.6")

    # 8. Cinematic PiP Border Frame (Optional)
    border_frame = video_config.get("border_frame", False)
    if border_frame:
        filters.append("scale=w='2*trunc(iw*0.94/2)':h='2*trunc(ih*0.94/2)'")
        filters.append("pad=w='2*trunc(iw/0.94/2)':h='2*trunc(ih/0.94/2)':x='(ow-iw)/2':y='(oh-ih)/2':color=black")

    # 9. FPS Standardization
    if fps_target > 0:
        filters.append(f"fps={fps_target}")

    # 10. Clean standard pixel format
    filters.append("format=yuv420p")
    
    return ",".join(filters)
