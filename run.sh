#!/bin/bash

KERNEL_IMAGE="./linux-6.6.136/arch/x86/boot/bzImage"
ROOTFS="./rootfs.ext4"
KERNEL_APPEND="console=ttyS0 nokaslr root=/dev/vda rw init=/init"
SHARED_DIR="./shared"

qemu-system-x86_64 \
  -kernel "$KERNEL_IMAGE" \
  -drive file="$ROOTFS",format=raw,if=virtio \
  -append "$KERNEL_APPEND" \
  -nographic \
  -s \
  -m 1024 \
  -enable-kvm \
  -fsdev local,id=shared,path="$SHARED_DIR",security_model=none \
  -device virtio-9p-pci,fsdev=shared,mount_tag=shared
