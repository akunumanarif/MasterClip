# 🍪 YouTube Cookies Setup Guide

## Mengapa Butuh Cookies?

YouTube cookies dibutuhkan untuk:
- ✅ Video yang dibatasi usia (Age-restricted)
- ✅ Video private/unlisted dengan akses terbatas
- ✅ Video member-only channel
- ✅ Bypass pembatasan region
- ✅ Menghindari error "Sign in to confirm you're not a bot"

## Cara 1: Export Cookies dari Browser (Recommended)

### Menggunakan Browser Extension

1. **Install Extension** (pilih salah satu):
   - Chrome/Edge: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - Firefox: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

2. **Login ke YouTube**
   - Buka [youtube.com](https://youtube.com)
   - Login dengan akun Google Anda

3. **Export Cookies**
   - Klik icon extension di toolbar
   - Pilih "Export" atau "Get cookies"
   - Save file sebagai `youtube_cookies.txt`

4. **Simpan File Cookies**
   - Pindahkan file `youtube_cookies.txt` ke folder project:
     ```
     youtubeClipper/
     └── backend/
         └── youtube_cookies.txt  <-- Simpan di sini
     ```

## Cara 2: Auto-Extract dari Browser (Termudah)

Kode sudah diupdate untuk otomatis mengambil cookies dari browser!

**Tidak perlu export manual**, `yt-dlp` akan otomatis mengambil cookies dari:
1. Chrome (default)
2. Edge
3. Firefox
4. Safari (macOS)

**Syarat:**
- Anda sudah login ke YouTube di browser tersebut
- Browser dalam keadaan tertutup saat download (untuk keamanan)

### Mengubah Browser Default

Edit file `downloader.py` line 59:

```python
# Untuk Chrome (default)
ydl_opts['cookiesfrombrowser'] = ('chrome',)

# Untuk Edge
ydl_opts['cookiesfrombrowser'] = ('edge',)

# Untuk Firefox
ydl_opts['cookiesfrombrowser'] = ('firefox',)
```

## Cara Menggunakan

### Opsi A: Dengan File Cookies (Manual)

Update request API Anda di frontend:

```typescript
const response = await fetch('http://localhost:8000/api/process', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    youtube_url: videoUrl,
    segments: segments,
    resolution: '1080p',
    cookies_file: 'backend/youtube_cookies.txt'  // Path ke file cookies
  })
});
```

### Opsi B: Auto-Extract (Tidak Perlu Edit Frontend)

Biarkan parameter `cookies_file` kosong atau `null`, sistem akan otomatis mengambil dari browser:

```typescript
const response = await fetch('http://localhost:8000/api/process', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    youtube_url: videoUrl,
    segments: segments,
    resolution: '1080p'
    // cookies_file tidak perlu dikirim!
  })
});
```

## Troubleshooting

### Error: "Sign in to confirm you're not a bot"
- ✅ Pastikan cookies valid dan tidak expired
- ✅ Re-export cookies dari browser yang masih login
- ✅ Coba logout dan login ulang di YouTube

### Error: "HTTP Error 403: Forbidden"
- ✅ Pastikan cookies file path benar
- ✅ Coba gunakan auto-extract dari browser
- ✅ Update yt-dlp ke versi terbaru: `pip install -U yt-dlp`

### Auto-extract tidak bekerja
- ✅ Pastikan browser dalam keadaan tertutup
- ✅ Pastikan sudah login ke YouTube di browser tersebut
- ✅ Coba browser lain (Chrome/Edge/Firefox)

## Keamanan

⚠️ **PENTING**: 
- File `youtube_cookies.txt` berisi informasi login Anda
- **JANGAN** commit file ini ke Git!
- Tambahkan ke `.gitignore`:
  ```
  backend/youtube_cookies.txt
  *.cookies.txt
  ```

## Testing

Test dengan video age-restricted:

```bash
# Di backend folder
python -c "from core.downloader import download_youtube_video; download_youtube_video('https://www.youtube.com/watch?v=VIDEO_ID', 'temp', '1080p')"
```

Jika berhasil, video akan terdownload tanpa error!

## Update Dependencies

Pastikan yt-dlp versi terbaru untuk fitur cookies:

```bash
cd backend
pip install -U yt-dlp
```

---

**Happy Clipping! 🎬**
