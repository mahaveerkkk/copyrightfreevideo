"""
Alex Hormozi Style Animated Dynamic Captions Engine.
Generates styled Advanced SubStation Alpha (.ass) subtitles with bold yellow/white word popping.
"""

import os
from typing import List, Dict, Any

def format_ass_time(seconds: float) -> str:
    """Formats seconds into ASS timestamp format: H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def generate_ass_subtitle_file(
    transcript_segments: List[Dict[str, Any]],
    clip_start: float,
    clip_end: float,
    output_ass_path: str,
    highlight_color: str = "&H002BF7F7"  # Electric Yellow (&HAABBGGRR in ASS)
) -> str:
    """
    Constructs an Alex Hormozi style ASS subtitle file:
    - Bold centered text
    - Black 4px border & drop shadow
    - Fast 3-5 word bursts with uppercase emphasis
    - Highlighted active words
    """
    os.makedirs(os.path.dirname(output_ass_path), exist_ok=True)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hormozi,Arial,68,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,5,3,2,60,60,540,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogue_lines = []

    # Filter segments within clip duration
    relevant_segments = []
    for item in transcript_segments:
        s = float(item.get("start", 0))
        dur = float(item.get("duration", 2.0))
        e = s + dur
        if e >= clip_start and s <= clip_end:
            relevant_segments.append(item)

    for item in relevant_segments:
        raw_text = str(item.get("text", "")).strip().upper()
        if not raw_text:
            continue

        raw_s = float(item.get("start", 0))
        raw_dur = float(item.get("duration", 2.0))
        raw_e = raw_s + raw_dur

        # Offset timestamps relative to clip start (t=0 at clip_start)
        rel_s = max(0.0, raw_s - clip_start)
        rel_e = max(rel_s + 0.5, min(clip_end - clip_start, raw_e - clip_start))

        # Split into short 3-4 word phrases for fast impact
        words = raw_text.split()
        if not words:
            continue

        # Create word chunks
        chunk_size = 4
        total_chunks = (len(words) + chunk_size - 1) // chunk_size
        chunk_dur = (rel_e - rel_s) / max(1, total_chunks)

        for i in range(total_chunks):
            chunk_words = words[i * chunk_size : (i + 1) * chunk_size]
            c_start = rel_s + (i * chunk_dur)
            c_end = c_start + chunk_dur

            start_str = format_ass_time(c_start)
            end_str = format_ass_time(c_end)

            # Highlight first word of the burst in bright yellow
            if len(chunk_words) > 1:
                highlighted_phrase = f"{{\\c{highlight_color}\\b1}}{chunk_words[0]}{{\\c&H00FFFFFF\\b1}} " + " ".join(chunk_words[1:])
            else:
                highlighted_phrase = f"{{\\c{highlight_color}\\b1}}{chunk_words[0]}"

            dialogue_lines.append(
                f"Dialogue: 0,{start_str},{end_str},Hormozi,,0,0,0,,{highlighted_phrase}"
            )

    content = header + "\n".join(dialogue_lines) + "\n"
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_ass_path
