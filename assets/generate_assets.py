"""
Generates built-in royalty-free audio beds and dynamic bottom canvases.
Ensures zero external file dependency on Railway or local deployment.
"""

import os
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BGM_DIR = os.path.join(SCRIPT_DIR, "bgm")
CANVAS_DIR = os.path.join(SCRIPT_DIR, "gameplay")

os.makedirs(BGM_DIR, exist_ok=True)
os.makedirs(CANVAS_DIR, exist_ok=True)

def generate_assets():
    # 1. Generate Lo-Fi Chill Ambient Bed (30s loop)
    lofi_path = os.path.join(BGM_DIR, "lofi_chill.mp3")
    if not os.path.exists(lofi_path):
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "sine=f=220:d=30,volume=0.08[a1];sine=f=330:d=30,volume=0.06[a2];sine=f=440:d=30,volume=0.04[a3];anoisesrc=d=30:c=pink:r=44100,volume=0.015,lowpass=f=800[noise];[a1][a2][a3][noise]amix=inputs=4:duration=longest[mix];[mix]chorus=0.7:0.9:55:0.4:0.25:2[out]",
            "-map", "[out]",
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            lofi_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 2. Generate Cinematic Tension Drone (30s loop)
    cine_path = os.path.join(BGM_DIR, "cinematic_tension.mp3")
    if not os.path.exists(cine_path):
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "sine=f=65:d=30,volume=0.15[sub];sine=f=130:d=30,volume=0.08[mid];anoisesrc=d=30:c=brown:r=44100,volume=0.02,bandpass=f=200:w=100[amb];[sub][mid][amb]amix=inputs=3:duration=longest[out]",
            "-map", "[out]",
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            cine_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 3. Generate Satisfying Dynamic Visual Canvas (1080x768 15s loop for bottom split-screen)
    canvas_path = os.path.join(CANVAS_DIR, "satisfying_canvas.mp4")
    if not os.path.exists(canvas_path):
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "mandelbrot=size=1080x768:rate=30:maxiter=120,hue=s=sin(t*0.5)*0.5+0.5:h=t*20,format=yuv420p",
            "-t", "15",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            canvas_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    generate_assets()
    print("Assets generated successfully!")
