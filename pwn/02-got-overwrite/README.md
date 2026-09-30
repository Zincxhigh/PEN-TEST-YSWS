# GOT Overwrite — Medium

The program contains a format-string vulnerability (`printf(buf)`) and a
`win()` function that is never called. There is no buffer overflow, and the
stack canary is intact — but the Global Offset Table is writable.

- `chall.c` — source (compiled with `gcc -O0 -fstack-protector-strong
  -pie -fPIE -z relro -z lazy -z noexecstack`)
- `chall` — the binary (64-bit, PIE on, NX on, canary on, **Partial RELRO**)
- `flag.txt` — the flag (read by the binary at runtime)
- `solve.py` — reference exploit (pure Python, no dependencies)

Ideas:
- The banner leaks a PIE address — derive the base, `win()`, and GOT.
- Only 63 bytes of format input: use two-byte (`%hn`) writes.
- `exit@GOT` is never resolved before your input, so it still points into
  the PLT and shares its high bytes with `win()` — one write is enough.
- `main` ends with an explicit `exit()` call, which then lands in `win()`.
- Beware: the input may contain `0x0a` bytes — `read()` keeps them.
