import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac"}
SCENE_COUNT = 5


def run(command, *, cwd=None):
    subprocess.run(command, check=True, cwd=cwd)


def find_asset(directory, number, extensions, kind):
    matches = [
        path
        for path in directory.rglob("*")
        if path.is_file()
        and path.stem == str(number)
        and path.suffix.lower() in extensions
    ]
    if not matches:
        raise FileNotFoundError(f"Missing {kind} file numbered {number} in {directory}")
    if len(matches) > 1:
        found = ", ".join(str(path) for path in matches)
        raise ValueError(f"More than one {kind} file numbered {number}: {found}")
    return matches[0]


def probe_duration(ffprobe, path):
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise ValueError(f"Could not read a valid duration from {path}")
    return duration


def caption_words(transcript):
    clean_text = re.sub(r"\[[^\]]*\]", "", transcript).strip()
    return re.findall(r"\S+", clean_text)


def ass_timestamp(seconds):
    total_centiseconds = max(0, round(seconds * 100))
    hours, remainder = divmod(total_centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    whole_seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02}:{whole_seconds:02}.{centiseconds:02}"


def make_ass(transcript, duration):
    words = caption_words(transcript)
    if not words:
        raise ValueError("A transcript line has no captionable words")

    weights = []
    for word in words:
        spoken_length = max(1, len(re.sub(r"[^\w]", "", word)))
        punctuation_pause = 0.12 if word.endswith((".", "!", "?")) else 0.0
        if word.endswith((",", ";", ":")):
            punctuation_pause = 0.06
        weights.append(spoken_length + punctuation_pause * 10)

    total_weight = sum(weights)
    current_time = 0.0
    events = []
    for word, weight in zip(words, weights):
        end_time = current_time + duration * weight / total_weight
        safe_word = word.replace("{", "\\{").replace("}", "\\}")
        events.append(
            "Dialogue: 0,{},{},Default,,0,0,0,,{}".format(
                ass_timestamp(current_time), ass_timestamp(end_time), safe_word
            )
        )
        current_time = end_time

    return "\n".join(
        [
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            "Style: Default,Arial,76,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,1,2,80,80,260,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
            *events,
            "",
        ]
    )


def escape_filter_path(path):
    return str(path.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def assemble(args):
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("FFmpeg and ffprobe must both be installed and available on PATH")

    video_dir = args.video_dir.resolve()
    audio_dir = args.audio_dir.resolve()
    if not video_dir.is_dir():
        raise NotADirectoryError(f"Video folder not found: {video_dir}")
    if not audio_dir.is_dir():
        raise NotADirectoryError(f"Audio folder not found: {audio_dir}")

    transcript_lines = [
        line.strip() for line in args.transcript.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if len(transcript_lines) != SCENE_COUNT:
        raise ValueError(
            f"Expected {SCENE_COUNT} non-empty transcript lines in {args.transcript}, "
            f"found {len(transcript_lines)}"
        )

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="shorts-helper-") as temporary_name:
        temporary_dir = Path(temporary_name)
        segment_files = []

        for number, transcript in enumerate(transcript_lines, start=1):
            video = find_asset(video_dir, number, VIDEO_EXTENSIONS, "video")
            audio = find_asset(audio_dir, number, AUDIO_EXTENSIONS, "audio")
            duration = probe_duration(ffprobe, audio)
            ass_path = temporary_dir / f"scene_{number}.ass"
            ass_path.write_text(make_ass(transcript, duration), encoding="utf-8")
            segment_path = temporary_dir / f"scene_{number}.mp4"
            subtitle_filter = escape_filter_path(ass_path)
            video_filter = (
                "scale=1080:1920:force_original_aspect_ratio=decrease,"
                "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,"
                f"tpad=stop_mode=clone:stop_duration={duration:.3f},"
                f"trim=duration={duration:.3f},setpts=PTS-STARTPTS,subtitles='{subtitle_filter}'"
            )
            run(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(video),
                    "-i",
                    str(audio),
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-vf",
                    video_filter,
                    "-r",
                    "30",
                    "-t",
                    f"{duration:.3f}",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "20",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-movflags",
                    "+faststart",
                    str(segment_path),
                ]
            )
            segment_files.append(segment_path.name)
            print(f"Rendered scene {number}/5: {video.name} + {audio.name}")

        concat_list = temporary_dir / "segments.txt"
        concat_list.write_text(
            "".join(f"file '{name}'\n" for name in segment_files), encoding="utf-8"
        )
        run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c",
                "copy",
                str(output),
            ],
            cwd=temporary_dir,
        )

    print(f"Finished: {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Join five numbered video/audio pairs with one-word-at-a-time captions."
    )
    parser.add_argument("--video-dir", type=Path, default=Path("videos"))
    parser.add_argument("--audio-dir", type=Path, default=Path("output"))
    parser.add_argument("--transcript", type=Path, default=Path("script.txt"))
    parser.add_argument("--output", type=Path, default=Path("final_video.mp4"))
    args = parser.parse_args()

    try:
        assemble(args)
    except (FileNotFoundError, NotADirectoryError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())