"""Small built-in UI translations for the desktop client."""
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QComboBox, QGroupBox, QTableWidget, QTabWidget, QWidget
import re

ID_TO_EN = {
    "Dashboard": "Dashboard", "Riwayat": "History", "Pengaturan": "Settings",
    "File": "File", "Bagikan": "Share", "Bantuan": "Help", "Keluar": "Exit",
    "Tambah Folder Baru...": "Add folder...", "Tambah Folder Baru": "Add folder",
    "Ekspor Backup...": "Export backup...", "Impor Backup...": "Import backup...",
    "Tampilkan QR SMB...": "Show SMB QR...", "Tampilkan QR WiFi...": "Show Wi-Fi QR...",
    "Simpan QR...": "Save QR...",
    "Nama di Daftar:": "List display name:",
    "Kosongkan untuk memakai nama folder asli": "Leave blank to use the folder name",
    "●  Aktif": "●  Active", "○  Tidak aktif": "○  Inactive",
    "Tentang ItShare": "About ItShare", "Tidak ada sesi aktif": "No active session",
    "BERBAGI DI JARINGAN LOKAL": "LOCAL NETWORK SHARING", "Bagikan folder ke Android": "Share a folder with Android",
    "Pilih folder di PC, lalu pindai QR dari perangkat Android pada jaringan yang sama.": "Select a PC folder, then scan its QR code from Android on the same network.",
    "FOLDER DIBAGIKAN": "SHARED FOLDERS", "KONEKSI ANDROID": "ANDROID CONNECTION",
    "Kode QR belum tersedia": "QR unavailable", "QR belum aktif": "QR not active",
    "Mulai server untuk menampilkan detail koneksi.": "Start sharing to view connection details.",
    "Perbesar QR SMB": "View SMB QR", "Salin Alamat": "Copy address", "Folder Saya": "My folders",
    "Buka di File Manager": "Open in File Explorer", "Belum ada folder dibagikan": "No shared folders",
    "Pilih Tambah Folder Baru untuk memilih folder dan mulai berbagi": "Add a folder to start sharing",
    "Pindai untuk terhubung": "Scan to connect", "Kode QR belum tersedia": "QR code unavailable",
    "Alamat Disalin": "Address copied", "Folder tidak ditemukan": "No folders found", "Coba kata kunci lain.": "Try another search.",
    "Aktif": "Active", "Tidak aktif": "Inactive", "Hanya Baca": "Read-only", "Hentikan": "Stop", "Mulai": "Start", "Hapus": "Remove",
    "‹ Sebelumnya": "‹ Previous", "Berikutnya ›": "Next ›", "Pengaturan tersimpan": "Settings saved",
    "AKTIVITAS": "ACTIVITY", "Lihat sesi koneksi dan aktivitas transfer berkas.": "Review connection sessions and file transfers.",
    "Koneksi": "Connections", "Transfer Berkas": "File transfers", "Muat Ulang": "Refresh",
    "Klien Aktif": "Active clients", "Belum ada klien aktif": "No active clients", "TERSAMBUNG": "CONNECTED",
    "koneksi SMB": "SMB connections",
    "Pengaturan folder": "Folder settings",
    "Hapus Riwayat Koneksi": "Clear connection history", "Hapus Koneksi": "Clear history", "Halaman": "Page", "sesi": "sessions",
    "DIMULAI": "STARTED", "DIHENTIKAN": "STOPPED", "dimulai": "started", "dihentikan": "stopped", "Sesi": "Session",
    "Pengaturan Aplikasi": "Application settings", "Default Server": "Server defaults",
    "Aplikasi & Tampilan": "App & appearance", "Port Default:": "Default port:", "Read-Only secara default": "Read-only by default",
    "Batas Waktu Default:": "Default time limit:", "jam": "hours", "0 = permanen": "0 = unlimited",
    "Halaman saat dibuka:": "Startup page:", "Jumlah folder per halaman:": "Folders per page:",
    "Ikuti tema Windows": "Follow Windows theme", "Terang": "Light", "Gelap": "Dark", "Tema aplikasi:": "App theme:",
    "Tampilkan lokasi folder di Dashboard": "Show folder paths on Dashboard",
    "Sembunyikan QR secara default": "Hide QR code by default",
    "QR akan diburamkan setiap kali sesi berbagi dimulai.": "The QR code will be blurred whenever a sharing session starts.",
    "Konfirmasi sebelum menghentikan share": "Confirm before stopping a share", "Pertahankan share saat aplikasi ditutup": "Keep sharing after closing the app",
    "Disimpan": "Saved",
    "Folder yang dibagikan dan status server (Ctrl+1)": "Shared folders and server status (Ctrl+1)",
    "Riwayat koneksi dan transfer (Ctrl+2)": "Connection and transfer history (Ctrl+2)",
    "Pengaturan server dan tampilan aplikasi (Ctrl+3)": "Server and app settings (Ctrl+3)",
    "Konfigurasi Share Baru": "New share setup", "Pilih Folder": "Select folder", "Jelajahi": "Browse",
    "Opsi Keamanan": "Security options", "Batas Waktu:": "Time limit:", "Port SMB:": "SMB port:",
    "Interface:": "Network interface:", "Tidak terdeteksi": "Not detected", "Generate Ulang": "Regenerate",
    "Batal": "Cancel", "Mulai Server": "Start server", "Scan QR untuk Terhubung": "Scan QR to connect",
    "Buka aplikasi SMB di HP → Scan QR ini": "Scan this QR code from your phone",
    "Baca & Tulis": "Read and write", "Koneksi SMB": "SMB connection", "Salin Semua Kredensial": "Copy credentials",
    "Tampilkan QR WiFi": "Show Wi-Fi QR", "Sesi Permanen": "Unlimited session", "Sesi telah berakhir": "Session expired",
    "Sisa waktu:": "Time remaining:", "Bagikan Koneksi WiFi via QR": "Share Wi-Fi via QR",
    "Keamanan:": "Security:", "Password:": "Password:", "SSID:": "SSID:", "Tutup": "Close", "Generate QR": "Generate QR",
    "Nama SSID:": "Network name:", "Perbarui QR WiFi": "Refresh Wi-Fi QR", "Masukkan detail lalu klik Perbarui QR WiFi": "Enter details to generate a Wi-Fi QR code",
    "Status: Server belum berjalan": "Status: Server is stopped", "Hentikan Server": "Stop server",
    "Buat Share && Mulai Server": "Create share && start server", "Jelajahi...": "Browse...", "Pilih Induk...": "Choose parent...",
    "Folder": "Folder", "Status": "Status", "Mode": "Mode", "Port": "Port", "Aksi": "Actions",
    "Bahasa:": "Language:", "English": "English", "Bahasa Indonesia": "Indonesian",
    "Cari folder...": "Search folders...", "Folder dibagikan": "Shared folders",
    "Kredensial akan digenerate otomatis saat sesi dibuat.": "Credentials are generated when a session starts.",
    "Tambah Folder ke Share": "Add folder to share", "Folder Tidak Sesuai": "Folder not compatible",
    "Semua folder harus berada di drive yang sama.": "All folders must be on the same drive.",
    "Nama Share di Android:": "Share name shown on Android:",
    "Nama yang akan terlihat di Android": "Name shown on Android",
    "Dibuat otomatis dari nama share di atas": "Generated from the share name above",
    "Pilih folder yang masih tersedia di PC.": "Select a folder available on this PC.",
    "Tidak Dapat Membuka File Manager": "Could not open File Explorer",
    "Belum ada aktivitas transfer di PC": "No file activity from Android yet",
    "Hapus Riwayat Transfer": "Clear Transfer History",
    "Hapus riwayat transfer?": "Clear transfer history?",
    "Hapus catatan transfer yang diterima PC?": "Clear transfer activity recorded by this PC?",
    "DIUNGGAH": "UPLOADED",
    "DIUNDUH": "DOWNLOADED",
    "Bagikan Folder Baru": "Share a New Folder",
    "Pilih folder, lalu pindai QR dari Android. Hanya 3 langkah.": "Choose a folder, then scan its QR code from Android. Just 3 steps.",
    "Folder mana yang mau dibagikan?": "Which folder do you want to share?",
    "Pilih folder yang sudah ada": "Choose an existing folder",
    "Belum punya folder?": "Need a new folder?",
    "Sudah punya folder?": "Already have a folder?",
    "Pilih folder yang tersedia di PC.": "Choose a folder on this PC.",
    "Nama yang tampil di HP": "Name shown on Android",
    "Nama yang muncul di Android": "Name shown on Android",
    "Terisi otomatis dari nama folder. Boleh diganti.": "Uses the folder name by default. You can change it.",
    "Atur akses dan waktu": "Set access and duration",
    "Hanya lihat  ·  Disarankan": "View only  ·  Recommended",
    "HP bisa mengunduh, tetapi tidak bisa mengubah atau menghapus.": "Android can download, but cannot edit or delete.",
    "Boleh ubah": "Allow changes",
    "HP bisa mengunggah, membuat folder, dan menghapus.": "Android can upload, create folders, and delete.",
    "Berapa lama dibagikan?": "How long should it be shared?",
    "Tanpa batas": "Unlimited",
    "Lainnya": "Custom",
    "Durasi (jam)": "Duration (hours)",
    "Pengaturan lanjutan  ·  Opsional": "Advanced settings  ·  Optional",
    "Jaringan": "Network",
    "Pengguna dan kata sandi (otomatis)": "Username and password (automatic)",
    "Kata sandi otomatis": "Automatic credentials",
    "Tampilkan": "Show",
    "Sembunyikan": "Hide",
    "Buat Ulang": "Regenerate",
    "Berkas hanya tersedia di jaringan lokal.": "Files are available on the local network only.",
    "Mulai Berbagi": "Start sharing",
    "Pilih Lokasi": "Choose location",
    "Pilih Direktori Induk": "Choose parent folder",
    "Lokasi induk": "Parent location",
    "Nama folder": "Folder name",
    "Nama folder baru": "New folder name",
    "Ganti hanya jika port sedang dipakai aplikasi lain.": "Change this only if another app is using the port.",
    "Already have a folder?": "Already have a folder?",
    "Need a new folder?": "Need a new folder?",
    "Belum ada folder dipilih": "No folder selected",
    "1 jam": "1 hour",
    "4 jam": "4 hours",
    "8 jam": "8 hours",
    "Direkomendasikan": "Recommended",
    "Ganti hanya jika port sedang dipakai aplikasi lain.": "Change only if another app is using the port.",
    "Masukkan nama folder baru.": "Enter a new folder name.",
    "Pilih folder yang valid.": "Choose a valid folder.",
    "Nama Kosong": "Name required",
    "Gagal Buat Folder": "Could not create folder",
    "Folder Tidak Valid": "Invalid folder",
    "Gunakan 1–80 huruf, angka, garis bawah, tanda minus, atau $. Tanpa spasi.": "Use 1–80 letters, numbers, underscores, hyphens, or $. No spaces.",
    "Buat folder baru": "Create a new folder",
    "Nama yang akan terlihat di Android": "Name shown on Android",
    "ItShare PC belum menerima catatan transfer dari Android. Riwayat transfer yang sebenarnya tersedia di tab Riwayat pada aplikasi Android.": "Transfer history is available in the Android app.",
    "Belum ada riwayat koneksi": "No connection history",
    "Riwayat sesi berbagi akan muncul di sini saat server ItShare dimulai atau dihentikan.": "Share sessions appear here when the server starts or stops.",
    "Alamat belum diketahui": "Address unavailable", "Folder bersama": "Shared folder",
    "Konfirmasi Keluar": "Confirm exit", "Nama Share Tidak Valid": "Invalid share name",
    "Tambah folder untuk mulai": "Add a folder to get started", "Coba kata kunci lain.": "Try another search.",
    "8 folder per halaman": "8 folders per page", "12 folder per halaman": "12 folders per page", "20 folder per halaman": "20 folders per page",
    "Mulai server berbagi untuk menampilkan detail koneksi.": "Start sharing to view connection details.",
    "Mulai server berbagi untuk menampilkan QR dan alamat koneksi yang aktif.": "Start sharing to view the QR code and address.",
    "Pindai dari Android di jaringan yang sama.": "Scan from Android on the same network.",
    "Folder tidak ditemukan": "No folders found", "Pilih folder yang masih tersedia di PC.": "Select an available folder.",
    "Hanya Baca": "Read-only", "Tidak ada sesi aktif": "No active session",
    "⏱ Sesi Permanen": "Unlimited session", "⏱ Sesi telah berakhir": "Session expired",
    "Folder dibagikan": "Shared folders", "Baca-Tulis": "Read/write", "Read-only secara default": "Read-only by default",
    "Pertahankan share saat aplikasi ditutup": "Keep sharing after closing the app",
    "Tampilkan lokasi folder di Dashboard": "Show folder paths on Dashboard",
    "Gunakan tampilan Dashboard yang lebih ringkas": "Use compact Dashboard layout",
    "Konfirmasi sebelum menghentikan share": "Confirm before stopping a share",
    "Pengguna:": "User:", "Pindai dari Android di jaringan yang sama.": "Scan from Android on the same network.",
    "Folder Saya": "My folders", "Cari folder...": "Search folders...", "Folder tidak ditemukan": "No folders found",
    "Muat Ulang": "Refresh", "Sebelumnya": "Previous",
    "Siap. Pilih folder pada Dashboard untuk mulai berbagi.": "Ready. Add a folder to start sharing.",
    "● Server dihentikan. Siap untuk sesi baru.": "● Server stopped. Ready for a new session.",
    "Kredensial diperbarui. Klien lama terputus.": "Credentials updated. Previous clients disconnected.",
    "Sesi direset. Pilih folder untuk mulai berbagi.": "Session reset. Select a folder to start sharing.",
}

EN_TO_ID = {english: indonesian for indonesian, english in ID_TO_EN.items() if english != indonesian}
EN_TO_ID.update({
    "Light": "Terang", "Dark": "Gelap", "Follow Windows theme": "Ikuti tema Windows",
    "Default Server": "Server Default", "File": "File", "Folder": "Folder", "Status": "Status",
    "Mode": "Mode", "Port": "Port", "Dashboard": "Dashboard",
    "App & appearance": "Aplikasi & Tampilan",
})
EN_TO_ID.update({"Indonesian": "Bahasa Indonesia", "Language:": "Bahasa:", "Search folders...": "Cari folder..."})
EN_TO_ID.update({"Server defaults": "Pengaturan server", "Default Server": "Server default", "App & appearance": "Aplikasi & Tampilan"})

def translate(text: str, language: str) -> str:
    if not isinstance(text, str):
        return text
    for symbol in ("📡", "📂", "📁", "⚙️", "⚙", "📱", "📋", "📶", "🔄", "💾", "▶", "⏱", "✅", "⚠️", "🔗", "🔍", "📜", "📲"):
        text = text.replace(symbol, "")
    text = text.strip()
    if language != "id":
        smb_count = re.fullmatch(r"(\d+) koneksi SMB", text)
        if smb_count:
            count = int(smb_count.group(1))
            return f"{count} SMB connection" if count == 1 else f"{count} SMB connections"

        if text in ID_TO_EN:
            return ID_TO_EN[text]
        for source, target in sorted(ID_TO_EN.items(), key=lambda item: len(item[0]), reverse=True):
            if len(source) >= 8 and source in text:
                text = text.replace(source, target)
        if text.startswith("● Aktif  "):
            text = "● Active  " + text[len("● Aktif  "):]
        if text.startswith("● Server aktif  "):
            text = "● Server active  " + text[len("● Server aktif  "):]
        if text.startswith("● Tidak ada sesi aktif"):
            return "● No active session"
        if text.startswith("● Server dihentikan."):
            text = "● Server stopped. Ready for a new session."
        if text.startswith("Sesi dimulai · "):
            text = "Session started · " + text[len("Sesi dimulai · "):]
        if text.startswith("Sesi dihentikan · "):
            text = "Session stopped · " + text[len("Sesi dihentikan · "):]
        if text.startswith("Halaman ") and " dari " in text:
            return text.replace("Halaman ", "Page ", 1).replace(" dari ", " of ", 1).replace(" folder", " folders").replace(" sesi", " sessions")
        return text.replace(" · Hanya baca", " · Read-only").replace(" · Baca-tulis", " · Read/write")
    if language == "id":
        smb_count = re.fullmatch(r"(\d+) SMB connections?", text)
        if smb_count:
            return f"{smb_count.group(1)} koneksi SMB"
        if text in EN_TO_ID:
            return EN_TO_ID[text]
        for source, target in sorted(EN_TO_ID.items(), key=lambda item: len(item[0]), reverse=True):
            if len(source) >= 8 and source in text:
                text = text.replace(source, target)
        return text
    return ID_TO_EN.get(text, text)

def apply_language(root: QWidget, language: str) -> None:
    """Translate existing widgets while retaining their original source text."""
    language = "id" if language == "id" else "en"
    root.setProperty("_itshare_language", language)
    widgets = [root, *root.findChildren(QWidget), *root.findChildren(QAction)]
    for widget in widgets:
        for getter, setter, key in (
            ("text", "setText", "text"),
            ("toolTip", "setToolTip", "toolTip"),
            ("placeholderText", "setPlaceholderText", "placeholder"),
            ("windowTitle", "setWindowTitle", "windowTitle"),
        ):
            if not hasattr(widget, getter) or not hasattr(widget, setter):
                continue
            current = getattr(widget, getter)()
            original = widget.property(f"_itshare_source_{key}")
            applied = widget.property(f"_itshare_applied_{key}")
            if original is None or (applied is not None and current != applied):
                original = current
                widget.setProperty(f"_itshare_source_{key}", original)
            localized = translate(original, language)
            getattr(widget, setter)(localized)
            widget.setProperty(f"_itshare_applied_{key}", localized)

        if isinstance(widget, QComboBox):
            source_items = widget.property("_itshare_source_items")
            if source_items is None:
                source_items = [widget.itemText(index) for index in range(widget.count())]
                widget.setProperty("_itshare_source_items", source_items)
            for index, source in enumerate(source_items):
                if index < widget.count():
                    widget.setItemText(index, translate(source, language))
        if isinstance(widget, QGroupBox):
            original_title = widget.property("_itshare_source_title")
            applied_title = widget.property("_itshare_applied_title")
            if original_title is None or (applied_title is not None and widget.title() != applied_title):
                original_title = widget.title()
                widget.setProperty("_itshare_source_title", original_title)
            localized_title = translate(original_title, language)
            widget.setTitle(localized_title)
            widget.setProperty("_itshare_applied_title", localized_title)

        if isinstance(widget, QTableWidget):
            headers = widget.property("_itshare_source_headers")
            if headers is None or len(headers) != widget.columnCount():
                headers = [widget.horizontalHeaderItem(index).text() if widget.horizontalHeaderItem(index) else "" for index in range(widget.columnCount())]
                widget.setProperty("_itshare_source_headers", headers)
            for index, source in enumerate(headers):
                if widget.horizontalHeaderItem(index):
                    widget.horizontalHeaderItem(index).setText(translate(source, language))

        if isinstance(widget, QTabWidget):
            tabs = widget.property("_itshare_source_tabs")
            if tabs is None or len(tabs) != widget.count():
                tabs = [widget.tabText(index) for index in range(widget.count())]
                widget.setProperty("_itshare_source_tabs", tabs)
            for index, source in enumerate(tabs):
                widget.setTabText(index, translate(source, language))
