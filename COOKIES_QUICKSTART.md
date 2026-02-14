# 🚀 Quick Reference: YouTube Cookies

## ⚡ Cara Tercepat (Auto-Extract)

**Tidak perlu setup apapun!** Aplikasi otomatis mengambil cookies dari Chrome.

**Requirement:**
1. ✅ Login ke YouTube di Chrome
2. ✅ Tutup Chrome sebelum run aplikasi
3. ✅ Run aplikasi seperti biasa

**Itu saja!** 🎉

---

## 🔧 Manual Setup (Jika Auto-Extract Gagal)

### Step 1: Install Extension
- Chrome: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)

### Step 2: Export Cookies
1. Login ke YouTube
2. Klik extension → "Export"
3. Save sebagai `youtube_cookies.txt`

### Step 3: Simpan File
```
youtubeClipper/
└── backend/
    └── youtube_cookies.txt  <-- Taruh di sini
```

### Step 4: Update Kode (Opsional)
Jika ingin gunakan file manual, edit `downloader.py`:

```python
# Ganti baris ini (line ~59):
ydl_opts['cookiesfrombrowser'] = ('chrome',)

# Jadi:
ydl_opts['cookiefile'] = 'backend/youtube_cookies.txt'
```

---

## 🧪 Testing

```bash
cd backend
python test_cookies.py
```

Masukkan URL video age-restricted untuk test.

---

## 🔄 Ganti Browser Default

Edit `downloader.py` line 59:

```python
# Chrome (default)
ydl_opts['cookiesfrombrowser'] = ('chrome',)

# Edge
ydl_opts['cookiesfrombrowser'] = ('edge',)

# Firefox
ydl_opts['cookiesfrombrowser'] = ('firefox',)
```

---

## ❌ Troubleshooting

| Error | Solusi |
|-------|--------|
| "Sign in to confirm..." | Login ke YouTube di Chrome |
| "HTTP 403 Forbidden" | Update yt-dlp: `pip install -U yt-dlp` |
| Auto-extract gagal | Gunakan manual export |
| Cookies expired | Re-export dari browser |

---

## 📝 Notes

- ✅ Cookies auto-refresh oleh browser
- ✅ File cookies sudah di `.gitignore`
- ✅ Tidak perlu update frontend
- ✅ Works out of the box!

**Full guide**: `YOUTUBE_COOKIES_GUIDE.md`
