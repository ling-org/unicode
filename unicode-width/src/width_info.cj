package unicode_width

public struct WidthInfo <: Equatable<WidthInfo> {
    public let value: UInt16

    public init(v: UInt16) {
        value = v
    }

    // Constants
    public static let DEFAULT = WidthInfo(0u16)
    public static let LINE_FEED = WidthInfo(0b0000000000000001u16)
    public static let EMOJI_MODIFIER = WidthInfo(0b0000000000000010u16)
    public static let REGIONAL_INDICATOR = WidthInfo(0b0000000000000011u16)
    public static let SEVERAL_REGIONAL_INDICATOR = WidthInfo(0b0000000000000100u16)
    public static let EMOJI_PRESENTATION = WidthInfo(0b0000000000000101u16)
    public static let ZWJ_EMOJI_PRESENTATION = WidthInfo(0b0001000000000110u16)
    public static let VS16_ZWJ_EMOJI_PRESENTATION = WidthInfo(0b1001000000000110u16)
    public static let KEYCAP_ZWJ_EMOJI_PRESENTATION = WidthInfo(0b0001000000000111u16)
    public static let VS16_KEYCAP_ZWJ_EMOJI_PRESENTATION = WidthInfo(0b1001000000000111u16)
    public static let REGIONAL_INDICATOR_ZWJ_PRESENTATION = WidthInfo(0b0000000000001001u16)
    public static let EVEN_REGIONAL_INDICATOR_ZWJ_PRESENTATION = WidthInfo(0b0000000000001010u16)
    public static let ODD_REGIONAL_INDICATOR_ZWJ_PRESENTATION = WidthInfo(0b0000000000001011u16)
    public static let TAG_END_ZWJ_EMOJI_PRESENTATION = WidthInfo(0b0000000000010000u16)
    public static let TAG_D1_END_ZWJ_EMOJI_PRESENTATION = WidthInfo(0b0000000000010001u16)
    public static let TAG_D2_END_ZWJ_EMOJI_PRESENTATION = WidthInfo(0b0000000000010010u16)
    public static let TAG_D3_END_ZWJ_EMOJI_PRESENTATION = WidthInfo(0b0000000000010011u16)
    public static let TAG_A1_END_ZWJ_EMOJI_PRESENTATION = WidthInfo(0b0000000000011001u16)
    public static let TAG_A2_END_ZWJ_EMOJI_PRESENTATION = WidthInfo(0b0000000000011010u16)
    public static let TAG_A3_END_ZWJ_EMOJI_PRESENTATION = WidthInfo(0b0000000000011011u16)
    public static let TAG_A4_END_ZWJ_EMOJI_PRESENTATION = WidthInfo(0b0000000000011100u16)
    public static let TAG_A5_END_ZWJ_EMOJI_PRESENTATION = WidthInfo(0b0000000000011101u16)
    public static let TAG_A6_END_ZWJ_EMOJI_PRESENTATION = WidthInfo(0b0000000000011110u16)
    public static let KIRAT_RAI_VOWEL_SIGN_E = WidthInfo(0b0000000000100000u16)
    public static let KIRAT_RAI_VOWEL_SIGN_AI = WidthInfo(0b0000000000100001u16)
    public static let VARIATION_SELECTOR_1_2_OR_3 = WidthInfo(0b0000001000000000u16)
    public static let VARIATION_SELECTOR_15 = WidthInfo(0b0100000000000000u16)
    public static let VARIATION_SELECTOR_16 = WidthInfo(0b1000000000000000u16)
    public static let JOINING_GROUP_ALEF = WidthInfo(0b0011000011111111u16)
    public static let COMBINING_LONG_SOLIDUS_OVERLAY = WidthInfo(0b0011110011111111u16)
    public static let SOLIDUS_OVERLAY_ALEF = WidthInfo(0b0011100011111111u16)
    public static let HEBREW_LETTER_LAMED = WidthInfo(0b0011100000000000u16)
    public static let ZWJ_HEBREW_LETTER_LAMED = WidthInfo(0b0011110000000000u16)
    public static let BUGINESE_LETTER_YA = WidthInfo(0b0011100000000001u16)
    public static let ZWJ_BUGINESE_LETTER_YA = WidthInfo(0b0011110000000001u16)
    public static let BUGINESE_VOWEL_SIGN_I_ZWJ_LETTER_YA = WidthInfo(0b0011110000000010u16)
    public static let TIFINAGH_CONSONANT = WidthInfo(0b0011100000000011u16)
    public static let ZWJ_TIFINAGH_CONSONANT = WidthInfo(0b0011110000000011u16)
    public static let TIFINAGH_JOINER_CONSONANT = WidthInfo(0b0011110000000100u16)
    public static let LISU_TONE_LETTER_MYA_NA_JEU = WidthInfo(0b0011110000000101u16)
    public static let OLD_TURKIC_LETTER_ORKHON_I = WidthInfo(0b0011100000000110u16)
    public static let ZWJ_OLD_TURKIC_LETTER_ORKHON_I = WidthInfo(0b0011110000000110u16)
    public static let KHMER_COENG_ELIGIBLE_LETTER = WidthInfo(0b0011110000000111u16)

    static let LIGATURE_TRANSPARENT_MASK: UInt16 = 0b0010000000000000u16

    public func isLigatureTransparent(): Bool {
        (value & 0b0000100000000000u16) == 0b0000100000000000u16
    }

    public func setZwjBit(): WidthInfo {
        WidthInfo(value | 0b0000010000000000u16)
    }

    public func isEmojiPresentation(): Bool {
        (value & VARIATION_SELECTOR_16.value) == VARIATION_SELECTOR_16.value
    }

    public func isZwjEmojiPresentation(): Bool {
        (value & 0b1011000000000000u16) == 0b1001000000000000u16
    }

    public func setEmojiPresentation(): WidthInfo {
        if ((value & LIGATURE_TRANSPARENT_MASK) == LIGATURE_TRANSPARENT_MASK ||
            (value & 0b1001000000000000u16) == 0b0001000000000000u16) {
            WidthInfo((value | VARIATION_SELECTOR_16.value) & (VARIATION_SELECTOR_15.value ^ 0xFFFFu16) & (VARIATION_SELECTOR_1_2_OR_3.value ^ 0xFFFFu16))
        } else {
            VARIATION_SELECTOR_16
        }
    }

    public func unsetEmojiPresentation(): WidthInfo {
        if ((value & LIGATURE_TRANSPARENT_MASK) == LIGATURE_TRANSPARENT_MASK) {
            WidthInfo(value & (VARIATION_SELECTOR_16.value ^ 0xFFFFu16))
        } else {
            DEFAULT
        }
    }

    public func isTextPresentation(): Bool {
        (value & VARIATION_SELECTOR_15.value) == VARIATION_SELECTOR_15.value
    }

    public func setTextPresentation(): WidthInfo {
        if ((value & LIGATURE_TRANSPARENT_MASK) == LIGATURE_TRANSPARENT_MASK) {
            WidthInfo((value | VARIATION_SELECTOR_15.value) & (VARIATION_SELECTOR_16.value ^ 0xFFFFu16) & (VARIATION_SELECTOR_1_2_OR_3.value ^ 0xFFFFu16))
        } else {
            WidthInfo(VARIATION_SELECTOR_15.value)
        }
    }

    public func unsetTextPresentation(): WidthInfo {
        WidthInfo(value & (VARIATION_SELECTOR_15.value ^ 0xFFFFu16))
    }

    public func isVs123(): Bool {
        (value & VARIATION_SELECTOR_1_2_OR_3.value) == VARIATION_SELECTOR_1_2_OR_3.value
    }

    public func setVs123(): WidthInfo {
        if ((value & LIGATURE_TRANSPARENT_MASK) == LIGATURE_TRANSPARENT_MASK) {
            WidthInfo((value | VARIATION_SELECTOR_1_2_OR_3.value) & (VARIATION_SELECTOR_15.value ^ 0xFFFFu16) & (VARIATION_SELECTOR_16.value ^ 0xFFFFu16))
        } else {
            WidthInfo(VARIATION_SELECTOR_1_2_OR_3.value)
        }
    }

    public func unsetVs123(): WidthInfo {
        WidthInfo(value & (VARIATION_SELECTOR_1_2_OR_3.value ^ 0xFFFFu16))
    }

    public operator func ==(rhs: WidthInfo): Bool {
        value == rhs.value
    }

    public operator func !=(rhs: WidthInfo): Bool {
        value != rhs.value
    }
}
