from Crypto.Util.number import bytes_to_long

p = 1000003
q = 1000033
n = p * q
e = 65537
flag = b"pentest{REDACTED}"

def chunks(b, s=4):
    return [b[i:i+s] for i in range(0, len(b), s)]

ct = [pow(bytes_to_long(c), e, n) for c in chunks(flag)]
print(f"n = {n}")
print(f"e = {e}")
print(f"ct = {ct}")
