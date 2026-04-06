# unicode

[仓颉](https://cangjie-lang.cn/) Unicode 工具库，基于 Unicode 17.0.0。

## 包

| 包 | 说明 |
|---|------|
| **unicode-case** | Unicode 大小写折叠，支持完整大小写无关比较 |
| **unicode-width** | 按照 [UAX #11](https://www.unicode.org/reports/tr11/) 计算字符和字符串的显示宽度 |

## 使用

在 `cjpm.toml` 中添加需要的包作为依赖：

```toml
[dependencies]
  unicode_case = { git = "https://github.com/ling-org/unicode.git", path = "unicode-case" }
  unicode_width = { git = "https://github.com/ling-org/unicode.git", path = "unicode-width" }
```

### unicode-case

```cangjie
import unicode_case.*

main() {
    println(eq("Maße", "MASSE"))        // true
    println(toFoldedCase("Maße"))        // masse
    println(eq("ﬂour", "flour"))         // true
}
```

### unicode-width

```cangjie
import unicode_width.*

main() {
    println(charWidth(r'a'))             // Some(1)
    println(charWidth(r'\u{4E2D}'))      // Some(2)
    println(strWidth("hello"))           // 5
    println(strWidth("你好"))            // 4
    println(strWidth("\u{1F600}"))       // 2
}
```

## 重新生成查找表

查找表由 Python 脚本从 Unicode 官方数据生成：

```bash
cd scripts
uv run generate.py
```

## 构建

```bash
cjpm build
```

## 测试

```bash
cjpm test
```

## 许可证

MIT
