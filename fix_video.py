import os
import subprocess
import imageio_ffmpeg

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
video_path = r'd:\A_LMS\A_LMS_upgrade\media\lessons\videos\PPE_detection_output.mp4'
temp_path = video_path.replace('.mp4', '_fixed.mp4')

# Re-encode to H.264 (avc1) which is universally supported by web browsers, and apply faststart.
cmd = [
    ffmpeg_exe, 
    '-y', 
    '-i', video_path, 
    '-vcodec', 'libx264', 
    '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart',
    temp_path
]

print("Starting FFmpeg re-encoding...")
subprocess.run(cmd, check=True)
print("Finished re-encoding. Replacing original file...")

os.remove(video_path)
os.rename(temp_path, video_path)
print("Done! The video is now H.264 and web-compatible.")
