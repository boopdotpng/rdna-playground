#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$SCRIPT_DIR"

SRC="${2:-test.hip.cc}"
OUT_DIR="${OUT_DIR:-"$SCRIPT_DIR/reference"}"
mkdir -p "$OUT_DIR"

detect_arch() {
  if command -v rocm_agent_enumerator >/dev/null 2>&1; then
    rocm_agent_enumerator 2>/dev/null | head -n 1 | tr -d '\r'
    return 0
  fi
  if command -v rocminfo >/dev/null 2>&1; then
    rocminfo 2>/dev/null | rg -o 'gfx[0-9]+' -m 1 || true
    return 0
  fi
  return 1
}

ARCH="${1:-}"
if [[ -z "${ARCH}" ]]; then
  ARCH="$(detect_arch || true)"
fi

if [[ -z "${ARCH}" ]]; then
  echo "error: could not detect GPU arch (gfx*). Pass it explicitly:" >&2
  echo "  $0 gfx1152 [path/to/test.hip.cc]" >&2
  exit 2
fi

for tool in hipcc clang-offload-bundler llvm-objdump llvm-readobj file rg; do
  command -v "$tool" >/dev/null 2>&1 || { echo "error: missing required tool: $tool" >&2; exit 2; }
done

OUT_BUNDLE="$OUT_DIR/reference.hsaco"
OUT_HSACO="$OUT_DIR/rdna_only.hsaco"
OUT_HSACO_TXT="$OUT_DIR/rdna_only.hsaco.txt"
OUT_DISASM="$OUT_DIR/rdna.disasm.txt"
OUT_RDNA_S="$OUT_DIR/rdna.s"

rm -f "$OUT_BUNDLE" "$OUT_HSACO" "$OUT_HSACO_TXT" "$OUT_DISASM" "$OUT_RDNA_S"

hipcc --genco --offload-arch="$ARCH" "$SRC" -o "$OUT_BUNDLE"

# `hipcc --genco` often produces a clang offload bundle; unbundle if needed.
if file -b "$OUT_BUNDLE" | rg -q 'ELF'; then
  cp "$OUT_BUNDLE" "$OUT_HSACO"
else
  clang-offload-bundler --unbundle --type=o \
    --targets="hipv4-amdgcn-amd-amdhsa--${ARCH}" \
    --input="$OUT_BUNDLE" \
    --output="$OUT_HSACO"
fi

{
  echo "# Source: $SRC"
  echo "# Arch:   $ARCH"
  echo "# File:   $OUT_HSACO"
  echo
  echo "# ---- llvm-readobj --all ----"
  llvm-readobj --all "$OUT_HSACO"
  echo
  echo "# ---- llvm-objdump -h -t -r -s ----"
  llvm-objdump -h -t -r -s "$OUT_HSACO"
} > "$OUT_HSACO_TXT"

TMP_DISASM="$OUT_DIR/.rdna.disasm.tmp"
llvm-objdump -d --arch=amdgcn --mcpu="$ARCH" "$OUT_HSACO" > "$TMP_DISASM"
sed -E 's|[[:space:]]*//.*$||; s|[[:space:]]+$||' "$TMP_DISASM" \
  | awk 'NR==1 && $0=="" { next } /^[[:space:]]*s_code_end[[:space:]]*$/ { next } { print }' \
  > "$OUT_DISASM"
rm -f "$TMP_DISASM"

# Extract just the RDNA ISA instruction lines (no addresses/encodings/comments).
awk '
  BEGIN { first_sym=1 }
  /^[0-9a-fA-F]+ <.*>:/ {
    sym=$0
    sub(/^[0-9a-fA-F]+ </, "", sym)
    sub(/>:\s*$/, "", sym)
    if (!first_sym) print ""
    first_sym=0
    print "// " sym
    next
  }
  /^[[:space:]]+[a-z][a-z0-9_.]*([[:space:]]|$)/ {
    line=$0
    sub(/^[[:space:]]+/, "", line)
    c=index(line, "//")
    if (c > 0) line=substr(line, 1, c-1)
    sub(/[[:space:]]+$/, "", line)
    if (line == "s_code_end") next
    if (length(line)) print line
  }
' "$OUT_DISASM" > "$OUT_RDNA_S"

rm -f "$OUT_BUNDLE" "$OUT_HSACO"

echo "wrote $OUT_HSACO_TXT"
echo "wrote $OUT_DISASM"
echo "wrote $OUT_RDNA_S"
