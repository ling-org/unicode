package unicode_case

public func eq(left: String, right: String): Bool {
    let leftRunes = left.toRuneArray()
    let rightRunes = right.toRuneArray()

    var li: Int64 = 0
    var ri: Int64 = 0
    var leftBuf = Array<Rune>()
    var rightBuf = Array<Rune>()
    var lbi: Int64 = 0
    var rbi: Int64 = 0

    while (true) {
        // Refill left buffer if needed
        if (lbi >= leftBuf.size) {
            if (li >= leftRunes.size) {
                // Left exhausted, check if right is also exhausted
                if (rbi >= rightBuf.size && ri >= rightRunes.size) {
                    return true
                }
                return false
            }
            leftBuf = lookup(leftRunes[li]).toArray()
            li += 1
            lbi = 0
        }

        // Refill right buffer if needed
        if (rbi >= rightBuf.size) {
            if (ri >= rightRunes.size) {
                return false
            }
            rightBuf = lookup(rightRunes[ri]).toArray()
            ri += 1
            rbi = 0
        }

        // Compare current folded runes
        if (leftBuf[lbi] != rightBuf[rbi]) {
            return false
        }
        lbi += 1
        rbi += 1
    }
    return false // unreachable
}

public func toFoldedCase(s: String): String {
    let runes = s.toRuneArray()
    let sb = StringBuilder()
    var i: Int64 = 0
    while (i < runes.size) {
        let folded = lookup(runes[i]).toArray()
        var j: Int64 = 0
        while (j < folded.size) {
            sb.append(folded[j])
            j += 1
        }
        i += 1
    }
    sb.toString()
}

public func foldedRunes(r: Rune): Array<Rune> {
    lookup(r).toArray()
}
