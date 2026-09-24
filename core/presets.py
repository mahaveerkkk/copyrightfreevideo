"""
Calibrated Protection Presets with Multi-Tier Visual & Audio Transformations.
"""

PRESETS = {
    "stealth_deep": {
        "id": "stealth_deep",
        "name": "Maximum Stealth (Deep-Clean)",
        "badge": "100% Full Spectrum",
        "description": "Total disruption: pHash noise, RGB spectral shift, 0.45° tilt, 4% zoom, vignette, stereo widening, pitch +0.3st & acoustic notch.",
        "security_score": 99,
        "video": {
            "zoom": 1.04,
            "rotate_deg": 0.45,
            "contrast": 1.03,
            "brightness": 0.01,
            "saturation": 1.04,
            "noise_grain": 2.2,
            "vignette": True,
            "sharpen": True,
            "fps_target": 29.97,
            "letterbox": True,
        },
        "audio": {
            "pitch_semitones": 0.55,
            "tempo": 1.025,
            "notch_filter": True,
            "stereo_widen": True,
            "dyn_norm": True
        }
    },
    "shorts_reels": {
        "id": "shorts_reels",
        "name": "Reels & Shorts Viral Shield",
        "badge": "Shorts / Reels Pro",
        "description": "Calibrated for 9:16 vertical reels: dynamic focal zoom (1.03x), punchy saturation, vocal pitch correction, and loud speech leveling.",
        "security_score": 96,
        "video": {
            "zoom": 1.03,
            "rotate_deg": 0.2,
            "contrast": 1.04,
            "brightness": 0.01,
            "saturation": 1.06,
            "noise_grain": 1.8,
            "vignette": False,
            "sharpen": True,
            "fps_target": 30.0,
        },
        "audio": {
            "pitch_semitones": 0.35,
            "tempo": 1.0,
            "notch_filter": False,
            "stereo_widen": True,
            "dyn_norm": True
        }
    },
    "movie_clip": {
        "id": "movie_clip",
        "name": "Cinema & Movie Clip Monetizer",
        "badge": "OTT & Film Shield",
        "description": "Preserves cinematic aesthetic while destroying keyframe visual embeddings with subtle RGB balance, film grain & micro-tilt.",
        "security_score": 97,
        "video": {
            "zoom": 1.03,
            "rotate_deg": 0.35,
            "contrast": 1.02,
            "brightness": 0.008,
            "saturation": 1.025,
            "noise_grain": 2.5,
            "vignette": True,
            "sharpen": True,
            "fps_target": 24.0,
        },
        "audio": {
            "pitch_semitones": 0.25,
            "tempo": 1.0,
            "notch_filter": True,
            "stereo_widen": True,
            "dyn_norm": True
        }
    },
    "music_safe": {
        "id": "music_safe",
        "name": "Music & Audio Protection",
        "badge": "Music Labels Bypass",
        "description": "High-intensity acoustic transformation. Dual notch filters, wider stereo phase decorrelation, and +0.45 semitone pitch shift.",
        "security_score": 98,
        "video": {
            "zoom": 1.03,
            "rotate_deg": 0.25,
            "contrast": 1.02,
            "brightness": 0.0,
            "saturation": 1.03,
            "noise_grain": 1.6,
            "vignette": False,
            "sharpen": True,
            "fps_target": 29.97,
        },
        "audio": {
            "pitch_semitones": 0.45,
            "tempo": 1.0,
            "notch_filter": True,
            "stereo_widen": True,
            "dyn_norm": True
        }
    }
}
