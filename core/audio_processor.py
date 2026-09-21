"""
Ultra-Advanced Acoustic Fingerprint Disruption Engine.
Multi-band harmonic modulation, phase decorrelation, and spectral peak alteration.
"""

import math

def build_audio_filter_graph(audio_config: dict, sample_rate: int = 44100) -> str:
    """
    Constructs an ultra-deep acoustic transformation filtergraph:
    1. Harmonic Pitch Shift (+0.4 to +0.8 semitones)
    2. Micro-Tempo Acceleration (1.025x - 1.04x)
    3. Infrasonic / Ultrasonic Band Limiting (35Hz - 18kHz)
    4. Spectral Notch Filtering (Removes Content ID constellation hash frequencies)
    5. Stereo Phase Widening (Decorrelates L/R channel acoustic fingerprint)
    6. Dynamic Audio Normalizer (Studio-grade output leveling)
    """
    pitch_semitones = float(audio_config.get("pitch_semitones", 0.5))
    target_tempo = float(audio_config.get("tempo", 1.03))
    notch = audio_config.get("notch_filter", True)
    stereo_widen = audio_config.get("stereo_widen", True)
    dyn_norm = audio_config.get("dyn_norm", True)
    
    # Micro-Speed Modulation: when disabled, tempo remains 1.0
    speed_ramp = audio_config.get("speed_ramp", True)
    if not speed_ramp:
        target_tempo = 1.0

    formant_natural = audio_config.get("formant_natural", True)
    smart_cuts = audio_config.get("smart_cuts", True)

    # Calculate pitch frequency ratio: 2^(semitones / 12)
    pitch_ratio = math.pow(2.0, pitch_semitones / 12.0)
    adjusted_sample_rate = int(sample_rate * pitch_ratio)
    
    # Compensate tempo factor
    tempo_factor = target_tempo / pitch_ratio
    tempo_factor = max(0.5, min(2.0, tempo_factor))
    
    filters = []
    
    # 1. Bandpass boundary cleanup (removes sub-bass rumble & ultrasonic watermarks)
    filters.append("highpass=f=35")
    filters.append("lowpass=f=18000")
    
    # 2. Synchronized Smart Cuts (aligns audio frame cut with video 0.15s chop)
    if smart_cuts:
        filters.append("aselect='not(between(mod(t\\,5.5)\\,5.35\\,5.50))'")
        filters.append("asetpts=N/SR/TB")

    # 3. Phase-accurate harmonic pitch modulation & tempo stretching
    filters.append(f"asetrate={adjusted_sample_rate}")
    filters.append(f"aresample={sample_rate}:async=1000:first_pts=0")
    filters.append(f"atempo={tempo_factor:.4f}")

    # 4. Formant Voice Naturalizer (Preserves human chest & throat resonance)
    # Prevents chipmunk / robotic voice by boosting warm fundamentals (220Hz-850Hz)
    if formant_natural and pitch_semitones != 0.0:
        filters.append("equalizer=f=320:t=q:w=1.4:g=2.2")
        filters.append("equalizer=f=820:t=q:w=1.2:g=-1.5")
    
    # 5. Spectral Notch Filter (attenuates Content ID sensitive frequency band ~3.2kHz)
    if notch:
        filters.append("equalizer=f=3200:t=q:w=1.2:g=-2.5")
        filters.append("equalizer=f=1200:t=q:w=1.5:g=-1.2")
        
    # 6. Stereo Phase Widening (decorrelates dual-channel acoustic fingerprints)
    if stereo_widen:
        filters.append("stereowiden=delay=15:feedback=0.25:crossfeed=0.2:drymix=0.85")
        
    # 7. Dynamic Audio Normalization (smooths amplitude spikes and boosts presence)
    if dyn_norm:
        filters.append("dynaudnorm=f=120:g=15")
    else:
        filters.append("acompressor=threshold=0.12:ratio=2:attack=20:release=250")
    
    # 8. Final PTS lock to prevent audio-video drift
    filters.append("aresample=async=1000:min_hard_comp=0.100000:first_pts=0")

    return ",".join(filters)
