"""Width table generation module.

Extracted from generate.py — contains all width-related code:
enums, data loading, table building, and Cangjie emission functions.
"""

import enum
import math
import operator
import re
from collections import defaultdict
from itertools import batched
from typing import Iterable, IO

from common import (
    UNICODE_VERSION,
    NUM_CODEPOINTS,
    Codepoint,
    fetch_open,
    load_unicode_version,
    load_property,
    to_sorted_ranges,
    emit_cangjie_file,
)

MAX_CODEPOINT_BITS = math.ceil(math.log2(NUM_CODEPOINTS - 1))
TABLE_SPLITS = [7, 13]
BitPos = int


class OffsetType(enum.IntEnum):
    U2 = 2
    U4 = 4
    U8 = 8


class EastAsianWidth(enum.IntEnum):
    NARROW = 1
    WIDE = 2
    AMBIGUOUS = 3


class CharWidthInTable(enum.IntEnum):
    ZERO = 0
    ONE = 1
    TWO = 2
    SPECIAL = 3


class WidthState(enum.IntEnum):
    ZERO = 0x1_0000
    NARROW = 0x1_0001
    WIDE = 0x1_0002
    THREE = 0x1_0003
    LINE_FEED = 0b0000_0000_0000_0001
    EMOJI_MODIFIER = 0b0000_0000_0000_0010
    REGIONAL_INDICATOR = 0b0000_0000_0000_0011
    SEVERAL_REGIONAL_INDICATOR = 0b0000_0000_0000_0100
    EMOJI_PRESENTATION = 0b0000_0000_0000_0101
    ZWJ_EMOJI_PRESENTATION = 0b0001_0000_0000_0110
    VS16_ZWJ_EMOJI_PRESENTATION = 0b1001_0000_0000_0110
    KEYCAP_ZWJ_EMOJI_PRESENTATION = 0b0001_0000_0000_0111
    VS16_KEYCAP_ZWJ_EMOJI_PRESENTATION = 0b1001_0000_0000_0111
    REGIONAL_INDICATOR_ZWJ_PRESENTATION = 0b0000_0000_0000_1001
    EVEN_REGIONAL_INDICATOR_ZWJ_PRESENTATION = 0b0000_0000_0000_1010
    ODD_REGIONAL_INDICATOR_ZWJ_PRESENTATION = 0b0000_0000_0000_1011
    TAG_END_ZWJ_EMOJI_PRESENTATION = 0b0000_0000_0001_0000
    TAG_D1_END_ZWJ_EMOJI_PRESENTATION = 0b0000_0000_0001_0001
    TAG_D2_END_ZWJ_EMOJI_PRESENTATION = 0b0000_0000_0001_0010
    TAG_D3_END_ZWJ_EMOJI_PRESENTATION = 0b0000_0000_0001_0011
    TAG_A1_END_ZWJ_EMOJI_PRESENTATION = 0b0000_0000_0001_1001
    TAG_A2_END_ZWJ_EMOJI_PRESENTATION = 0b0000_0000_0001_1010
    TAG_A3_END_ZWJ_EMOJI_PRESENTATION = 0b0000_0000_0001_1011
    TAG_A4_END_ZWJ_EMOJI_PRESENTATION = 0b0000_0000_0001_1100
    TAG_A5_END_ZWJ_EMOJI_PRESENTATION = 0b0000_0000_0001_1101
    TAG_A6_END_ZWJ_EMOJI_PRESENTATION = 0b0000_0000_0001_1110
    KIRAT_RAI_VOWEL_SIGN_E = 0b0000_0000_0010_0000
    KIRAT_RAI_VOWEL_SIGN_AI = 0b0000_0000_0010_0001
    VARIATION_SELECTOR_1_2_OR_3 = 0b0000_0010_0000_0000
    VARIATION_SELECTOR_15 = 0b0100_0000_0000_0000
    VARIATION_SELECTOR_16 = 0b1000_0000_0000_0000
    JOINING_GROUP_ALEF = 0b0011_0000_1111_1111
    COMBINING_LONG_SOLIDUS_OVERLAY = 0b0011_1100_1111_1111
    SOLIDUS_OVERLAY_ALEF = 0b0011_1000_1111_1111
    HEBREW_LETTER_LAMED = 0b0011_1000_0000_0000
    ZWJ_HEBREW_LETTER_LAMED = 0b0011_1100_0000_0000
    BUGINESE_LETTER_YA = 0b0011_1000_0000_0001
    ZWJ_BUGINESE_LETTER_YA = 0b0011_1100_0000_0001
    BUGINESE_VOWEL_SIGN_I_ZWJ_LETTER_YA = 0b0011_1100_0000_0010
    TIFINAGH_CONSONANT = 0b0011_1000_0000_0011
    ZWJ_TIFINAGH_CONSONANT = 0b0011_1100_0000_0011
    TIFINAGH_JOINER_CONSONANT = 0b0011_1100_0000_0100
    LISU_TONE_LETTER_MYA_NA_JEU = 0b0011_1100_0000_0101
    OLD_TURKIC_LETTER_ORKHON_I = 0b0011_1000_0000_0110
    ZWJ_OLD_TURKIC_LETTER_ORKHON_I = 0b0011_1100_0000_0110
    KHMER_COENG_ELIGIBLE_LETTER = 0b0011_1100_0000_0111

    def table_width(self) -> CharWidthInTable:
        match self:
            case WidthState.ZERO:
                return CharWidthInTable.ZERO
            case WidthState.NARROW:
                return CharWidthInTable.ONE
            case WidthState.WIDE:
                return CharWidthInTable.TWO
            case WidthState.THREE:
                return CharWidthInTable.SPECIAL
            case _:
                return CharWidthInTable.SPECIAL

    def is_carried(self) -> bool:
        return int(self) <= 0xFFFF

    def width_alone(self) -> int:
        match self:
            case (
                WidthState.ZERO
                | WidthState.COMBINING_LONG_SOLIDUS_OVERLAY
                | WidthState.VARIATION_SELECTOR_15
                | WidthState.VARIATION_SELECTOR_16
                | WidthState.VARIATION_SELECTOR_1_2_OR_3
            ):
                return 0
            case (
                WidthState.WIDE
                | WidthState.EMOJI_MODIFIER
                | WidthState.EMOJI_PRESENTATION
            ):
                return 2
            case WidthState.THREE:
                return 3
            case _:
                return 1

    def is_cjk_only(self) -> bool:
        return self in [
            WidthState.COMBINING_LONG_SOLIDUS_OVERLAY,
            WidthState.SOLIDUS_OVERLAY_ALEF,
        ]

    def is_non_cjk_only(self) -> bool:
        return self == WidthState.VARIATION_SELECTOR_15


assert len(set([v.value for v in WidthState])) == len([v.value for v in WidthState])


# ---------------------------------------------------------------------------
# Data loading functions
# ---------------------------------------------------------------------------


def load_east_asian_widths() -> list[EastAsianWidth]:
    with fetch_open("EastAsianWidth.txt") as eaw:
        single = re.compile(r"^([0-9A-F]+)\s*;\s*(\w+) +# (\w+)")
        multiple = re.compile(r"^([0-9A-F]+)\.\.([0-9A-F]+)\s*;\s*(\w+) +# (\w+)")
        width_codes = {
            **{c: EastAsianWidth.NARROW for c in ["N", "Na", "H"]},
            **{c: EastAsianWidth.WIDE for c in ["W", "F"]},
            "A": EastAsianWidth.AMBIGUOUS,
        }

        width_map = []
        current = 0
        for line in eaw.readlines():
            raw_data = None
            if match := single.match(line):
                raw_data = (match.group(1), match.group(1), match.group(2))
            elif match := multiple.match(line):
                raw_data = (match.group(1), match.group(2), match.group(3))
            else:
                continue
            low = int(raw_data[0], 16)
            high = int(raw_data[1], 16)
            width = width_codes[raw_data[2]]

            assert current <= high
            while current <= high:
                width_map.append(EastAsianWidth.NARROW if current < low else width)
                current += 1

        while len(width_map) < NUM_CODEPOINTS:
            width_map.append(EastAsianWidth.NARROW)

    load_property(
        "LineBreak.txt",
        "AI",
        lambda cp: (operator.setitem(width_map, cp, EastAsianWidth.AMBIGUOUS)),
    )

    load_property(
        "extracted/DerivedGeneralCategory.txt",
        r"(:?Lu|Ll|Lt|Lm|Lo|Sk)",
        lambda cp: (
            operator.setitem(width_map, cp, EastAsianWidth.NARROW)
            if width_map[cp] == EastAsianWidth.AMBIGUOUS
            else None
        ),
    )

    width_map[0x0387] = EastAsianWidth.AMBIGUOUS

    with fetch_open("UnicodeData.txt") as udata:
        single = re.compile(r"([0-9A-Z]+);.*?;.*?;.*?;.*?;([0-9A-Z]+) 0338;")
        for line in udata.readlines():
            if match := single.match(line):
                composed = int(match.group(1), 16)
                decomposed = int(match.group(2), 16)
                if width_map[decomposed] == EastAsianWidth.AMBIGUOUS:
                    width_map[composed] = EastAsianWidth.AMBIGUOUS

    return width_map


def load_zero_widths() -> list[bool]:
    zw_map = [False] * NUM_CODEPOINTS

    load_property(
        "DerivedCoreProperties.txt",
        r"(?:Default_Ignorable_Code_Point|Grapheme_Extend)",
        lambda cp: operator.setitem(zw_map, cp, True),
    )

    load_property(
        "HangulSyllableType.txt",
        r"(?:V|T)",
        lambda cp: operator.setitem(zw_map, cp, True),
    )

    zw_map[0x070F] = True
    zw_map[0x0605] = True
    zw_map[0x0890] = True
    zw_map[0x0891] = True
    zw_map[0x08E2] = True

    gcb_prepend = set()
    load_property(
        "auxiliary/GraphemeBreakProperty.txt",
        "Prepend",
        lambda cp: gcb_prepend.add(cp),
    )
    load_property(
        "PropList.txt",
        "Prepended_Concatenation_Mark",
        lambda cp: gcb_prepend.remove(cp),
    )
    for cp in gcb_prepend:
        zw_map[cp] = True

    zw_map[0x115F] = False
    zw_map[0x2D7F] = False
    zw_map[0xA8FA] = True

    return zw_map


def load_width_maps() -> tuple[list[WidthState], list[WidthState]]:
    eaws = load_east_asian_widths()
    zws = load_zero_widths()

    not_ea = []
    ea = []

    for eaw, zw in zip(eaws, zws):
        if zw:
            not_ea.append(WidthState.ZERO)
            ea.append(WidthState.ZERO)
        else:
            if eaw == EastAsianWidth.WIDE:
                not_ea.append(WidthState.WIDE)
            else:
                not_ea.append(WidthState.NARROW)

            if eaw == EastAsianWidth.NARROW:
                ea.append(WidthState.NARROW)
            else:
                ea.append(WidthState.WIDE)

    alef_joining = []
    load_property(
        "extracted/DerivedJoiningGroup.txt",
        "Alef",
        lambda cp: alef_joining.append(cp),
    )

    regional_indicators = []
    load_property(
        "PropList.txt",
        "Regional_Indicator",
        lambda cp: regional_indicators.append(cp),
    )

    emoji_modifiers = []
    load_property(
        "emoji/emoji-data.txt",
        "Emoji_Modifier",
        lambda cp: emoji_modifiers.append(cp),
    )

    emoji_presentation = []
    load_property(
        "emoji/emoji-data.txt",
        "Emoji_Presentation",
        lambda cp: emoji_presentation.append(cp),
    )

    for cps, width in [
        ([0x0A], WidthState.LINE_FEED),
        ([0x05DC], WidthState.HEBREW_LETTER_LAMED),
        (alef_joining, WidthState.JOINING_GROUP_ALEF),
        (range(0x1780, 0x1783), WidthState.KHMER_COENG_ELIGIBLE_LETTER),
        (range(0x1784, 0x1788), WidthState.KHMER_COENG_ELIGIBLE_LETTER),
        (range(0x1789, 0x178D), WidthState.KHMER_COENG_ELIGIBLE_LETTER),
        (range(0x178E, 0x1794), WidthState.KHMER_COENG_ELIGIBLE_LETTER),
        (range(0x1795, 0x1799), WidthState.KHMER_COENG_ELIGIBLE_LETTER),
        (range(0x179B, 0x179E), WidthState.KHMER_COENG_ELIGIBLE_LETTER),
        (
            [0x17A0, 0x17A2, 0x17A7, 0x17AB, 0x17AC, 0x17AF],
            WidthState.KHMER_COENG_ELIGIBLE_LETTER,
        ),
        ([0x17A4], WidthState.WIDE),
        ([0x17D8], WidthState.THREE),
        ([0x1A10], WidthState.BUGINESE_LETTER_YA),
        (range(0x2D31, 0x2D66), WidthState.TIFINAGH_CONSONANT),
        ([0x2D6F], WidthState.TIFINAGH_CONSONANT),
        ([0xA4FC], WidthState.LISU_TONE_LETTER_MYA_NA_JEU),
        ([0xA4FD], WidthState.LISU_TONE_LETTER_MYA_NA_JEU),
        ([0xFE0F], WidthState.VARIATION_SELECTOR_16),
        ([0x10C03], WidthState.OLD_TURKIC_LETTER_ORKHON_I),
        ([0x16D67], WidthState.KIRAT_RAI_VOWEL_SIGN_E),
        ([0x16D68], WidthState.KIRAT_RAI_VOWEL_SIGN_AI),
        (emoji_presentation, WidthState.EMOJI_PRESENTATION),
        (emoji_modifiers, WidthState.EMOJI_MODIFIER),
        (regional_indicators, WidthState.REGIONAL_INDICATOR),
    ]:
        for cp in cps:
            not_ea[cp] = width
            ea[cp] = width

    ea[0x0338] = WidthState.COMBINING_LONG_SOLIDUS_OVERLAY
    ea[0xFE00] = WidthState.VARIATION_SELECTOR_1_2_OR_3
    ea[0xFE02] = WidthState.VARIATION_SELECTOR_1_2_OR_3

    not_ea[0xFE01] = WidthState.VARIATION_SELECTOR_1_2_OR_3
    not_ea[0xFE0E] = WidthState.VARIATION_SELECTOR_15

    return (not_ea, ea)


def load_joining_group_lam() -> list[tuple[Codepoint, Codepoint]]:
    lam_joining = []
    load_property(
        "extracted/DerivedJoiningGroup.txt",
        "Lam",
        lambda cp: lam_joining.append(cp),
    )
    return to_sorted_ranges(lam_joining)


def load_non_transparent_zero_widths(
    width_map: list[WidthState],
) -> list[tuple[Codepoint, Codepoint]]:
    zero_widths = set()
    for cp, width in enumerate(width_map):
        if width.width_alone() == 0:
            zero_widths.add(cp)
    transparent = set()
    load_property(
        "extracted/DerivedJoiningType.txt",
        "T",
        lambda cp: transparent.add(cp),
    )
    return to_sorted_ranges(zero_widths - transparent)


def load_ligature_transparent() -> list[tuple[Codepoint, Codepoint]]:
    default_ignorables = set()
    load_property(
        "DerivedCoreProperties.txt",
        "Default_Ignorable_Code_Point",
        lambda cp: default_ignorables.add(cp),
    )

    combining_marks = set()
    load_property(
        "extracted/DerivedGeneralCategory.txt",
        "(?:Mc|Mn|Me)",
        lambda cp: combining_marks.add(cp),
    )

    default_ignorable_combinings = default_ignorables.intersection(combining_marks)
    default_ignorable_combinings.add(0x200D)  # ZWJ

    return to_sorted_ranges(default_ignorable_combinings)


def load_solidus_transparent(
    ligature_transparents: list[tuple[Codepoint, Codepoint]],
    cjk_width_map: list[WidthState],
) -> list[tuple[Codepoint, Codepoint]]:
    ccc_above_1 = set()
    load_property(
        "extracted/DerivedCombiningClass.txt",
        "(?:[2-9]|(?:[1-9][0-9]+))",
        lambda cp: ccc_above_1.add(cp),
    )

    for lo, hi in ligature_transparents:
        for cp in range(lo, hi + 1):
            ccc_above_1.add(cp)

    num_chars = len(ccc_above_1)

    while True:
        with fetch_open("UnicodeData.txt") as udata:
            single = re.compile(r"([0-9A-Z]+);.*?;.*?;.*?;.*?;([0-9A-F ]+);")
            for line in udata.readlines():
                if match := single.match(line):
                    composed = int(match.group(1), 16)
                    decomposed = [int(c, 16) for c in match.group(2).split(" ")]
                    if all([c in ccc_above_1 for c in decomposed]):
                        ccc_above_1.add(composed)
        if len(ccc_above_1) == num_chars:
            break
        else:
            num_chars = len(ccc_above_1)

    for cp in ccc_above_1:
        if cp not in [0xFE00, 0xFE02, 0xFE0F]:
            assert (
                cjk_width_map[cp].table_width() != CharWidthInTable.SPECIAL
            ), f"U+{cp:X}"

    sorted_ranges = to_sorted_ranges(ccc_above_1)
    return list(filter(lambda r: r not in ligature_transparents, sorted_ranges))


def load_emoji_presentation_sequences() -> list[Codepoint]:
    with fetch_open("emoji/emoji-variation-sequences.txt") as sequences:
        sequence = re.compile(r"^([0-9A-F]+)\s+FE0F\s*;\s*emoji style")
        codepoints = []
        for line in sequences.readlines():
            if match := sequence.match(line):
                cp = int(match.group(1), 16)
                codepoints.append(cp)
    return codepoints


def load_text_presentation_sequences() -> list[Codepoint]:
    text_presentation_seq_codepoints = set()
    with fetch_open("emoji/emoji-variation-sequences.txt") as sequences:
        sequence = re.compile(r"^([0-9A-F]+)\s+FE0E\s*;\s*text style")
        for line in sequences.readlines():
            if match := sequence.match(line):
                cp = int(match.group(1), 16)
                text_presentation_seq_codepoints.add(cp)

    default_emoji_codepoints = set()
    load_property(
        "emoji/emoji-data.txt",
        "Emoji_Presentation",
        lambda cp: default_emoji_codepoints.add(cp),
    )

    codepoints = []
    for cp in text_presentation_seq_codepoints.intersection(default_emoji_codepoints):
        if not cp in range(0x1F200, 0x1F300):
            codepoints.append(cp)

    codepoints.sort()
    return codepoints


def load_emoji_modifier_bases() -> list[Codepoint]:
    ret = []
    load_property(
        "emoji/emoji-data.txt",
        "Emoji_Modifier_Base",
        lambda cp: ret.append(cp),
    )
    ret.sort()
    return ret


def make_presentation_sequence_table(
    seqs: list[Codepoint],
    lsb: int = 10,
) -> tuple[list[tuple[int, int]], list[list[int]]]:
    prefixes_dict = defaultdict(set)
    for cp in seqs:
        prefixes_dict[cp >> lsb].add(cp & (2**lsb - 1))

    msbs: list[int] = list(prefixes_dict.keys())

    leaves: list[list[int]] = []
    for cps in prefixes_dict.values():
        leaf = [0] * (2 ** (lsb - 3))
        for cp in cps:
            idx_in_leaf, bit_shift = divmod(cp, 8)
            leaf[idx_in_leaf] |= 1 << bit_shift
        leaves.append(leaf)

    indexes = [(msb, index) for (index, msb) in enumerate(msbs)]

    i = 0
    while i < len(leaves):
        first_idx = leaves.index(leaves[i])
        if first_idx == i:
            i += 1
        else:
            for j in range(0, len(indexes)):
                if indexes[j][1] == i:
                    indexes[j] = (indexes[j][0], first_idx)
                elif indexes[j][1] > i:
                    indexes[j] = (indexes[j][0], indexes[j][1] - 1)
            leaves.pop(i)

    return (indexes, leaves)


def make_ranges_table(
    seqs: list[Codepoint],
) -> tuple[list[tuple[int, int]], list[list[tuple[int, int]]]]:
    prefixes_dict = defaultdict(list)
    for cp in seqs:
        prefixes_dict[cp >> 8].append(cp & 0xFF)

    msbs: list[int] = list(prefixes_dict.keys())

    leaves: list[list[tuple[int, int]]] = []
    for cps in prefixes_dict.values():
        leaf = []
        for cp in cps:
            if len(leaf) > 0 and leaf[-1][1] == cp - 1:
                leaf[-1] = (leaf[-1][0], cp)
            else:
                leaf.append((cp, cp))
        leaves.append(leaf)

    indexes = [(msb, index) for (index, msb) in enumerate(msbs)]

    i = 0
    while i < len(leaves):
        first_idx = leaves.index(leaves[i])
        if first_idx == i:
            i += 1
        else:
            for j in range(0, len(indexes)):
                if indexes[j][1] == i:
                    indexes[j] = (indexes[j][0], first_idx)
                elif indexes[j][1] > i:
                    indexes[j] = (indexes[j][0], indexes[j][1] - 1)
            leaves.pop(i)

    return (indexes, leaves)


def make_special_ranges(
    width_map: list[WidthState],
) -> list[tuple[tuple[Codepoint, Codepoint], WidthState]]:
    ret = []
    can_merge_with_prev = False
    for cp, width in enumerate(width_map):
        if width == WidthState.EMOJI_PRESENTATION:
            can_merge_with_prev = False
        elif width.table_width() == CharWidthInTable.SPECIAL:
            if can_merge_with_prev and ret[-1][1] == width:
                ret[-1] = ((ret[-1][0][0], cp), width)
            else:
                ret.append(((cp, cp), width))
                can_merge_with_prev = True
    return ret


class Bucket:
    def __init__(self):
        self.entry_set = set()
        self.widths = []

    def append(self, codepoint: Codepoint, width: CharWidthInTable):
        self.entry_set.add((codepoint, width))
        self.widths.append(width)

    def try_extend(self, attempt: "Bucket") -> bool:
        (less, more) = (self.widths, attempt.widths)
        if len(self.widths) > len(attempt.widths):
            (less, more) = (attempt.widths, self.widths)
        if less != more[: len(less)]:
            return False
        self.entry_set |= attempt.entry_set
        self.widths = more
        return True

    def entries(self) -> list[tuple[Codepoint, CharWidthInTable]]:
        result = list(self.entry_set)
        result.sort()
        return result

    def width(self) -> CharWidthInTable | None:
        if len(self.widths) == 0:
            return None
        potential_width = self.widths[0]
        for width in self.widths[1:]:
            if potential_width != width:
                return None
        return potential_width


def make_buckets(
    entries: Iterable[tuple[int, CharWidthInTable]], low_bit: BitPos, cap_bit: BitPos
) -> list[Bucket]:
    num_bits = cap_bit - low_bit
    assert num_bits > 0
    buckets = [Bucket() for _ in range(0, 2**num_bits)]
    mask = (1 << num_bits) - 1
    for codepoint, width in entries:
        buckets[(codepoint >> low_bit) & mask].append(codepoint, width)
    return buckets


class Table:
    def __init__(
        self,
        name: str,
        entry_groups: Iterable[Iterable[tuple[int, CharWidthInTable]]],
        secondary_entry_groups: Iterable[Iterable[tuple[int, CharWidthInTable]]],
        low_bit: BitPos,
        cap_bit: BitPos,
        offset_type: OffsetType,
        align: int,
        bytes_per_row: int | None = None,
        starting_indexed: list[Bucket] = [],
        cfged: bool = False,
    ):
        starting_indexed_len = len(starting_indexed)
        self.name = name
        self.low_bit = low_bit
        self.cap_bit = cap_bit
        self.offset_type = offset_type
        self.entries: list[int] = []
        self.indexed: list[Bucket] = list(starting_indexed)
        self.align = align
        self.bytes_per_row = bytes_per_row
        self.cfged = cfged

        buckets: list[Bucket] = []
        for entries in entry_groups:
            buckets.extend(make_buckets(entries, self.low_bit, self.cap_bit))

        for bucket in buckets:
            for i, existing in enumerate(self.indexed):
                if existing.try_extend(bucket):
                    self.entries.append(i)
                    break
            else:
                self.entries.append(len(self.indexed))
                self.indexed.append(bucket)

        self.primary_len = len(self.entries)
        self.primary_bucket_len = len(self.indexed)

        buckets = []
        for entries in secondary_entry_groups:
            buckets.extend(make_buckets(entries, self.low_bit, self.cap_bit))

        for bucket in buckets:
            for i, existing in enumerate(self.indexed):
                if existing.try_extend(bucket):
                    self.entries.append(i)
                    break
            else:
                self.entries.append(len(self.indexed))
                self.indexed.append(bucket)

        max_index = 1 << int(self.offset_type)
        for index in self.entries:
            assert index < max_index, f"{index} <= {max_index}"

        self.indexed = self.indexed[starting_indexed_len:]

    def indices_to_widths(self):
        self.entries = list(map(lambda i: int(self.indexed[i].width()), self.entries))  # type: ignore
        del self.indexed

    def buckets(self):
        return self.indexed

    def to_bytes(self) -> list[int]:
        entries_per_byte = 8 // int(self.offset_type)
        byte_array = []
        for i in range(0, len(self.entries), entries_per_byte):
            byte = 0
            for j in range(0, entries_per_byte):
                byte |= self.entries[i + j] << (j * int(self.offset_type))
            byte_array.append(byte)
        return byte_array


def make_tables(
    width_map: list[WidthState],
    cjk_width_map: list[WidthState],
) -> list[Table]:
    entries = enumerate([w.table_width() for w in width_map])
    cjk_entries = enumerate([w.table_width() for w in cjk_width_map])

    root_table = Table(
        "WIDTH_ROOT",
        [entries],
        [],
        TABLE_SPLITS[1],
        MAX_CODEPOINT_BITS,
        OffsetType.U8,
        128,
    )

    cjk_root_table = Table(
        "WIDTH_ROOT_CJK",
        [cjk_entries],
        [],
        TABLE_SPLITS[1],
        MAX_CODEPOINT_BITS,
        OffsetType.U8,
        128,
        starting_indexed=root_table.indexed,
        cfged=True,
    )

    middle_table = Table(
        "WIDTH_MIDDLE",
        map(lambda bucket: bucket.entries(), root_table.buckets()),
        map(lambda bucket: bucket.entries(), cjk_root_table.buckets()),
        TABLE_SPLITS[0],
        TABLE_SPLITS[1],
        OffsetType.U8,
        2 ** (TABLE_SPLITS[1] - TABLE_SPLITS[0]),
        bytes_per_row=2 ** (TABLE_SPLITS[1] - TABLE_SPLITS[0]),
    )

    leaves_table = Table(
        "WIDTH_LEAVES",
        map(
            lambda bucket: bucket.entries(),
            middle_table.buckets()[: middle_table.primary_bucket_len],
        ),
        map(
            lambda bucket: bucket.entries(),
            middle_table.buckets()[middle_table.primary_bucket_len :],
        ),
        0,
        TABLE_SPLITS[0],
        OffsetType.U2,
        2 ** (TABLE_SPLITS[0] - 2),
        bytes_per_row=2 ** (TABLE_SPLITS[0] - 2),
    )

    return [root_table, cjk_root_table, middle_table, leaves_table]


# ---------------------------------------------------------------------------
# Cangjie emission: tables.cj
# ---------------------------------------------------------------------------


def emit_tables_cj(
    module: IO[str],
    unicode_version: tuple[int, int, int],
    tables: list[Table],
    emoji_presentation_table: tuple[list[tuple[int, int]], list[list[int]]],
    text_presentation_table: tuple[list[tuple[int, int]], list[list[tuple[int, int]]]],
    emoji_modifier_table: tuple[list[tuple[int, int]], list[list[tuple[int, int]]]],
    non_transparent_zero_widths: list[tuple[Codepoint, Codepoint]],
    solidus_transparent: list[tuple[Codepoint, Codepoint]],
):
    module.write("package unicode_width\n\n")
    module.write(
        f"public const UNICODE_VERSION: (UInt8, UInt8, UInt8) = ({unicode_version[0]}u8, {unicode_version[1]}u8, {unicode_version[2]}u8)\n"
    )

    emoji_presentation_idx, emoji_presentation_leaves = emoji_presentation_table
    text_presentation_idx, text_presentation_leaves = text_presentation_table
    emoji_modifier_idx, emoji_modifier_leaves = emoji_modifier_table

    subtable_count = 1
    for i, table in enumerate(tables):
        new_subtable_count = len(table.buckets())
        if i == len(tables) - 1:
            table.indices_to_widths()
        byte_array = table.to_bytes()

        if table.bytes_per_row is None:
            # Flat table (ROOT / ROOT_CJK) -> const VArray<UInt8, $N>
            n = len(byte_array)
            module.write(f"\nconst {table.name}: VArray<UInt8, ${n}> = [\n")
            for j, byte in enumerate(byte_array):
                if j % 16 == 0:
                    module.write("   ")
                module.write(f" 0x{byte:02X}u8,")
                if j % 16 == 15 or j == len(byte_array) - 1:
                    module.write("\n")
            module.write("]\n")
        else:
            # 2D table (MIDDLE / LEAVES) -> const VArray<VArray<UInt8, $COLS>, $ROWS>
            num_rows = len(byte_array) // table.bytes_per_row
            cols = table.bytes_per_row
            module.write(
                f"\nconst {table.name}: VArray<VArray<UInt8, ${cols}>, ${num_rows}> = [\n"
            )
            for row_num in range(num_rows):
                module.write("    [\n")
                row = byte_array[
                    row_num * cols : (row_num + 1) * cols
                ]
                for subrow in batched(row, 15):
                    module.write("       ")
                    for entry in subrow:
                        module.write(f" 0x{entry:02X}u8,")
                    module.write("\n")
                module.write("    ],\n")
            module.write("]\n")

        subtable_count = new_subtable_count

    # NON_TRANSPARENT_ZERO_WIDTHS -> let Array (passed to binary search function)
    module.write(
        f"\nlet NON_TRANSPARENT_ZERO_WIDTHS: Array<(UInt32, UInt32)> = [\n"
    )
    for lo, hi in non_transparent_zero_widths:
        module.write(f"    (0x{lo:06X}u32, 0x{hi:06X}u32),\n")
    module.write("]\n")

    # SOLIDUS_TRANSPARENT -> let Array (passed to binary search function)
    module.write(
        f"\nlet SOLIDUS_TRANSPARENT: Array<(UInt32, UInt32)> = [\n"
    )
    for lo, hi in solidus_transparent:
        module.write(f"    (0x{lo:06X}u32, 0x{hi:06X}u32),\n")
    module.write("]\n")

    # EMOJI_PRESENTATION_LEAVES -> const VArray<VArray<UInt8, $COLS>, $ROWS>
    ep_rows = len(emoji_presentation_leaves)
    ep_cols = len(emoji_presentation_leaves[0]) if ep_rows > 0 else 0
    module.write(
        f"\nconst EMOJI_PRESENTATION_LEAVES: VArray<VArray<UInt8, ${ep_cols}>, ${ep_rows}> = [\n"
    )
    for leaf in emoji_presentation_leaves:
        module.write("    [\n")
        for row in batched(leaf, 15):
            module.write("       ")
            for entry in row:
                module.write(f" 0x{entry:02X}u8,")
            module.write("\n")
        module.write("    ],\n")
    module.write("]\n")

    # TEXT_PRESENTATION_LEAF_N -> let Array (variable-length, used as function args)
    for leaf_idx, leaf in enumerate(text_presentation_leaves):
        module.write(
            f"\nlet TEXT_PRESENTATION_LEAF_{leaf_idx}: Array<(UInt8, UInt8)> = [\n"
        )
        for lo, hi in leaf:
            module.write(f"    (0x{lo:02X}u8, 0x{hi:02X}u8),\n")
        module.write("]\n")

    # EMOJI_MODIFIER_LEAF_N -> let Array (variable-length, used as function args)
    for leaf_idx, leaf in enumerate(emoji_modifier_leaves):
        module.write(
            f"\nlet EMOJI_MODIFIER_LEAF_{leaf_idx}: Array<(UInt8, UInt8)> = [\n"
        )
        for lo, hi in leaf:
            module.write(f"    (0x{lo:02X}u8, 0x{hi:02X}u8),\n")
        module.write("]\n")


# ---------------------------------------------------------------------------
# Cangjie emission: lookup.cj
# ---------------------------------------------------------------------------


def emit_lookup_cj(
    module: IO[str],
    special_ranges: list[tuple[tuple[Codepoint, Codepoint], WidthState]],
    special_ranges_cjk: list[tuple[tuple[Codepoint, Codepoint], WidthState]],
):
    module.write("package unicode_width\n\n")

    for is_cjk in [False, True]:
        if is_cjk:
            fn_name = "lookupWidthCjk"
            root_name = "WIDTH_ROOT_CJK"
            ranges = special_ranges_cjk
        else:
            fn_name = "lookupWidth"
            root_name = "WIDTH_ROOT"
            ranges = special_ranges

        module.write(f"func {fn_name}(c: Rune): (UInt8, WidthInfo) {{\n")
        module.write(f"    let cp = Int64(UInt32(c))\n\n")
        module.write(f"    let t1Offset = {root_name}[cp >> {TABLE_SPLITS[1]}]\n\n")
        module.write(
            f"    let t2Offset = WIDTH_MIDDLE[Int64(t1Offset)][cp >> {TABLE_SPLITS[0]} & 0x{(2 ** (TABLE_SPLITS[1] - TABLE_SPLITS[0]) - 1):X}]\n\n"
        )
        module.write(
            f"    let packedWidths = WIDTH_LEAVES[Int64(t2Offset)][cp >> 2 & 0x{(2 ** (TABLE_SPLITS[0] - 2) - 1):X}]\n"
        )
        module.write(
            f"    let width = (packedWidths >> UInt8(2 * (cp & 0b11))) & 0b11u8\n\n"
        )
        module.write("    if (width < 3u8) {\n")
        module.write("        return (width, WidthInfo.DEFAULT)\n")
        module.write("    }\n\n")

        module.write("    let cpU32 = UInt32(c)\n")

        for (lo, hi), ws in ranges:
            if ws.is_carried():
                width_info = f"WidthInfo.{ws.name}"
            else:
                width_info = "WidthInfo.DEFAULT"
            w = ws.width_alone()
            if lo == hi:
                module.write(
                    f"    if (cpU32 == 0x{lo:X}u32) {{ return ({w}u8, {width_info}) }}\n"
                )
            else:
                module.write(
                    f"    if (cpU32 >= 0x{lo:X}u32 && cpU32 <= 0x{hi:X}u32) {{ return ({w}u8, {width_info}) }}\n"
                )

        module.write("    return (2u8, WidthInfo.EMOJI_PRESENTATION)\n")
        module.write("}\n\n")


# ---------------------------------------------------------------------------
# Cangjie emission: props.cj
# ---------------------------------------------------------------------------


def emit_props_cj(
    module: IO[str],
    ligature_transparent: list[tuple[Codepoint, Codepoint]],
    emoji_presentation_table: tuple[list[tuple[int, int]], list[list[int]]],
    text_presentation_table: tuple[list[tuple[int, int]], list[list[tuple[int, int]]]],
    emoji_modifier_table: tuple[list[tuple[int, int]], list[list[tuple[int, int]]]],
    joining_group_lam: list[tuple[Codepoint, Codepoint]],
):
    module.write("package unicode_width\n\n")

    # isJoiningGroupLam
    module.write("func isJoiningGroupLam(c: Rune): Bool {\n")
    module.write("    let cp = UInt32(c)\n")
    conditions = []
    for lo, hi in joining_group_lam:
        if lo == hi:
            conditions.append(f"cp == 0x{lo:X}u32")
        else:
            conditions.append(f"(cp >= 0x{lo:X}u32 && cp <= 0x{hi:X}u32)")
    module.write("    return " + " || ".join(conditions) + "\n")
    module.write("}\n\n")

    # isLigatureTransparent
    module.write("func isLigatureTransparent(c: Rune): Bool {\n")
    module.write("    let cp = UInt32(c)\n")
    conditions = []
    for lo, hi in ligature_transparent:
        if lo == hi:
            conditions.append(f"cp == 0x{lo:X}u32")
        else:
            conditions.append(f"(cp >= 0x{lo:X}u32 && cp <= 0x{hi:X}u32)")
    # Split into multiple lines for readability
    module.write("    return ")
    for i, cond in enumerate(conditions):
        if i > 0:
            module.write(" ||\n        ")
        module.write(cond)
    module.write("\n")
    module.write("}\n\n")

    # startsEmojiPresentationSeq - two level lookup with bitmap
    emoji_presentation_idx, _ = emoji_presentation_table
    module.write("func startsEmojiPresentationSeq(c: Rune): Bool {\n")
    module.write("    let cp = UInt32(c)\n")
    module.write("    let topBits = cp >> 10\n")
    module.write("    let idxOfLeaf: Int64 = match (topBits) {\n")
    for msbs, i in emoji_presentation_idx:
        module.write(f"        case 0x{msbs:X}u32 => {i}i64\n")
    module.write("        case _ => return false\n")
    module.write("    }\n")
    module.write("    let idxWithinLeaf = Int64((cp >> 3) & 0x7Fu32)\n")
    module.write("    let leafByte = EMOJI_PRESENTATION_LEAVES[idxOfLeaf][idxWithinLeaf]\n")
    module.write("    return ((leafByte >> UInt8(cp & 7u32)) & 1u8) == 1u8\n")
    module.write("}\n\n")

    # startsNonIdeographicTextPresentationSeq - binary search on ranges
    text_presentation_idx, _ = text_presentation_table
    module.write("func startsNonIdeographicTextPresentationSeq(c: Rune): Bool {\n")
    module.write("    let cp = UInt32(c)\n")
    module.write("    let topBits = cp >> 8\n")
    module.write("    let leaf: Array<(UInt8, UInt8)> = match (topBits) {\n")
    for msbs, i in text_presentation_idx:
        module.write(f"        case 0x{msbs:X}u32 => TEXT_PRESENTATION_LEAF_{i}\n")
    module.write("        case _ => return false\n")
    module.write("    }\n")
    module.write("    let bottomBits = UInt8(cp & 0xFFu32)\n")
    module.write("    return binarySearchRanges(leaf, bottomBits)\n")
    module.write("}\n\n")

    # isEmojiModifierBase - binary search on ranges
    emoji_modifier_idx, _ = emoji_modifier_table
    module.write("func isEmojiModifierBase(c: Rune): Bool {\n")
    module.write("    let cp = UInt32(c)\n")
    module.write("    let topBits = cp >> 8\n")
    module.write("    let leaf: Array<(UInt8, UInt8)> = match (topBits) {\n")
    for msbs, i in emoji_modifier_idx:
        module.write(f"        case 0x{msbs:X}u32 => EMOJI_MODIFIER_LEAF_{i}\n")
    module.write("        case _ => return false\n")
    module.write("    }\n")
    module.write("    let bottomBits = UInt8(cp & 0xFFu32)\n")
    module.write("    return binarySearchRanges(leaf, bottomBits)\n")
    module.write("}\n\n")

    # isTransparentZeroWidth
    module.write("func isTransparentZeroWidth(c: Rune): Bool {\n")
    module.write("    let result = lookupWidth(c)\n")
    module.write("    let w = result[0]\n")
    module.write("    if (w != 0u8) {\n")
    module.write("        return false\n")
    module.write("    }\n")
    module.write("    let cp = UInt32(c)\n")
    module.write("    return !binarySearchU32Ranges(NON_TRANSPARENT_ZERO_WIDTHS, cp)\n")
    module.write("}\n\n")

    # isSolidusTransparent
    module.write("func isSolidusTransparent(c: Rune): Bool {\n")
    module.write("    if (isLigatureTransparent(c)) {\n")
    module.write("        return true\n")
    module.write("    }\n")
    module.write("    let cp = UInt32(c)\n")
    module.write("    return binarySearchU32Ranges(SOLIDUS_TRANSPARENT, cp)\n")
    module.write("}\n\n")

    # binarySearchRanges
    module.write("func binarySearchRanges(ranges: Array<(UInt8, UInt8)>, target: UInt8): Bool {\n")
    module.write("    var lo: Int64 = 0i64\n")
    module.write("    var hi: Int64 = Int64(ranges.size) - 1i64\n")
    module.write("    while (lo <= hi) {\n")
    module.write("        let mid = (lo + hi) / 2i64\n")
    module.write("        let pair = ranges[mid]\n")
    module.write("        if (target < pair[0]) {\n")
    module.write("            hi = mid - 1i64\n")
    module.write("        } else if (target > pair[1]) {\n")
    module.write("            lo = mid + 1i64\n")
    module.write("        } else {\n")
    module.write("            return true\n")
    module.write("        }\n")
    module.write("    }\n")
    module.write("    return false\n")
    module.write("}\n\n")

    # binarySearchU32Ranges
    module.write("func binarySearchU32Ranges(ranges: Array<(UInt32, UInt32)>, target: UInt32): Bool {\n")
    module.write("    var lo: Int64 = 0i64\n")
    module.write("    var hi: Int64 = Int64(ranges.size) - 1i64\n")
    module.write("    while (lo <= hi) {\n")
    module.write("        let mid = (lo + hi) / 2i64\n")
    module.write("        let pair = ranges[mid]\n")
    module.write("        if (target < pair[0]) {\n")
    module.write("            hi = mid - 1i64\n")
    module.write("        } else if (target > pair[1]) {\n")
    module.write("            lo = mid + 1i64\n")
    module.write("        } else {\n")
    module.write("            return true\n")
    module.write("        }\n")
    module.write("    }\n")
    module.write("    return false\n")
    module.write("}\n")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate(output_dir: str):
    """Download Unicode data and generate tables.cj, lookup.cj, and props.cj."""
    print("\n=== Generating width tables ===")

    version = load_unicode_version()
    print(f"  Unicode version: {version[0]}.{version[1]}.{version[2]}")

    print("  Loading width maps...")
    (width_map, cjk_width_map) = load_width_maps()

    print("  Building tables...")
    tables = make_tables(width_map, cjk_width_map)

    special_ranges = make_special_ranges(width_map)
    cjk_special_ranges = make_special_ranges(cjk_width_map)

    print("  Loading emoji presentation sequences...")
    emoji_presentations = load_emoji_presentation_sequences()
    emoji_presentation_table = make_presentation_sequence_table(emoji_presentations)

    print("  Loading text presentation sequences...")
    text_presentations = load_text_presentation_sequences()
    text_presentation_table = make_ranges_table(text_presentations)

    print("  Loading emoji modifier bases...")
    emoji_modifier_bases = load_emoji_modifier_bases()
    emoji_modifier_table = make_ranges_table(emoji_modifier_bases)

    print("  Loading joining group lam...")
    joining_group_lam = load_joining_group_lam()
    non_transparent_zero_widths = load_non_transparent_zero_widths(width_map)
    ligature_transparent = load_ligature_transparent()
    solidus_transparent = load_solidus_transparent(ligature_transparent, cjk_width_map)

    # Print size info
    print("  ------------------------")
    total_size = 0
    for i, table in enumerate(tables):
        size_bytes = len(table.to_bytes())
        print(f"  Table {i} size: {size_bytes} bytes")
        total_size += size_bytes

    for s, table in [
        ("Emoji presentation", emoji_presentation_table),
    ]:
        index_size = len(table[0]) * (math.ceil(math.log(table[0][-1][0], 256)) + 8)
        print(f"  {s} index size: {index_size} bytes")
        total_size += index_size
        leaves_size = len(table[1]) * len(table[1][0])
        print(f"  {s} leaves size: {leaves_size} bytes")
        total_size += leaves_size

    for s, table in [
        ("Text presentation", text_presentation_table),
        ("Emoji modifier", emoji_modifier_table),
    ]:
        index_size = len(table[0]) * (math.ceil(math.log(table[0][-1][0], 256)) + 16)
        print(f"  {s} index size: {index_size} bytes")
        total_size += index_size
        leaves_size = 2 * sum(map(len, table[1]))
        print(f"  {s} leaves size: {leaves_size} bytes")
        total_size += leaves_size

    for s, tbl in [
        ("Non transparent zero width", non_transparent_zero_widths),
        ("Solidus transparent", solidus_transparent),
    ]:
        table_size = 6 * len(tbl)
        print(f"  {s} table size: {table_size} bytes")
        total_size += table_size
    print("  ------------------------")
    print(f"    Total size: {total_size} bytes")

    # Emit tables.cj
    tables_path = f"{output_dir}/unicode-width/src/tables.cj"
    emit_cangjie_file(
        tables_path,
        lambda f: emit_tables_cj(
            f,
            version,
            tables,
            emoji_presentation_table,
            text_presentation_table,
            emoji_modifier_table,
            non_transparent_zero_widths,
            solidus_transparent,
        ),
    )
    print(f'  Wrote to "{tables_path}"')

    # Emit lookup.cj
    lookup_path = f"{output_dir}/unicode-width/src/lookup.cj"
    emit_cangjie_file(
        lookup_path,
        lambda f: emit_lookup_cj(
            f,
            special_ranges,
            cjk_special_ranges,
        ),
    )
    print(f'  Wrote to "{lookup_path}"')

    # Emit props.cj
    props_path = f"{output_dir}/unicode-width/src/props.cj"
    emit_cangjie_file(
        props_path,
        lambda f: emit_props_cj(
            f,
            ligature_transparent,
            emoji_presentation_table,
            text_presentation_table,
            emoji_modifier_table,
            joining_group_lam,
        ),
    )
    print(f'  Wrote to "{props_path}"')
