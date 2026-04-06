import unittest

import common
import gen_case
import gen_width


class UnicodeQueryTests(unittest.TestCase):
    def test_lookup_codepoint_by_name(self):
        self.assertEqual(
            common.find_codepoint("ZERO WIDTH JOINER"),
            ord("\u200d"),
        )

    def test_lookup_block_by_name(self):
        enclosed_ideographic = common.load_blocks()["Enclosed Ideographic Supplement"]
        self.assertTrue(any(lo <= ord("\U0001F200") <= hi for lo, hi in enclosed_ideographic))

    def test_find_codepoints_by_property_value(self):
        emoji_presentation = common.load_property_set(
            "emoji/emoji-data.txt",
            "Emoji_Presentation",
        )
        self.assertIn(common.find_codepoint("GRINNING FACE"), emoji_presentation)

    def test_find_codepoints_by_decomposition(self):
        middle_dot = common.find_codepoint("MIDDLE DOT")
        greek_ano_teleia = common.find_codepoint("GREEK ANO TELEIA")
        self.assertIn(
            greek_ano_teleia,
            common.find_codepoints_with_canonical_decomposition((middle_dot,)),
        )


class CaseGeneratorTests(unittest.TestCase):
    def test_case_layout_is_derived_from_runs(self):
        runs = gen_case.load_casefold_runs()
        layout = gen_case.derive_case_lookup_layout(runs)

        expected_bucket_count = max(
            (run.end >> common.BYTE_BITS)
            for run in runs
            if run.end <= layout.compact_lookup_max
        ) + 1

        self.assertEqual(layout.bucket_count, expected_bucket_count)
        self.assertEqual(layout.compact_lookup_max, layout.compact_lookup_last_high_byte << common.BYTE_BITS | common.BYTE_MASK)
        self.assertTrue(all(run.end > layout.compact_lookup_max for run in layout.high_runs))


class WidthRuleDerivationTests(unittest.TestCase):
    def test_ambiguous_width_overrides_are_derived(self):
        overrides = gen_width.derive_ambiguous_width_overrides()
        self.assertIn(common.find_codepoint("GREEK ANO TELEIA"), overrides)

    def test_zero_width_overrides_are_derived(self):
        zero_width_rules = gen_width.derive_zero_width_rule_sets()
        self.assertIn(common.find_codepoint("SYRIAC ABBREVIATION MARK"), zero_width_rules.force_zero)
        self.assertIn(common.find_codepoint("DEVANAGARI CARET"), zero_width_rules.force_zero)
        self.assertIn(common.find_codepoint("HANGUL CHOSEONG FILLER"), zero_width_rules.force_non_zero)
        self.assertIn(common.find_codepoint("TIFINAGH CONSONANT JOINER"), zero_width_rules.force_non_zero)

    def test_special_width_states_are_derived(self):
        special_widths = gen_width.derive_special_widths()
        self.assertEqual(
            special_widths.common[common.find_codepoint("LINE FEED")],
            gen_width.WidthState.LINE_FEED,
        )
        self.assertEqual(
            special_widths.common[common.find_codepoint("HEBREW LETTER LAMED")],
            gen_width.WidthState.HEBREW_LETTER_LAMED,
        )
        self.assertEqual(
            special_widths.common[common.find_codepoint("KHMER SIGN BEYYAL")],
            gen_width.WidthState.THREE,
        )
        self.assertEqual(
            special_widths.common[common.find_codepoint("LISU LETTER TONE MYA JEU")],
            gen_width.WidthState.LISU_TONE_LETTER_MYA_NA_JEU,
        )

    def test_variation_selector_rules_are_derived(self):
        variation_rules = gen_width.derive_variation_selector_rules()
        self.assertIn(common.find_codepoint("VARIATION SELECTOR-16"), variation_rules.common)
        self.assertIn(common.find_codepoint("VARIATION SELECTOR-15"), variation_rules.non_cjk_only)
        self.assertIn(common.find_codepoint("VARIATION SELECTOR-1"), variation_rules.cjk_only)

    def test_text_presentation_exclusion_uses_unicode_blocks(self):
        text_presentation = gen_width.load_text_presentation_sequences()
        self.assertIn(common.find_codepoint("WATCH"), text_presentation)
        self.assertNotIn(common.find_codepoint("SQUARED KATAKANA SA"), text_presentation)

    def test_emoji_presentation_sequences_are_loaded(self):
        emoji_presentation = gen_width.load_emoji_presentation_sequences()
        self.assertIn(common.find_codepoint("COPYRIGHT SIGN"), emoji_presentation)


if __name__ == "__main__":
    unittest.main()
