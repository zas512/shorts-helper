import unittest

from assemble import ass_timestamp, caption_words, make_ass


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


if __name__ == "__main__":
    unittest.main()