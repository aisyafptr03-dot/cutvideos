#  Potong Video per Detik

Web app sederhana untuk memotong video otomatis per N detik memakai **Python + Flask + FFmpeg**.
Upload video lewat browser, tentukan tiap berapa detik, pilih folder penyimpanan, hasil potongan tersimpan otomatis di laptop dan bisa di-download / ZIP.

---

## 1. Syarat (Prasyarat)

1. **Python 3.10+** (disarankan 3.11 / 3.12)
   - Cek: `python --version`
   - Download: https://www.python.org/downloads/
   - Saat install di Windows **centang `Add python.exe to PATH`**.

2. **FFmpeg + FFprobe** (wajib, untuk motong video)
   - Codingan ini memanggil perintah `ffmpeg` dan `ffprobe` lewat terminal.
   - Cek sudah terinstall atau belum:
     ```powershell
     ffmpeg -version
     ffprobe -version
     ```
   - Kalau belum ada, install salah satu cara ini:

     **Cara A: via winget (paling mudah, Windows 10/11)**
     ```powershell
     winget install Gyan.FFmpeg
     ```
     Tutup dan buka ulang PowerShell, lalu cek lagi `ffmpeg -version`.

     **Cara B: manual**
     1. Download dari https://www.gyan.dev/ffmpeg/builds/ (pilih `ffmpeg-release-essentials.zip`)
     2. Extract ke misal `C:\ffmpeg`
     3. Tambahkan `C:\ffmpeg\bin` ke PATH (Edit environment variables)
     4. Restart PowerShell, cek `ffmpeg -version`.

3. **Browser** (Chrome / Edge / Firefox)

---

## 2. Struktur Folder Proyek

```
cutvideos/
├── app.py              # Program utama (backend Flask + frontend HTML)
├── requirements.txt    # Daftar library Python (Flask)
├── README.md           # File ini
├── uploads/            # Folder sementara untuk upload (otomatis dibuat)
└── hasil_potongan/     # Folder default hasil potongan (otomatis dibuat)
```

---

## 3. Cara Menjalankan

### Langkah 1: Buka folder proyek

```powershell
cd "D:\AISYAH PUTRI (S2)\TESIS\cutvideos"
```

### Langkah 2: (Disarankan) Buat virtual environment

```powershell
python -m venv venv
.\venv\Scripts\activate
```

> Kalau tidak mau pakai venv, langkah ini boleh dilewati.

### Langkah 3: Install library

```powershell
pip install -r requirements.txt
```

Isi `requirements.txt` saat ini:

```
Flask>=3.0
```

### Langkah 4: Jalankan aplikasi

```powershell
python app.py
```

Kalau berhasil akan muncul:

```
Upload dir : D:\AISYAH PUTRI (S2)\TESIS\cutvideos\uploads
Hasil      : D:\AISYAH PUTRI (S2)\TESIS\cutvideos\hasil_potongan
Buka http://127.0.0.1:5000
```

### Langkah 5: Buka di browser

Buka:

```
http://127.0.0.1:5000
```

> Untuk berhenti: tekan `CTRL + C` di PowerShell.

---

## 4. Cara Menggunakan di Web

1. **Pilih video (bisa lebih dari 1)**
   - Format didukung: `.mp4, .mkv, .avi, .mov, .webm, .m4v, .mpg, .mpeg, .3gp`
   - Maksimal total upload 4 GB.

2. **Potong tiap berapa detik?**
   - Contoh: isi `10` = video dipotong tiap 10 detik.
   - Batas: 1 – 3600 detik. Default: `10`.

3. **Mode potong:**
   - `Akurat pas detik (re-encode, disarankan)`: tiap potongan PAS durasinya (misal pas 10.00 dtk). Lebih lambat karena encode ulang.
   - `Cepat (copy, instan)`: sangat cepat tanpa encode ulang, tapi durasi bisa meleset mengikuti keyframe (misal jadi 16 dtk + 8 dtk).

4. **Simpan di mana?**
   - Klik tombol **📂 Pilih Folder...** untuk jelajahi Drive D:, E:, Desktop, dll. seperti file explorer.
   - Atau ketik manual, contoh: `D:\Hasil Potongan`
   - Tombol cepat tersedia: `📁 Default Proyek`, `🖥️ Desktop`, `📄 Documents`.
   - Isi **Nama sub-folder hasil**, contoh: `potongan_10detik`
   - Hasil akhir tersimpan di: `<Lokasi>/<NamaFolder>_<waktu>`, contoh:
     ```
     D:\Hasil Potongan\potongan_10detik_20250927_101523_a1b2c3\
     ```

5. Klik **Potong Sekarang**, tunggu sampai status `✅ Selesai!`.
   - Bisa download per file (`⬇️ namafile.mp4`)
   - Atau download semua sekaligus via **⬇️ Download Semua (ZIP)**.

---

## 5. Contoh Hasil

Misal upload `ujian.mp4` durasi 35 detik, potong tiap 10 detik, mode Akurat:

```
potongan_10detik_20250927_101523_a1b2c3/
├── ujian_10dtk_000.mp4  (0–10 dtk)
├── ujian_10dtk_001.mp4  (10–20 dtk)
├── ujian_10dtk_002.mp4  (20–30 dtk)
└── ujian_10dtk_003.mp4  (30–35 dtk)
```

---

## 6. Troubleshooting (Error Umum)

| Error / Gejala | Penyebab & Solusi |
|---|---|
| `'ffmpeg' is not recognized` / `FileNotFoundError: ffmpeg` | FFmpeg belum terinstall / belum masuk PATH. Install via `winget install Gyan.FFmpeg`, restart PowerShell. |
| `ModuleNotFoundError: No module named 'flask'` | Belum `pip install -r requirements.txt`. Jalankan lagi setelah venv aktif. |
| `Address already in use / port 5000 dipakai` | Port 5000 sudah dipakai app lain. Tutup app lain, atau ganti `port=5000` di baris terakhir `app.py`. |
| `Detik harus 1 - 3600` | Input detik di web di luar batas. Isi 1–3600. |
| Upload gagal / 413 | File > 4 GB (batas `MAX_CONTENT_LENGTH`). Kecilkan / split file dulu. |
| Hasil 16 dtk + 8 dtk padahal setting 10 dtk | Itu mode `Cepat (copy)` yang motong mengikuti keyframe. Pakai mode `Akurat` biar pas. |
| `Tidak punya akses ke folder ini` saat Browse | Folder sistem / butuh admin. Pilih folder lain (misal Documents / D:\Hasil). |

---

## 7. Perintah Penting (Cheat Sheet)

```powershell
# masuk folder
cd "D:\AISYAH PUTRI (S2)\TESIS\cutvideos"

# aktifkan venv (jika pakai)
.\venv\Scripts\activate

# install
pip install -r requirements.txt

# jalan
python app.py

# cek ffmpeg
ffmpeg -version
ffprobe -version
```

---

## 8. Catatan untuk Tesis

- Mode **Akurat** memakai `libx264 (preset veryfast, crf 23)` + `aac`, cocok untuk preprocessing dataset video agar durasi tiap clip seragam.
- Durasi tiap hasil otomatis dicek ulang dengan `ffprobe` dan ditampilkan di web (`(10.0 dtk)`).
- Nama folder hasil selalu unik (`nama_waktu_uuid6`) sehingga tidak menimpa eksperimen sebelumnya.
