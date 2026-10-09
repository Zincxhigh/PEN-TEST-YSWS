# ret2win — Easy

A classic stack buffer overflow. There is a function that prints the flag,
but the program never calls it. Overflow the buffer and redirect execution
to it.

- `chall.c` — source (compiled with `gcc -O0 -fno-stack-protector -no-pie
  -z noexecstack -z relro -z now`)
- `chall` — the binary (64-bit, **no PIE**, NX on, no canary)
- `flag.txt` — the flag (read by the binary at runtime)
- `solve.py` — reference exploit (pure Python, no dependencies)

Find the address of `win` (e.g. with `nm`) and overwrite the saved return
address. Offset: 72 bytes (64-byte buffer + saved RBP).
