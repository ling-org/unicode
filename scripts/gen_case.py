"""Case folding table generator.

Reads CaseFolding.txt and emits ``unicode-case/src/map.cj``.
"""

from typing import IO

from common import UNICODE_VERSION, fetch_open, emit_cangjie_file


# ---------------------------------------------------------------------------
# Run – a contiguous mapping range
# ---------------------------------------------------------------------------

class Run:
    def __init__(self, map_from, map_tos):
        self.start = map_from
        self.end = map_from
        self.map_tos = map_tos
        self.every_other = None

    def limit_to_range(self, min_relevant, max_relevant):
        if self.end < min_relevant:
            return None
        if self.start > max_relevant:
            return None
        if self.start >= min_relevant and self.end <= max_relevant:
            return self

        ret = Run(self.start, [m for m in self.map_tos])
        ret.end = self.end
        ret.every_other = self.every_other
        if ret.start < min_relevant:
            diff = min_relevant - ret.start
            if ret.every_other is True and diff % 2 == 1:
                diff += 1
            ret.start += diff
            ret.map_tos[0] += diff
        if ret.end > max_relevant:
            ret.end = max_relevant
        return ret

    def expand_into(self, map_from, map_tos):
        if len(self.map_tos) != 1 or len(map_tos) != 1:
            return False

        if (
            self.every_other is not True
            and self.end + 1 == map_from
            and map_tos[0] == self.map_tos[0] + (map_from - self.start)
        ):
            self.end += 1
            self.every_other = False
            return True
        if (
            self.every_other is not False
            and self.end + 2 == map_from
            and map_tos[0] == self.map_tos[0] + (map_from - self.start)
        ):
            self.end += 2
            self.every_other = True
            return True
        return False

    # -----------------------------------------------------------------
    # Cangjie code emitter
    # -----------------------------------------------------------------

    def dump_cangjie(self, out: IO[str], *, match_on_low_byte: bool = False, is_high: bool = False):
        """Emit Cangjie match arms."""

        def fmt(x):
            if match_on_low_byte:
                return "0x%02Xu8" % (x & 0xFF)
            if is_high:
                return "0x%04Xu32" % x
            return "0x%04Xu16" % x

        indent = "                    " if match_on_low_byte else "                "

        # -- single value --
        if self.start == self.end:
            if len(self.map_tos) == 1:
                suffix = "u32" if is_high else "u16"
                out.write(f"{indent}case {fmt(self.start)} => 0x{self.map_tos[0]:04X}{suffix}\n")
            else:
                chars = ", ".join(f"Rune(0x{c:04X}u32)" for c in self.map_tos)
                variant = {1: "One", 2: "Two", 3: "Three"}[len(self.map_tos)]
                out.write(f"{indent}case {fmt(self.start)} => return Fold.{variant}({chars})\n")
            return

        # helper: remove trivially-true comparisons
        def clean(line):
            line = line.replace("(0x00u8 <= x && ", "(")
            if match_on_low_byte:
                line = line.replace(" && x <= 0xFFu8)", ")")
            return line

        T = "UInt32" if is_high else "UInt16"
        s = "u32" if is_high else "u16"

        # -- contiguous range with constant offset --
        if self.every_other is not True:
            offset = self.map_tos[0] - self.start
            op = "+" if offset >= 0 else "-"
            off_abs = abs(offset)
            out.write(clean(
                f"{indent}case x where ({fmt(self.start)} <= x && x <= {fmt(self.end)}) => "
                f"{T}(x) {op} 0x{off_abs:04X}{s}\n"
            ))
        # -- from | 1  (even start) --
        elif self.map_tos[0] - self.start == 1 and self.start % 2 == 0:
            out.write(clean(
                f"{indent}case x where ({fmt(self.start)} <= x && x <= {fmt(self.end)}) => "
                f"{T}(x) | 0x01{s}\n"
            ))
        # -- (from + 1) & ~1  (odd start) --
        elif self.map_tos[0] - self.start == 1 and self.start % 2 == 1:
            mask = "0xFFFFFFFE" if is_high else "0xFFFE"
            out.write(clean(
                f"{indent}case x where ({fmt(self.start)} <= x && x <= {fmt(self.end)}) => "
                f"({T}(x) + 1{s}) & {mask}{s}\n"
            ))
        # -- every-other with general offset --
        else:
            v_check = self.start % 2
            offset = self.map_tos[0] - self.start
            op = "+" if offset >= 0 else "-"
            off_abs = abs(offset)
            out.write(
                f"{indent}case x where ({fmt(self.start)} <= x && x <= {fmt(self.end)}) =>\n"
                f"{indent}    if (({T}(x) & 1{s}) == {v_check}{s}) {{\n"
                f"{indent}        {T}(x) {op} 0x{off_abs:04X}{s}\n"
                f"{indent}    }} else {{\n"
                f"{indent}        {T}(x)\n"
                f"{indent}    }}\n"
            )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate(output_dir: str):
    """Download CaseFolding.txt and generate map.cj."""
    print("=== Generating case table ===")

    with fetch_open("CaseFolding.txt") as txt:
        run_in_progress = None
        runs: list[Run] = []

        for line in txt:
            if not line or line[0] == "#":
                continue
            parts = line.split("; ")
            if len(parts) > 2 and parts[1] in "CF":
                map_from = int(parts[0], 16)
                map_tos = [int(c, 16) for c in parts[2].split(" ")]

                if run_in_progress and run_in_progress.expand_into(map_from, map_tos):
                    pass
                else:
                    if run_in_progress:
                        runs.append(run_in_progress)
                    run_in_progress = Run(map_from, map_tos)
        if run_in_progress:
            runs.append(run_in_progress)

    high_runs = [r for r in runs if r.end > 0x2CFF]

    small_run_chunks: list[list[Run]] = []
    for high_byte in range(0, 0x2D):
        lo = high_byte << 8
        hi = lo + 255
        chunk = [sub for r in runs if (sub := r.limit_to_range(lo, hi)) is not None]
        small_run_chunks.append(chunk)

    output_path = f"{output_dir}/unicode-case/src/map.cj"

    def write_case(out: IO[str]):
        out.write("package unicode_case\n\n")
        out.write("func lookup(orig: Rune): Fold {\n")
        out.write("    let from32 = UInt32(orig)\n")
        out.write("    if (from32 <= 0x2CFFu32) {\n")
        out.write("        let from16 = UInt16(from32)\n")
        out.write("        let highByte = UInt8(from16 >> 8)\n")
        out.write("        let lowByte = UInt8(from16 & 0xFFu16)\n")
        out.write("        let singleChar: UInt16 = match (highByte) {\n")

        for hb, chunk in enumerate(small_run_chunks):
            if not chunk:
                out.write("            case 0x%02Xu8 => from16\n" % hb)
            else:
                out.write("            case 0x%02Xu8 => match (lowByte) {\n" % hb)
                for r in chunk:
                    r.dump_cangjie(out, match_on_low_byte=True)
                out.write("                    case _ => from16\n")
                out.write("                }\n")

        out.write("            case _ => from16\n")
        out.write("        }\n")
        out.write("        Fold.One(Rune(UInt32(singleChar)))\n")
        out.write("    } else {\n")
        out.write("        let singleChar32: UInt32 = match (from32) {\n")
        for r in high_runs:
            r.dump_cangjie(out, is_high=True)
        out.write("            case _ => from32\n")
        out.write("        }\n")
        out.write("        Fold.One(Rune(singleChar32))\n")
        out.write("    }\n")
        out.write("}\n")

    emit_cangjie_file(output_path, write_case)
    print(f'  Wrote to "{output_path}"')
