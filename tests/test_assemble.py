import os
import tempfile
import unittest
from pathlib import Path

from assemble import ass_timestamp, caption_words, find_program, make_ass


class CaptionTests(unittest.TestCase):
    def test_caption_words_remove_voice_tags(self):
        self.assertEqual(caption_words("[curious] Look here."), ["Look", "here."])

    def test_ass_timestamp_uses_centiseconds(self):
        self.assertEqual(ass_timestamp(1.234), "0:00:01.23")

    def test_ass_creates_one_caption_event_per_word(self):
        ass_text = make_ass("One word.", 2.0)
        dialogue_lines = [
            line for line in ass_text.splitlines() if line.startswith("Dialogue:")
        ]

        self.assertEqual([line.rsplit(",", 1)[-1] for line in dialogue_lines], ["One", "word."])

    def test_find_program_prefers_project_bundle(self):
        executable = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundled_bin = Path(temporary_directory) / ".tools" / "ffmpeg" / "release" / "bin"
            bundled_bin.mkdir(parents=True)
            bundled_executable = bundled_bin / executable
            bundled_executable.touch()

            self.assertEqual(
                find_program("ffmpeg", temporary_directory), str(bundled_executable)
            )


if __name__ == "__main__":
    unittest.main()