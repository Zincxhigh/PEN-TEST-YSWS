import hashlib, random

p = 1000003  
g = 5

random.seed(0xC0FFEE)
a = random.randint(2, p - 2) 
b = random.randint(2, p - 2)
A = pow(g, a, p)
B = pow(g, b, p)
s = pow(B, a, p)  
assert s == pow(A, b, p)

key = hashlib.sha256(str(s).encode()).digest()
flag = b"pentest{REDACTED}"
ct = bytes(x ^ y for x, y in zip(flag, key * (len(flag) // len(key) + 1)))

print(f"p = {p}")
print(f"g = {g}")
print(f"A = {A}")
print(f"B = {B}")
print(f"ct = {ct.hex()}")
