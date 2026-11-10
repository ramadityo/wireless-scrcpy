#!/usr/bin/env python3
"""
Pairing Android "Wireless debugging" lewat QR, connect ADB, lalu buka scrcpy.

Syarat:
- Android 11+, Developer Options dan Wireless debugging aktif
- PC dan HP di jaringan Wi-Fi yang sama (mDNS tidak diblokir)
- adb (Android platform-tools) di PATH, scrcpy di PATH (opsional)

Install dependensi:
    pip install zeroconf qrcode

Pakai:
    python adb_qr_pair.py            # pairing + connect + buka scrcpy
"""

import argparse
import secrets
import shutil
import string
import subprocess
import sys
import threading

import qrcode
from zeroconf import IPVersion, ServiceBrowser, ServiceListener, Zeroconf

PAIRING_TYPE = "_adb-tls-pairing._tcp.local."
CONNECT_TYPE = "_adb-tls-connect._tcp.local."


def random_token(n: int, alphabet: str) -> str:
    return "".join(secrets.choice(alphabet) for _ in range(n))


def adb(*args: str) -> str:
    result = subprocess.run(["adb", *args], capture_output=True, text=True)
    return (result.stdout + result.stderr).strip()


def ipv4_of(info) -> str | None:
    addrs = info.parsed_addresses(IPVersion.V4Only)
    return addrs[0] if addrs else None


class Finder(ServiceListener):
    """Menunggu service mDNS pertama yang lolos fungsi `match`."""

    def __init__(self, match):
        self.match = match
        self.found = None
        self.event = threading.Event()

    def _check(self, zc: Zeroconf, type_: str, name: str) -> None:
        if self.event.is_set():
            return
        info = zc.get_service_info(type_, name, timeout=3000)
        if info and self.match(info):
            self.found = info
            self.event.set()

    def add_service(self, zc, type_, name):
        self._check(zc, type_, name)

    def update_service(self, zc, type_, name):
        self._check(zc, type_, name)

    def remove_service(self, zc, type_, name):
        pass


def wait_for_service(zc: Zeroconf, type_: str, match, timeout: float):
    finder = Finder(match)
    browser = ServiceBrowser(zc, type_, finder)
    try:
        return finder.found if finder.event.wait(timeout) else None
    finally:
        browser.cancel()


def show_qr(payload: str, invert: bool) -> None:
    qr = qrcode.QRCode(border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    qr.print_ascii(invert=invert)


def main() -> None:
    parser = argparse.ArgumentParser(description="ADB wireless pairing via QR + scrcpy")
    parser.add_argument("--timeout", type=int, default=120, help="detik menunggu HP scan QR")
    parser.add_argument("--invert", action="store_true", help="balik warna QR")
    parser.add_argument("--no-scrcpy", action="store_true", help="berhenti setelah adb connect")
    args = parser.parse_args()

    if not shutil.which("adb"):
        sys.exit("adb tidak ditemukan di PATH. Install Android platform-tools dulu.")
    adb("start-server")

    # Nama service dibuat lowercase karena nama mDNS tidak case-sensitive.
    service_name = "adbqr-" + random_token(8, string.ascii_lowercase + string.digits)
    password = random_token(12, string.ascii_letters + string.digits)
    payload = f"WIFI:T:ADB;S:{service_name};P:{password};;"

    show_qr(payload, args.invert)
    print("Di HP: Developer options > Wireless debugging > Pair device with QR code, lalu scan.")
    print(f"Menunggu HP (maks {args.timeout} detik)...\n")

    zc = Zeroconf()
    try:
        expected = f"{service_name}.{PAIRING_TYPE}".lower()
        pairing = wait_for_service(
            zc, PAIRING_TYPE, lambda i: i.name.lower() == expected, args.timeout
        )
        if not pairing:
            sys.exit(
                "Timeout. HP tidak terdeteksi. Cek apakah satu Wi-Fi dan jaringannya "
                "tidak memblokir mDNS (AP isolation)."
            )

        ip = ipv4_of(pairing)
        if not ip:
            sys.exit("HP ditemukan, tapi tidak punya alamat IPv4.")

        print(f"HP ditemukan di {ip}:{pairing.port}, pairing...")
        out = adb("pair", f"{ip}:{pairing.port}", password)
        print(out)
        if "Successfully paired" not in out:
            sys.exit("Pairing gagal.")

        # Port untuk connect berbeda dari port pairing; dicari lewat service kedua.
        print("Mencari port connect...")
        connect = wait_for_service(zc, CONNECT_TYPE, lambda i: ipv4_of(i) == ip, 30)
    finally:
        zc.close()

    if not connect:
        sys.exit(
            "Pairing berhasil, tapi port connect tidak ditemukan. Lihat IP:port di layar "
            "Wireless debugging lalu jalankan: adb connect IP:PORT"
        )

    serial = f"{ip}:{connect.port}"
    print(adb("connect", serial))
    if adb("-s", serial, "get-state") != "device":
        sys.exit(f"Gagal connect ke {serial}.")
    print(f"Terhubung: {serial}")

    if args.no_scrcpy:
        return
    if not shutil.which("scrcpy"):
        print(f"scrcpy tidak ditemukan. Jalankan manual: scrcpy -s {serial}")
        return
    subprocess.run(["scrcpy", "-s", serial])


if __name__ == "__main__":
    main()