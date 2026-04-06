package unicode_case

public enum Fold {
    | Zero
    | One(Rune)
    | Two(Rune, Rune)
    | Three(Rune, Rune, Rune)

    public func toArray(): Array<Rune> {
        match (this) {
            case Zero => Array<Rune>()
            case One(a) => [a]
            case Two(a, b) => [a, b]
            case Three(a, b, c) => [a, b, c]
        }
    }

    public func size(): Int64 {
        match (this) {
            case Zero => 0
            case One(_) => 1
            case Two(_, _) => 2
            case Three(_, _, _) => 3
        }
    }
}
