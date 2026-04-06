# unicode-width

按照 [UAX #11](https://www.unicode.org/reports/tr11/) 计算 Unicode 字符和字符串的显示宽度。基于 Unicode 17.0.0。

支持 emoji ZWJ 序列、变体选择符、CJK 上下文、阿拉伯语连字等复杂场景。

## 使用

```toml
[dependencies]
  unicode_width = { version = "0.1.0" }
```

```cangjie
import unicode_width.*

main() {
    // 单字符宽度
    println(charWidth(r'a'))             // Some(1)
    println(charWidth(r'\u{4E2D}'))      // Some(2)  中
    println(charWidth(r'\u{0}'))         // None（控制字符）

    // 字符串宽度
    println(strWidth("hello"))           // 5
    println(strWidth("你好"))            // 4
    println(strWidth("\u{1F600}"))       // 2（emoji）

    // CJK 上下文（模糊宽度字符视为宽）
    println(charWidthCJK(r'\u{2010}'))   // Some(2)
    println(strWidthCJK("hello"))        // 5
}
```

## API

| 函数 | 签名 | 说明 |
|------|------|------|
| `charWidth` | `(Rune): Option<Int64>` | 字符显示宽度，控制字符返回 None |
| `charWidthCJK` | `(Rune): Option<Int64>` | CJK 上下文字符宽度 |
| `strWidth` | `(String): Int64` | 字符串显示宽度 |
| `strWidthCJK` | `(String): Int64` | CJK 上下文字符串宽度 |

## 许可证

MIT
