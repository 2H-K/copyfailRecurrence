#!/bin/bash

set -e

# ======================== 配置变量 ========================
WORK_DIR="./copyfail-lab"
ROOTFS_DIR="$WORK_DIR/ubuntu-rootfs"
IMAGE_FILE="$WORK_DIR/rootfs.ext4"
IMAGE_SIZE_MB=1536

DEBOOTSTRAP_SUITE="noble"
DEBOOTSTRAP_MIRROR="http://archive.ubuntu.com/ubuntu"

PACKAGES="\
python3,strace,bpftrace,\
gcc,libc6-dev,make,curl,\
keyutils,\
iproute2,\
net-tools,\
openssh-server,\
vim,\
sudo,\
util-linux,\
procps,\
login"

# ======================== 检查权限 ========================
if [ "$EUID" -ne 0 ]; then
    echo "请使用 root 权限运行（sudo）"
    exit 1
fi

# ======================== 创建工作目录 ========================
mkdir -p "$WORK_DIR"

# ======================== 删除旧镜像 ========================
if [ -f "$IMAGE_FILE" ]; then
    echo "[*] 删除旧镜像文件，准备重构..."
    rm -f "$IMAGE_FILE"
fi

# ======================== debootstrap ========================
if [ -d "$ROOTFS_DIR/usr" ]; then
    echo "[1/6] 检测到已存在 rootfs，跳过 debootstrap"
else
    echo "[1/6] 开始 debootstrap..."

    mkdir -p "$ROOTFS_DIR"

    debootstrap \
        --variant=minbase \
        --include="$PACKAGES" \
        "$DEBOOTSTRAP_SUITE" \
        "$ROOTFS_DIR" \
        "$DEBOOTSTRAP_MIRROR"
fi

# ======================== chroot 配置 ========================
echo "[2/6] 配置 rootfs..."

chroot "$ROOTFS_DIR" /bin/bash -c '
echo "copyfail" > /etc/hostname

cat > /etc/hosts << EOF
127.0.0.1 localhost
127.0.1.1 copyfail
EOF

echo "root:root" | chpasswd

if ! id "asdf" >/dev/null 2>&1; then
    useradd -m -s /bin/bash asdf
fi

echo "asdf:test" | chpasswd

chmod u+s /usr/bin/su

# ssh 允许密码登录
sed -i "s/^#PermitRootLogin.*/PermitRootLogin yes/" /etc/ssh/sshd_config
sed -i "s/^#PasswordAuthentication.*/PasswordAuthentication yes/" /etc/ssh/sshd_config

mkdir -p /run/sshd

apt clean
rm -rf /var/lib/apt/lists/*
'

# ======================== init ========================
echo "[3/6] 更新 /init 脚本..."

cat > "$ROOTFS_DIR/init" << 'INITEOF'
#!/bin/sh

mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mount -t debugfs debugfs /sys/kernel/debug

mkdir -p /dev/pts
mount -t devpts devpts /dev/pts

mkdir -p /run
mkdir -p /run/sshd
mkdir -p /mnt/shared

# 共享目录
mount -t 9p -o trans=virtio shared /mnt/shared

# 网络初始化
ip link set lo up
ip link set eth0 up

# QEMU user networking 默认静态 IP
ip addr add 10.0.2.15/24 dev eth0
ip route add default via 10.0.2.2

# 启动 ssh
/usr/sbin/sshd

echo ""
echo "=============================================="
echo "  Copy Fail Lab Ready (auto root login)"
echo "=============================================="
echo "  sshd running, root shell on console"
echo "=============================================="
echo ""

# 自动以 root 登录，无密码提示
exec /bin/bash --login
INITEOF

chmod +x "$ROOTFS_DIR/init"

mkdir -p "$ROOTFS_DIR/mnt/shared"

# ======================== 创建 ext4 镜像 ========================
echo "[4/6] 创建 ext4 镜像 ($IMAGE_SIZE_MB MB)..."

dd if=/dev/zero of="$IMAGE_FILE" \
    bs=1M \
    count="$IMAGE_SIZE_MB" \
    status=noxfer

mkfs.ext4 -F -L copyfail-root "$IMAGE_FILE"

# ======================== 挂载并同步 ========================
echo "[5/6] 同步 rootfs (排除虚拟文件系统)..."

MOUNT_POINT="/mnt/rootfs_$$"
mkdir -p "$MOUNT_POINT"
mount "$IMAGE_FILE" "$MOUNT_POINT"

# 只使用 rsync，不要再用 cp -a
rsync -aHAX \
  --exclude='/proc' \
  --exclude='/sys' \
  --exclude='/dev' \
  --exclude='/run' \
  --exclude='/tmp' \
  "$ROOTFS_DIR"/ "$MOUNT_POINT"/

# 创建必要的空目录（因为排除了，但挂载时需要）
mkdir -p "$MOUNT_POINT"/{proc,sys,dev,run,tmp}

# 写入 fstab
cat > "$MOUNT_POINT/etc/fstab" << EOF
/dev/vda / ext4 rw,noatime 0 1
proc /proc proc defaults 0 0
sysfs /sys sysfs defaults 0 0
devtmpfs /dev devtmpfs defaults 0 0
devpts /dev/pts devpts defaults 0 0
tmpfs /tmp tmpfs defaults 0 0
EOF

# ======================== 清理 ========================
echo "[6/6] 清理..."

umount "$MOUNT_POINT"

rmdir "$MOUNT_POINT"

REAL_USER=$(logname 2>/dev/null || echo $SUDO_USER)

chown "$REAL_USER":"$REAL_USER" "$IMAGE_FILE"

echo ""
echo "[✓] Rootfs 构建完成:"
echo "    $IMAGE_FILE"