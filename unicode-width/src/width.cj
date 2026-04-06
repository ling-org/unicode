package unicode_width

public func charWidth(c: Rune): Option<Int64> {
    if (c < r'\u{7F}') {
        if (c >= r'\u{20}') {
            Some(1i64)
        } else {
            None
        }
    } else if (c >= r'\u{A0}') {
        let result = lookupWidth(c)
        Some(Int64(result[0]))
    } else {
        None
    }
}

public func charWidthCJK(c: Rune): Option<Int64> {
    if (c < r'\u{7F}') {
        if (c >= r'\u{20}') {
            Some(1i64)
        } else {
            None
        }
    } else if (c >= r'\u{A0}') {
        let result = lookupWidthCjk(c)
        Some(Int64(result[0]))
    } else {
        None
    }
}

public func strWidth(s: String): Int64 {
    strWidthImpl(s, false)
}

public func strWidthCJK(s: String): Int64 {
    strWidthImpl(s, true)
}

func strWidthImpl(s: String, isCjk: Bool): Int64 {
    let runes = s.toRuneArray()
    var sum: Int64 = 0
    var nextInfo = WidthInfo.DEFAULT
    var i: Int64 = runes.size - 1
    while (i >= 0) {
        let result = widthInGeneric(runes[i], nextInfo, isCjk)
        sum += Int64(result[0])
        nextInfo = result[1]
        i -= 1
    }
    sum
}

func lookupWidthGeneric(c: Rune, isCjk: Bool): (UInt8, WidthInfo) {
    if (isCjk) {
        return lookupWidthCjk(c)
    }
    return lookupWidth(c)
}

func widthInGeneric(c: Rune, nextInfoArg: WidthInfo, isCjk: Bool): (Int8, WidthInfo) {
    var nextInfo = nextInfoArg

    // Emoji presentation check
    if (nextInfo.isEmojiPresentation()) {
        if (startsEmojiPresentationSeq(c)) {
            let w: Int8 = if (nextInfo.isZwjEmojiPresentation()) { 0i8 } else { 2i8 }
            return (w, WidthInfo.EMOJI_PRESENTATION)
        } else {
            nextInfo = nextInfo.unsetEmojiPresentation()
        }
    }

    // CJK solidus overlay
    if (isCjk &&
        (nextInfo == WidthInfo.COMBINING_LONG_SOLIDUS_OVERLAY ||
         nextInfo == WidthInfo.SOLIDUS_OVERLAY_ALEF)) {
        let cpVal = UInt32(c)
        if (cpVal == 0x3Cu32 || cpVal == 0x3Du32 || cpVal == 0x3Eu32) {
            return (2i8, WidthInfo.DEFAULT)
        }
    }

    // ASCII and control path
    if (c <= r'\u{A0}') {
        let cpVal = UInt32(c)
        if (cpVal == 0x0Au32) {
            return (1i8, WidthInfo.LINE_FEED)
        }
        if (cpVal == 0x0Du32 && nextInfo == WidthInfo.LINE_FEED) {
            return (0i8, WidthInfo.DEFAULT)
        }
        return (1i8, WidthInfo.DEFAULT)
    }

    // Non-default nextInfo processing
    if (nextInfo != WidthInfo.DEFAULT) {
        let cpVal = UInt32(c)

        // VS16 (FE0F)
        if (cpVal == 0xFE0Fu32) {
            return (0i8, nextInfo.setEmojiPresentation())
        }

        if (isCjk) {
            // CJK: FE00 or FE02
            if (cpVal == 0xFE00u32 || cpVal == 0xFE02u32) {
                return (0i8, nextInfo.setVs123())
            }
        } else {
            // Non-CJK: FE01
            if (cpVal == 0xFE01u32) {
                return (0i8, nextInfo.setVs123())
            }
            // FE0E
            if (cpVal == 0xFE0Eu32) {
                return (0i8, nextInfo.setTextPresentation())
            }
            if (nextInfo.isTextPresentation()) {
                if (startsNonIdeographicTextPresentationSeq(c)) {
                    return (1i8, WidthInfo.DEFAULT)
                } else {
                    nextInfo = nextInfo.unsetTextPresentation()
                }
            }
        }

        if (nextInfo.isVs123()) {
            if (cpVal == 0x2018u32 || cpVal == 0x2019u32 ||
                cpVal == 0x201Cu32 || cpVal == 0x201Du32) {
                let w: Int8 = if (isCjk) { 1i8 } else { 2i8 }
                return (w, WidthInfo.DEFAULT)
            } else {
                nextInfo = nextInfo.unsetVs123()
            }
        }

        if (nextInfo.isLigatureTransparent()) {
            if (cpVal == 0x200Du32) {
                return (0i8, nextInfo.setZwjBit())
            } else if (isLigatureTransparent(c)) {
                return (0i8, nextInfo)
            }
        }

        // CJK solidus transparent
        if (isCjk && nextInfo == WidthInfo.COMBINING_LONG_SOLIDUS_OVERLAY && isSolidusTransparent(c)) {
            let ret = lookupWidthGeneric(c, isCjk)
            return (Int8(ret[0]), WidthInfo.COMBINING_LONG_SOLIDUS_OVERLAY)
        }

        // Alef + solidus overlay (CJK)
        if (nextInfo == WidthInfo.JOINING_GROUP_ALEF && cpVal == 0x0338u32 && isCjk) {
            return (0i8, WidthInfo.SOLIDUS_OVERLAY_ALEF)
        }

        // Arabic Lam-Alef ligature
        if (nextInfo == WidthInfo.JOINING_GROUP_ALEF && isJoiningGroupLam(c)) {
            return (0i8, WidthInfo.DEFAULT)
        }
        if (isCjk && nextInfo == WidthInfo.SOLIDUS_OVERLAY_ALEF && isJoiningGroupLam(c)) {
            return (0i8, WidthInfo.DEFAULT)
        }
        if (nextInfo == WidthInfo.JOINING_GROUP_ALEF && isTransparentZeroWidth(c)) {
            return (0i8, WidthInfo.JOINING_GROUP_ALEF)
        }

        // Hebrew Alef-ZWJ-Lamed
        if (nextInfo == WidthInfo.ZWJ_HEBREW_LETTER_LAMED && cpVal == 0x05D0u32) {
            return (0i8, WidthInfo.DEFAULT)
        }

        // Khmer coeng signs
        if (nextInfo == WidthInfo.KHMER_COENG_ELIGIBLE_LETTER && cpVal == 0x17D2u32) {
            return (-1i8, WidthInfo.DEFAULT)
        }

        // Buginese <a, -i> ZWJ ya ligature
        if (nextInfo == WidthInfo.ZWJ_BUGINESE_LETTER_YA && cpVal == 0x1A17u32) {
            return (0i8, WidthInfo.BUGINESE_VOWEL_SIGN_I_ZWJ_LETTER_YA)
        }
        if (nextInfo == WidthInfo.BUGINESE_VOWEL_SIGN_I_ZWJ_LETTER_YA && cpVal == 0x1A15u32) {
            return (0i8, WidthInfo.DEFAULT)
        }

        // Tifinagh bi-consonants
        if ((nextInfo == WidthInfo.TIFINAGH_CONSONANT || nextInfo == WidthInfo.ZWJ_TIFINAGH_CONSONANT) && cpVal == 0x2D7Fu32) {
            return (1i8, WidthInfo.TIFINAGH_JOINER_CONSONANT)
        }
        if (nextInfo == WidthInfo.ZWJ_TIFINAGH_CONSONANT &&
            ((cpVal >= 0x2D31u32 && cpVal <= 0x2D65u32) || cpVal == 0x2D6Fu32)) {
            return (0i8, WidthInfo.DEFAULT)
        }
        if (nextInfo == WidthInfo.TIFINAGH_JOINER_CONSONANT &&
            ((cpVal >= 0x2D31u32 && cpVal <= 0x2D65u32) || cpVal == 0x2D6Fu32)) {
            return (-1i8, WidthInfo.DEFAULT)
        }

        // Lisu tone letter combinations
        if (nextInfo == WidthInfo.LISU_TONE_LETTER_MYA_NA_JEU &&
            cpVal >= 0xA4F8u32 && cpVal <= 0xA4FBu32) {
            return (0i8, WidthInfo.DEFAULT)
        }

        // Old Turkic ligature
        if (nextInfo == WidthInfo.ZWJ_OLD_TURKIC_LETTER_ORKHON_I && cpVal == 0x10C32u32) {
            return (0i8, WidthInfo.DEFAULT)
        }

        // Emoji modifier
        if (nextInfo == WidthInfo.EMOJI_MODIFIER && isEmojiModifierBase(c)) {
            return (0i8, WidthInfo.EMOJI_PRESENTATION)
        }

        // Regional indicator
        if ((nextInfo == WidthInfo.REGIONAL_INDICATOR || nextInfo == WidthInfo.SEVERAL_REGIONAL_INDICATOR) &&
            cpVal >= 0x1F1E6u32 && cpVal <= 0x1F1FFu32) {
            return (1i8, WidthInfo.SEVERAL_REGIONAL_INDICATOR)
        }

        // ZWJ emoji sequences
        if ((nextInfo == WidthInfo.EMOJI_PRESENTATION ||
             nextInfo == WidthInfo.SEVERAL_REGIONAL_INDICATOR ||
             nextInfo == WidthInfo.EVEN_REGIONAL_INDICATOR_ZWJ_PRESENTATION ||
             nextInfo == WidthInfo.ODD_REGIONAL_INDICATOR_ZWJ_PRESENTATION ||
             nextInfo == WidthInfo.EMOJI_MODIFIER) && cpVal == 0x200Du32) {
            return (0i8, WidthInfo.ZWJ_EMOJI_PRESENTATION)
        }

        if (nextInfo == WidthInfo.ZWJ_EMOJI_PRESENTATION && cpVal == 0x20E3u32) {
            return (0i8, WidthInfo.KEYCAP_ZWJ_EMOJI_PRESENTATION)
        }

        if (nextInfo == WidthInfo.VS16_ZWJ_EMOJI_PRESENTATION && startsEmojiPresentationSeq(c)) {
            return (0i8, WidthInfo.EMOJI_PRESENTATION)
        }

        if (nextInfo == WidthInfo.VS16_KEYCAP_ZWJ_EMOJI_PRESENTATION &&
            ((cpVal >= 0x30u32 && cpVal <= 0x39u32) || cpVal == 0x23u32 || cpVal == 0x2Au32)) {
            return (0i8, WidthInfo.EMOJI_PRESENTATION)
        }

        if (nextInfo == WidthInfo.ZWJ_EMOJI_PRESENTATION &&
            cpVal >= 0x1F1E6u32 && cpVal <= 0x1F1FFu32) {
            return (1i8, WidthInfo.REGIONAL_INDICATOR_ZWJ_PRESENTATION)
        }

        if ((nextInfo == WidthInfo.REGIONAL_INDICATOR_ZWJ_PRESENTATION ||
             nextInfo == WidthInfo.ODD_REGIONAL_INDICATOR_ZWJ_PRESENTATION) &&
            cpVal >= 0x1F1E6u32 && cpVal <= 0x1F1FFu32) {
            return (-1i8, WidthInfo.EVEN_REGIONAL_INDICATOR_ZWJ_PRESENTATION)
        }

        if (nextInfo == WidthInfo.EVEN_REGIONAL_INDICATOR_ZWJ_PRESENTATION &&
            cpVal >= 0x1F1E6u32 && cpVal <= 0x1F1FFu32) {
            return (3i8, WidthInfo.ODD_REGIONAL_INDICATOR_ZWJ_PRESENTATION)
        }

        if (nextInfo == WidthInfo.ZWJ_EMOJI_PRESENTATION &&
            cpVal >= 0x1F3FBu32 && cpVal <= 0x1F3FFu32) {
            return (0i8, WidthInfo.EMOJI_MODIFIER)
        }

        // Tag sequences
        if (nextInfo == WidthInfo.ZWJ_EMOJI_PRESENTATION && cpVal == 0xE007Fu32) {
            return (0i8, WidthInfo.TAG_END_ZWJ_EMOJI_PRESENTATION)
        }
        if (nextInfo == WidthInfo.TAG_END_ZWJ_EMOJI_PRESENTATION &&
            cpVal >= 0xE0061u32 && cpVal <= 0xE007Au32) {
            return (0i8, WidthInfo.TAG_A1_END_ZWJ_EMOJI_PRESENTATION)
        }
        if (nextInfo == WidthInfo.TAG_A1_END_ZWJ_EMOJI_PRESENTATION &&
            cpVal >= 0xE0061u32 && cpVal <= 0xE007Au32) {
            return (0i8, WidthInfo.TAG_A2_END_ZWJ_EMOJI_PRESENTATION)
        }
        if (nextInfo == WidthInfo.TAG_A2_END_ZWJ_EMOJI_PRESENTATION &&
            cpVal >= 0xE0061u32 && cpVal <= 0xE007Au32) {
            return (0i8, WidthInfo.TAG_A3_END_ZWJ_EMOJI_PRESENTATION)
        }
        if (nextInfo == WidthInfo.TAG_A3_END_ZWJ_EMOJI_PRESENTATION &&
            cpVal >= 0xE0061u32 && cpVal <= 0xE007Au32) {
            return (0i8, WidthInfo.TAG_A4_END_ZWJ_EMOJI_PRESENTATION)
        }
        if (nextInfo == WidthInfo.TAG_A4_END_ZWJ_EMOJI_PRESENTATION &&
            cpVal >= 0xE0061u32 && cpVal <= 0xE007Au32) {
            return (0i8, WidthInfo.TAG_A5_END_ZWJ_EMOJI_PRESENTATION)
        }
        if (nextInfo == WidthInfo.TAG_A5_END_ZWJ_EMOJI_PRESENTATION &&
            cpVal >= 0xE0061u32 && cpVal <= 0xE007Au32) {
            return (0i8, WidthInfo.TAG_A6_END_ZWJ_EMOJI_PRESENTATION)
        }

        // Tag digit sequences
        if ((nextInfo == WidthInfo.TAG_END_ZWJ_EMOJI_PRESENTATION ||
             nextInfo == WidthInfo.TAG_A1_END_ZWJ_EMOJI_PRESENTATION ||
             nextInfo == WidthInfo.TAG_A2_END_ZWJ_EMOJI_PRESENTATION ||
             nextInfo == WidthInfo.TAG_A3_END_ZWJ_EMOJI_PRESENTATION ||
             nextInfo == WidthInfo.TAG_A4_END_ZWJ_EMOJI_PRESENTATION) &&
            cpVal >= 0xE0030u32 && cpVal <= 0xE0039u32) {
            return (0i8, WidthInfo.TAG_D1_END_ZWJ_EMOJI_PRESENTATION)
        }
        if (nextInfo == WidthInfo.TAG_D1_END_ZWJ_EMOJI_PRESENTATION &&
            cpVal >= 0xE0030u32 && cpVal <= 0xE0039u32) {
            return (0i8, WidthInfo.TAG_D2_END_ZWJ_EMOJI_PRESENTATION)
        }
        if (nextInfo == WidthInfo.TAG_D2_END_ZWJ_EMOJI_PRESENTATION &&
            cpVal >= 0xE0030u32 && cpVal <= 0xE0039u32) {
            return (0i8, WidthInfo.TAG_D3_END_ZWJ_EMOJI_PRESENTATION)
        }

        // Flag emoji
        if ((nextInfo == WidthInfo.TAG_A3_END_ZWJ_EMOJI_PRESENTATION ||
             nextInfo == WidthInfo.TAG_A4_END_ZWJ_EMOJI_PRESENTATION ||
             nextInfo == WidthInfo.TAG_A5_END_ZWJ_EMOJI_PRESENTATION ||
             nextInfo == WidthInfo.TAG_A6_END_ZWJ_EMOJI_PRESENTATION ||
             nextInfo == WidthInfo.TAG_D3_END_ZWJ_EMOJI_PRESENTATION) && cpVal == 0x1F3F4u32) {
            return (0i8, WidthInfo.EMOJI_PRESENTATION)
        }

        // Generic ZWJ emoji fallback
        if (nextInfo == WidthInfo.ZWJ_EMOJI_PRESENTATION) {
            let result = lookupWidthGeneric(c, isCjk)
            if (result[1] == WidthInfo.EMOJI_PRESENTATION) {
                return (0i8, WidthInfo.EMOJI_PRESENTATION)
            }
        }

        // Kirat Rai vowel signs
        if (nextInfo == WidthInfo.KIRAT_RAI_VOWEL_SIGN_E && cpVal == 0x16D63u32) {
            return (0i8, WidthInfo.DEFAULT)
        }
        if (nextInfo == WidthInfo.KIRAT_RAI_VOWEL_SIGN_E && cpVal == 0x16D67u32) {
            return (0i8, WidthInfo.KIRAT_RAI_VOWEL_SIGN_AI)
        }
        if (nextInfo == WidthInfo.KIRAT_RAI_VOWEL_SIGN_E && cpVal == 0x16D68u32) {
            return (1i8, WidthInfo.KIRAT_RAI_VOWEL_SIGN_E)
        }
        if (nextInfo == WidthInfo.KIRAT_RAI_VOWEL_SIGN_E && cpVal == 0x16D69u32) {
            return (0i8, WidthInfo.DEFAULT)
        }
        if (nextInfo == WidthInfo.KIRAT_RAI_VOWEL_SIGN_AI && cpVal == 0x16D63u32) {
            return (0i8, WidthInfo.DEFAULT)
        }
    }

    // Fallback: table lookup
    let ret = lookupWidthGeneric(c, isCjk)
    return (Int8(ret[0]), ret[1])
}
