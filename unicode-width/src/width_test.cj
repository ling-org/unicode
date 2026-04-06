package unicode_width

import std.unittest.*
import std.unittest.testmacro.*

@Test
public class CharWidthTest {
    @TestCase
    public func testControlChars(): Unit {
        @Expect(Option<Int64>.None, charWidth(r'\u{0}'))
        @Expect(Option<Int64>.None, charWidth(r'\u{1}'))
        @Expect(Option<Int64>.None, charWidth(r'\u{1F}'))
        @Expect(Option<Int64>.None, charWidth(r'\u{7F}'))
    }

    @TestCase
    public func testAscii(): Unit {
        @Expect(Some(1i64), charWidth(r' '))
        @Expect(Some(1i64), charWidth(r'a'))
        @Expect(Some(1i64), charWidth(r'z'))
        @Expect(Some(1i64), charWidth(r'A'))
        @Expect(Some(1i64), charWidth(r'~'))
    }

    @TestCase
    public func testCjkIdeograph(): Unit {
        // CJK Unified Ideographs
        @Expect(Some(2i64), charWidth(r'\u{4E00}'))  // 一
        @Expect(Some(2i64), charWidth(r'\u{4E2D}'))  // 中
        @Expect(Some(2i64), charWidth(r'\u{6587}'))  // 文
    }

    @TestCase
    public func testFullwidth(): Unit {
        @Expect(Some(2i64), charWidth(r'\u{FF21}'))  // Ａ
        @Expect(Some(2i64), charWidth(r'\u{FF41}'))  // ａ
        @Expect(Some(2i64), charWidth(r'\u{FF10}'))  // ０
    }

    @TestCase
    public func testHalfwidth(): Unit {
        @Expect(Some(1i64), charWidth(r'\u{FF61}'))  // ｡
    }

    @TestCase
    public func testZeroWidth(): Unit {
        // Combining mark
        @Expect(Some(0i64), charWidth(r'\u{0300}'))
        // Zero-width space
        @Expect(Some(0i64), charWidth(r'\u{200B}'))
    }
}

@Test
public class CharWidthCJKTest {
    @TestCase
    public func testAmbiguous(): Unit {
        // These are ambiguous width chars - narrow in non-CJK, wide in CJK
        // U+00A1 INVERTED EXCLAMATION MARK is Narrow (not Ambiguous)
        // Let's test some actual ambiguous chars
        @Expect(Some(1i64), charWidth(r'\u{2010}'))    // HYPHEN - narrow
        @Expect(Some(2i64), charWidthCJK(r'\u{2010}')) // HYPHEN - wide in CJK
    }
}

@Test
public class StrWidthTest {
    @TestCase
    public func testEmpty(): Unit {
        @Expect(0i64, strWidth(""))
    }

    @TestCase
    public func testAscii(): Unit {
        @Expect(5i64, strWidth("hello"))
    }

    @TestCase
    public func testFullwidthStr(): Unit {
        // Ｈｅｌｌｏ (5 fullwidth chars = 10 columns)
        @Expect(10i64, strWidth("\u{FF28}\u{FF45}\u{FF4C}\u{FF4C}\u{FF4F}"))
    }

    @TestCase
    public func testMixed(): Unit {
        // "ab中文cd" = 2(ascii) + 2*2(CJK) + 2(ascii) = 8
        @Expect(8i64, strWidth("ab\u{4E2D}\u{6587}cd"))
    }

    @TestCase
    public func testCRLF(): Unit {
        @Expect(1i64, strWidth("\r\n"))
    }

    @TestCase
    public func testLineFeed(): Unit {
        @Expect(1i64, strWidth("\n"))
    }

    @TestCase
    public func testEmoji(): Unit {
        // Single emoji (has Emoji_Presentation)
        @Expect(2i64, strWidth("\u{1F600}"))
    }

    @TestCase
    public func testEmojiZWJSequence(): Unit {
        // Family emoji: 👨‍👩‍👧‍👦
        // This is a ZWJ sequence: 1F468 200D 1F469 200D 1F467 200D 1F466
        @Expect(2i64, strWidth("\u{1F468}\u{200D}\u{1F469}\u{200D}\u{1F467}\u{200D}\u{1F466}"))
    }

    @TestCase
    public func testEmojiModifierSequence(): Unit {
        // 👍🏽 (thumbs up + skin tone)
        @Expect(2i64, strWidth("\u{1F44D}\u{1F3FD}"))
    }

    @TestCase
    public func testFlagEmoji(): Unit {
        // 🇺🇸 (regional indicators U + S)
        @Expect(2i64, strWidth("\u{1F1FA}\u{1F1F8}"))
    }
}

@Test
public class StrWidthCJKTest {
    @TestCase
    public func testBasic(): Unit {
        @Expect(5i64, strWidthCJK("hello"))
    }

    @TestCase
    public func testAmbiguousInCJK(): Unit {
        // In CJK context, ambiguous chars are 2 columns wide
        // Test with string width too
        @Expect(2i64, strWidthCJK("\u{2010}"))  // HYPHEN
    }
}

@Test
public class UnicodeVersionTest {
    @TestCase
    public func testVersion(): Unit {
        @Expect(17u8, UNICODE_VERSION[0])
        @Expect(0u8, UNICODE_VERSION[1])
        @Expect(0u8, UNICODE_VERSION[2])
    }
}
