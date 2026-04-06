# unicode-case

Unicode 大小写折叠，支持完整大小写无关比较。基于 Unicode 17.0.0 CaseFolding 数据。

## 使用

```toml
[dependencies]
  unicode_case = { version = "0.1.0" }
```

```cangjie
import unicode_case.*

main() {
    // 大小写无关比较
    println(eq("Foo Bar", "foo bar"))    // true
    println(eq("Maße", "MASSE"))         // true（ß 折叠为 ss）
    println(eq("ﬂour", "flour"))         // true（ﬂ 连字折叠为 fl）

    // 获取折叠后的字符串
    println(toFoldedCase("Maße"))        // masse

    // 单字符折叠
    println(foldedRunes(r'A'))           // [a]
    println(foldedRunes(r'\u{00DF}'))    // [s, s]
}
```

## API

| 函数 | 签名 | 说明 |
|------|------|------|
| `eq` | `(String, String): Bool` | 大小写无关相等比较 |
| `toFoldedCase` | `(String): String` | 返回 case-folded 字符串 |
| `foldedRunes` | `(Rune): Array<Rune>` | 返回单个 Rune 折叠后的结果 |

## 许可证

MIT
