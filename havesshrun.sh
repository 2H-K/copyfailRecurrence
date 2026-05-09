#!/bin/bash

KERNEL_IMAGE="./linux-6.6.136/arch/x86/boot/bzImage"
ROOTFS="./rootfs.ext4"
SHARED_DIR="./shared"

qemu-system-x86_64 \
  -kernel "$KERNEL_IMAGE" \
  -drive file="$ROOTFS",format=raw,if=virtio \
  -append "console=ttyS0 root=/dev/vda rw nokaslr init=/init" \
  -nographic \
  -m 2048 \
  -smp 2 \
  -enable-kvm \
  -cpu host \
  -s \
  \
  -netdev user,id=net0,hostfwd=tcp::2222-:22 \
  -device virtio-net-pci,netdev=net0 \
  \
  -fsdev local,id=shared,path="$SHARED_DIR",security_model=none \
  -device virtio-9p-pci,fsdev=shared,mount_tag=shared