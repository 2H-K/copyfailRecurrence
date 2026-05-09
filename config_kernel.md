# 一、推荐基础流程

进入：

```bash id="cfg7"
make menuconfig
```

然后按下面路径配置。

---

# 二、QEMU / KVM 基础环境

## 路径

```text id="cfg8"
General setup
```

开启：

```text id="cfg9"
[*] Initial RAM filesystem and RAM disk (initramfs/initrd) support
```

---

## 路径

```text id="cfg10"
Device Drivers
    └── Generic Driver Options
```

开启：

```text id="cfg11"
[*] Maintain a devtmpfs filesystem to mount at /dev
[*] Automount devtmpfs at /dev
```

---

## 路径

```text id="cfg12"
File systems
```

开启：

```text id="cfg13"
[*] The Extended 4 (ext4) filesystem
```

---

## 路径

```text id="cfg14"
Device Drivers
    └── Virtio drivers
```

开启：

```text id="cfg15"
[*] PCI driver for virtio devices
[*] Virtio block driver
[*] Virtio balloon driver
[*] Virtio input driver
```

建议：

```text id="cfg16"
[*] Virtio network driver
```

---

## 路径

```text id="cfg17"
File systems
    └── Network File Systems
```

开启：

```text id="cfg18"
[*] Plan 9 Resource Sharing Support (9P2000)
[*]   9P Virtio Transport
```

---

# 三、调试支持（强烈建议）

## 路径

```text id="cfg19"
Kernel hacking
```

开启：

```text id="cfg20"
[*] Kernel debugging
```

---

## 路径

```text id="cfg21"
Kernel hacking
    └── Compile-time checks and compiler options
```

配置：

```text id="cfg22"
Debug information  ---> Generate DWARF Version 4 debuginfo

[ ] Reduce debugging information
[ ] Produce split debuginfo in .dwo files

[*] Generate BTF type information
[*] Generate BTF type information for kernel modules

[*] Provide GDB scripts for kernel debugging
```

这是最关键部分。 ([Cateee][1])

---

# 四、ftrace / bpftrace / eBPF

## 路径

```text id="cfg23"
Kernel hacking
    └── Tracers
```

开启：

```text id="cfg24"
[*] Kernel Function Tracer
[*] Kernel Function Graph Tracer
[*] tracepoint
[*] Enable dynamic ftrace
[*] Enable syscall tracing support
```

---

## 路径

```text id="cfg25"
General architecture-dependent options
```

开启：

```text id="cfg26"
[*] Kprobes
[*] Uprobes
```

---

## 路径

```text id="cfg27"
Networking support
    └── Networking options
```

开启：

```text id="cfg28"
[*] TCP/IP networking
```

---

## 路径

```text id="cfg29"
General setup
```

开启：

```text id="cfg30"
[*] BPF subsystem support
[*] Enable bpf() system call
[*] Enable BPF Just In Time compiler
[*] Compile-in debug information for BPF verifier
```

---

# 五、DirtyFrag 复现配置

## 路径

```text id="cfg31"
Networking support
    └── Networking options
```

开启：

```text id="cfg32"
[*] Transformation user configuration interface
[*] IP: AH transformation
[*] IP: ESP transformation
[*] IPv6: ESP transformation
```

---

## 路径

```text id="cfg33"
Networking support
    └── RxRPC session sockets
```

开启：

```text id="cfg34"
[*] RxRPC session sockets
[*] RxKAD security module
```

---

## 路径

```text id="cfg35"
Security options
    └── Keys
```

开启：

```text id="cfg36"
[*] Enable access key retention support
[*] Large payload keys
[*] Persistent keyrings
```

---

## 路径

```text id="cfg37"
General setup
    └── Namespaces support
```

全部开启：

```text id="cfg38"
[*] User namespace
[*] PID Namespaces
[*] Network namespace
[*] IPC namespace
[*] UTS namespace
[*] Mount namespace
```

---

# 六、CopyFail 复现配置

## 路径

```text id="cfg39"
Cryptographic API
```

开启：

```text id="cfg40"
[*] Userspace interface for hash algorithms
[*] Userspace interface for symmetric key cipher algorithms
[*] Userspace interface for AEAD cipher algorithms

[*] Authenticated Encryption with Associated Data
[*] HMAC support
[*] CBC support

[*] AES cipher algorithms
[*] SHA224 and SHA256 digest algorithm
```

---


# 七、最终验证

退出保存后：

```bash id="cfg49"
grep -E "BTF|DEBUG_INFO|KPROBE|UPROBE|FTRACE" .config
```

应看到：

```text id="cfg50"
CONFIG_DEBUG_INFO=y
CONFIG_DEBUG_INFO_DWARF4=y
CONFIG_DEBUG_INFO_BTF=y

# CONFIG_DEBUG_INFO_SPLIT is not set
# CONFIG_DEBUG_INFO_REDUCED is not set
```

---

# 九、编译完成后验证

启动 QEMU 后：

```bash id="cfg51"
ls /sys/kernel/btf/vmlinux
```

应存在。

然后：

```bash id="cfg52"
bpftrace -lv 'kprobe:vfs_read'
```

如果能看到：

```text id="cfg53"
struct file
struct inode
```

说明：

```text id="cfg54"
BTF 完全生效
```

了。

[1]: https://cateee.net/lkddb/web-lkddb/DEBUG_INFO_BTF.html?utm_source=chatgpt.com "Linux Kernel Driver DataBase: CONFIG_DEBUG_INFO_BTF: Generate BTF type information"
