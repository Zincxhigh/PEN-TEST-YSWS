# ret2libc — Medium/Hard

Full protections, no `win()` function, no shellcode allowed. Chain a
format-string info leak with a stack overflow to call `system("/bin/sh")`
from libc.

- `chall.c` — source (compiled with `gcc -O0 -fstack-protector-strong
  -pie -fPIE -z relro -z now -z noexecstack`)
- `chall` — the binary (64-bit, PIE on, NX on, canary on, **Full RELRO**)
- `flag.txt` — the flag (read it from the shell you spawn)
- `solve.py` — reference exploit (pure Python, no dependencies)

Ideas:
- Stage 1 (`printf(buf)`) leaks the stack canary (`%25$p`) and the program
  helpfully prints `puts@libc` — that gives you the libc base.
- Stage 2 overflows the buffer: keep the canary intact and build a ROP
  chain from **libc** gadgets only: `pop rdi; ret`, `"/bin/sh"`, `ret`
  (stack alignment!), `system`.
- Resolve libc offsets/gadgets from the local libc at runtime (`ldd`,
  `readelf`), so the exploit survives libc updates.
