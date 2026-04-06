package unicode_case

import std.unittest.*
import std.unittest.testmacro.*

@Test
public class CaseEqTest {
    @TestCase
    public func testAsciiCaseInsensitive(): Unit {
        @Expect(true, eq("foo bar", "FoO BAR"))
        @Expect(true, eq("foobar", "FOOBAR"))
        @Expect(true, eq("", ""))
    }

    @TestCase
    public func testNotEqual(): Unit {
        @Expect(false, eq("foo", "foobar"))
        @Expect(false, eq("foobar", "foo"))
        @Expect(false, eq("foo", "bar"))
    }

    @TestCase
    public func testSimpleCaseFolding(): Unit {
        // Greek sigma variants: ς (U+03C2 final sigma) folds to σ (U+03C3)
        @Expect(true, eq("\u{03C3}\u{03C4}\u{03B9}\u{03B3}\u{03BC}\u{03B1}\u{03C2}",
                         "\u{03C3}\u{03C4}\u{03B9}\u{03B3}\u{03BC}\u{03B1}\u{03C3}"))
    }

    @TestCase
    public func testFullCaseFolding(): Unit {
        // ﬂ (U+FB02 latin small ligature fl) folds to "fl"
        @Expect(true, eq("\u{FB02}our", "flour"))
        // ß (U+00DF) folds to "ss"
        @Expect(true, eq("Ma\u{00DF}e", "MASSE"))
        // ᾲ (U+1FB2) folds to ὰι
        @Expect(true, eq("\u{1FB2} \u{03C3}\u{03C4}\u{03BF} \u{03B4}\u{03B9}\u{03AC}\u{03BF}\u{03BB}\u{03BF}",
                         "\u{1F70}\u{03B9} \u{03C3}\u{03C4}\u{03BF} \u{03B4}\u{03B9}\u{03AC}\u{03BF}\u{03BB}\u{03BF}"))
    }

    @TestCase
    public func testSingleChar(): Unit {
        @Expect(true, eq("A", "a"))
        @Expect(true, eq("Z", "z"))
        @Expect(false, eq("A", "b"))
    }
}

@Test
public class ToFoldedCaseTest {
    @TestCase
    public func testBasic(): Unit {
        @Expect("masse", toFoldedCase("Ma\u{00DF}e"))
        @Expect("foo bar", toFoldedCase("FOO BAR"))
        @Expect("", toFoldedCase(""))
    }

    @TestCase
    public func testAlreadyFolded(): Unit {
        @Expect("hello", toFoldedCase("hello"))
    }

    @TestCase
    public func testLigature(): Unit {
        @Expect("flour", toFoldedCase("\u{FB02}our"))
    }
}

@Test
public class FoldedRunesTest {
    @TestCase
    public func testAsciiChar(): Unit {
        let result = foldedRunes(r'A')
        @Expect(1, result.size)
        @Expect(r'a', result[0])
    }

    @TestCase
    public func testLowercaseUnchanged(): Unit {
        let result = foldedRunes(r'a')
        @Expect(1, result.size)
        @Expect(r'a', result[0])
    }

    @TestCase
    public func testEszett(): Unit {
        // ß folds to ss
        let result = foldedRunes(r'\u{00DF}')
        @Expect(2, result.size)
        @Expect(r's', result[0])
        @Expect(r's', result[1])
    }
}
