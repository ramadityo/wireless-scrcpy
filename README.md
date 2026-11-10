# SCRCPY Wireless - Via QR Code

Script Python untuk menyambungkan HP Android ke PC lewat Wireless debugging dengan scan QR, lalu membuka scrcpy. Kamu tidak perlu kabel USB, dan tidak perlu mengetik IP, port, atau kode pairing.

Cara pairing-nya sama dengan fitur "Pair device with QR code" di Android Studio. Bedanya, script ini berjalan di terminal dan langsung meneruskan koneksinya ke scrcpy.

## Kebutuhan

Di PC:

- Python 3.10 atau lebih baru
- adb (Android platform-tools)
- scrcpy, opsional. Tanpa scrcpy, script berhenti setelah `adb connect`.

Di HP:

- Android 11 atau lebih baru
- Developer options aktif (Settings > About phone > ketuk Build number 7 kali)
- Wireless debugging dinyalakan di Developer options

PC dan HP harus terhubung ke Wi-Fi yang sama. HP tidak perlu memasang aplikasi apa pun.

## Instalasi

Pasang adb dan scrcpy sesuai OS:

```bash
# Windows (rilis scrcpy untuk Windows sudah membawa adb)
winget install --exact Genymobile.scrcpy

# macOS
brew install scrcpy
brew install --cask android-platform-tools

# Ubuntu/Debian
sudo apt install adb scrcpy
```

Versi scrcpy di repo apt sering tertinggal. Kalau ada fitur yang tidak jalan, ambil rilis terbaru dari [GitHub Genymobile/scrcpy](https://github.com/Genymobile/scrcpy/releases).

Lalu pasang dua library Python:

```bash
pip install zeroconf qrcode
```

Cek bahwa `adb version` dan `scrcpy --version` bisa dijalankan dari terminal. Kalau muncul "command not found", folder instalasinya belum masuk PATH.

## Pemakaian

```bash
python scrcpy-qr.py
```

QR akan muncul di terminal. Di HP, buka Developer options > Wireless debugging > Pair device with QR code, lalu scan. Kalau semua berjalan lancar, jendela scrcpy terbuka beberapa detik kemudian.

| Flag | Fungsi |
| --- | --- |
| `--timeout DETIK` | Lama menunggu HP scan QR. Default 120. |
| `--invert` | Membalik warna QR. Pakai ini kalau QR tidak terbaca di terminal berlatar terang. |
| `--no-scrcpy` | Berhenti setelah `adb connect`, tanpa membuka scrcpy. |

## Cara kerja

1. Script membuat nama service dan password acak, lalu menampilkannya sebagai QR dengan format `WIFI:T:ADB;S:<nama>;P:<password>;;`.
2. Setelah scan, HP mengumumkan service mDNS `_adb-tls-pairing._tcp` dengan nama dari QR. Script menunggu service itu, mengambil IP dan port-nya, lalu menjalankan `adb pair`.
3. Port untuk koneksi berbeda dengan port pairing. Script mencarinya di service `_adb-tls-connect._tcp` dengan IP yang sama, lalu menjalankan `adb connect`.
4. Script membuka `scrcpy -s IP:PORT`.

## Setelah koneksi diputus

Pairing dan koneksi adalah dua hal terpisah. Pairing tersimpan di HP sampai kamu menekan Forget di daftar Paired devices, atau sampai Android mencabutnya karena PC itu tidak dipakai connect selama sekitar 7 hari.

Menutup jendela scrcpy tidak memutus ADB. `adb disconnect` memutus koneksi, tapi Wireless debugging di HP tetap menyala. Selama toggle itu menyala dan HP masih di jaringan yang sama, PC yang sudah di-pair bisa connect lagi tanpa scan QR dan tanpa konfirmasi di HP.

Karena itu, matikan Wireless debugging kalau sudah selesai. Bisa dari HP, atau dari PC:

```bash
adb -s IP:PORT shell settings put global adb_wifi_enabled 0
```

Perintah ini belum diuji di semua merek HP. Coba dulu di perangkatmu.

Wireless debugging juga mati sendiri saat HP pindah Wi-Fi, dan di banyak HP ikut mati setelah restart.

## Kalau gagal

**Timeout menunggu HP, padahal QR sudah di-scan.** Biasanya mDNS terblokir. Di Windows, izinkan Python di jaringan Private saat pop-up Windows Firewall muncul. Kalau pop-up itu sudah telanjur ditolak, ubah izinnya di pengaturan firewall. Wi-Fi kantor, kampus, dan jaringan publik sering memakai AP isolation, sehingga HP dan PC tidak bisa saling melihat. Coba lewat Wi-Fi rumah atau hotspot dari HP lain.

**Pairing berhasil, tapi port connect tidak ditemukan.** Lihat IP dan port yang tertulis di layar Wireless debugging, lalu sambungkan manual:

```bash
adb connect IP:PORT
scrcpy -s IP:PORT
```

**QR tidak terbaca.** Jalankan ulang dengan `--invert`, atau perbesar jendela terminal.
