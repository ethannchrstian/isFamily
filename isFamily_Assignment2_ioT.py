'''Smart Lamp System
Fitur Utama:

Lampu Merah (22:00 - 06:00)
Lampu merah akan menyala secara otomatis mulai pukul 22:00 hingga 06:00.
    Alasan penggunaan lampu merah:
    - Membantu tubuh tetap memproduksi melatonin
    - Menciptakan suasana yang lebih rileks
    - Meningkatkan kualitas tidur
Buzzer (06:00)
Tepat pukul 06:00, buzzer akan berbunyi terus-menerus selama 15 menit.
Pengguna dapat mematikannya dengan menekan dan menahan tombol yang tersedia.
Untuk mematikan buzzernya dapat dilakukan dengan menakan dan menahan tombolnya +- 5-7 detik.

Lampu Kuning (06:01 - 21:59)
Mulai pukul 06:01, lampu kuning akan aktif berdasarkan kondisi ruangan untuk menghemat energi.
Sistem ini menggunakan dua sensor:

LDR Sensor: Mengukur tingkat kecerahan ruangan.
PIR Sensor: Mendeteksi adanya pergerakan.
🔄 Logika Kerja Lampu Kuning:

Ruangan gelap + ada pergerakan → Lampu menyala (ada aktivitas di ruangan gelap)
Ruangan gelap + tidak ada pergerakan → Lampu mati (tidak ada aktivitas, tidak perlu menyalakan lampu)
Ruangan terang + ada pergerakan → Lampu mati (cukup terang tanpa perlu lampu tambahan)
Ruangan terang + tidak ada pergerakan → Lampu mati (ruangan sudah terang tanpa aktivitas)

OLED Display:
Menampilkan informasi secara real-time, yaitu:
Waktu (WIB) dan tanggal
Status lampu merah & kuning (ON/OFF)
Status pergerakan (Motion) → M:
Y → Ada pergerakan
N → Tidak ada pergerakan
Tingkat kegelapan ruangan (dalam persentase) untuk memudahkan pembacaan pengguna'''

import network
import ntptime
import time
import urequests
from machine import Pin, ADC, I2C
from ssd1306 import SSD1306_I2C
from time import sleep

# --- Konfigurasi Wi-Fi ---
WIFI_SSID = 'Indihome 4_G'
WIFI_PASSWORD = '14725836'

# --- Konfigurasi API ---
FLASK_API_URL = "http://192.168.100.61:5000/sensor1"

# --- Konfigurasi Ubidots ---
UBIDOTS_TOKEN = "BBUS-P5UWOWFdp6MPFGDS5n7rrDjgCiRfem"
UBIDOTS_DEVICE_LABEL = "iot_isfamily"
UBIDOTS_URL = f"http://industrial.api.ubidots.com/api/v1.6/devices/{UBIDOTS_DEVICE_LABEL}"

# --- Pin ---
LDR_PIN = 34
LED_MERAH_PIN = 2
LED_KUNING_PIN = 4
BUZZER_PIN = 15
BUTTON_PIN = 18
PIR_PIN = 23
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21

# --- Inisialisasi Perangkat Keras ---
ldr = ADC(Pin(LDR_PIN))
ldr.atten(ADC.ATTN_11DB)
led_merah = Pin(LED_MERAH_PIN, Pin.OUT)
led_kuning = Pin(LED_KUNING_PIN, Pin.OUT)
buzzer = Pin(BUZZER_PIN, Pin.OUT)
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
pir_sensor = Pin(PIR_PIN, Pin.IN, Pin.PULL_DOWN)
i2c = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN))
oled = SSD1306_I2C(128, 64, i2c)

# --- Fungsi Koneksi Wi-Fi ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('🔌 Menghubungkan ke Wi-Fi...')
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            pass
    print('✅ Terhubung ke Wi-Fi:', wlan.ifconfig())

# --- Fungsi Sinkronisasi Waktu ---
def update_time():
    try:
        ntptime.host = "pool.ntp.org"
        print("🔄 Mencoba sinkronisasi waktu...")
        ntptime.settime()
        print("✅ Waktu berhasil disinkronkan.")
    except Exception as e:
        print("⚠️ Gagal sinkronisasi waktu:", e)

# --- Fungsi Untuk Mendapatkan Waktu Lokal ---
def get_local_time(offset_hours=7): # = 7 artinya UTC + 7 yaitu waktu indonesia barat 
    raw_unix = time.time()  # Waktu UTC (detik)
    local_unix = raw_unix + offset_hours * 3600  # Waktu lokal (detik)
    current_time = time.localtime(local_unix)

    # String waktu lokal untuk tampilan OLED dan pengiriman ke Flask
    local_time_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        current_time[0], current_time[1], current_time[2], current_time[3], current_time[4], current_time[5]
    )

    # Epoch time dalam milidetik untuk Ubidots (menggunakan waktu UTC)
    timestamp_ms = int(raw_unix * 1000)

    return current_time, local_time_str, timestamp_ms

# --- Fungsi Konversi & Deteksi ---
def convert_ldr_to_percentage(ldr_value):
    percentage = int((ldr_value / 4095) * 100)
    return max(0, min(percentage, 100))  #konversi nilai LDR ke dalam persentase agar memudahkan ( meningkatkan user experience) user untuk membacanya

def is_night_mode(hour):
    return hour >= 22 or hour < 6

def is_motion_detected():
    return pir_sensor.value() == 1

# --- Fungsi untuk Membuat status_text & Menampilkan di OLED & Terminal ---
def create_and_show_status(year, month, day, hour, minute, second, lampu_merah_on, lampu_kuning_on, local_time_str):
    ldr_value = ldr.read()
    ldr_percentage = convert_ldr_to_percentage(ldr_value)
    motion_detect = is_motion_detected()

    status_text = (
        f"[Tanggal] {day:02d}/{month:02d}/{year} | [Jam] {hour:02d}:{minute:02d}:{second:02d} "
        f"[Gelap]: {ldr_percentage}% | [Motion]: {'YES' if motion_detect else 'NO'} "
        f"[Merah]: {'ON' if lampu_merah_on else 'OFF'} | [Kuning]: {'ON' if lampu_kuning_on else 'OFF'}"
    )

    print(status_text)  # print ke Serial

    # display di OLED
    oled.fill(0)
    oled.text(f"{day:02d}/{month:02d}/{year}", 0, 0)
    oled.text(f"{hour:02d}:{minute:02d}:{second:02d}", 0, 12)
    oled.text(f"Gelap:{ldr_percentage}% M:{'Y' if motion_detect else 'N'}", 0, 24)
    oled.text(f"Merah:{'ON' if lampu_merah_on else 'OFF'}", 0, 36)
    oled.text(f"Kuning:{'ON' if lampu_kuning_on else 'OFF'}", 0, 48)
    oled.show()

    return status_text, ldr_percentage, motion_detect

# --- Fungsi untuk Kontrol Buzzer ---
def start_buzzer():
    buzzer.value(1)

def stop_buzzer():
    buzzer.value(0)

# --- Fungsi Kirim Data ke Flask (gunakan string waktu lokal) ---
def send_status(status_text, local_time_str):
    payload = {
        "status": status_text,
        "timestamp": local_time_str  # String format untuk Flask
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = urequests.post(FLASK_API_URL, json=payload, headers=headers)
        print("✅ Data ke Flask terkirim:", response.text)
        response.close()
    except Exception as e:
        print("❌ Gagal mengirim data ke Flask:", e)

# --- Fungsi Kirim Data ke Ubidots (gunakan epoch milidetik) ---
def send_to_ubidots(ldr_percentage, motion_detected, lampu_merah_on, lampu_kuning_on, timestamp_ms):
    payload = {
        "ldr_percentage": float(ldr_percentage),
        "motion_detected": int(motion_detected),
        "lampu_merah": int(lampu_merah_on),
        "lampu_kuning": int(lampu_kuning_on),
        "timestamp": timestamp_ms  # Epoch time dalam milidetik
    }

    headers = {
        "X-Auth-Token": UBIDOTS_TOKEN,
        "Content-Type": "application/json"
    }

    try:
        response = urequests.post(UBIDOTS_URL, json=payload, headers=headers)
        print(f"✅ Data ke Ubidots terkirim: {response.status_code}, {response.text}")
        response.close()
    except Exception as e:
        print(f"❌ Gagal mengirim ke Ubidots: {e}")

# --- Inisialisasi ---
connect_wifi()
update_time()

BUZZER_START = (6, 0)
BUZZER_END = (6, 15)
buzzer_triggered_today = False

# --- Loop Utama ---
while True:
    current_time, local_time_str, timestamp_ms = get_local_time()
    year, month, day, hour, minute, second = current_time[:6]
    motion_detected = is_motion_detected()

    # 🔔 Kontrol Buzzer
    if BUZZER_START <= (hour, minute) <= BUZZER_END and not buzzer_triggered_today:
        start_buzzer()
        print("🔔 Buzzer aktif!")
        buzzer_triggered_today = True

    if button.value() == 0 and buzzer.value():
        stop_buzzer()
        print("🛑 Tombol ditekan - Buzzer dimatikan.")

    if (hour, minute) > BUZZER_END and buzzer.value():
        stop_buzzer()
        print("⏰ Waktu habis - Buzzer dimatikan.")

    # Reset buzzer harian
    if hour == 6 and minute >= 16 and buzzer_triggered_today:
        buzzer_triggered_today = False
        print("🔄 Buzzer direset untuk esok hari.")

    # 💡 Kontrol Lampu
    ldr_percentage = convert_ldr_to_percentage(ldr.read())

    if is_night_mode(hour):
        led_merah.on()
        led_kuning.off()
    else:
        led_merah.off()
        led_kuning.value(ldr_percentage > 60 and motion_detected)

    # 🎨 Buat status, tampilkan, dan kirim data
    status_text, ldr_percentage, motion_detected = create_and_show_status(
        year, month, day, hour, minute, second,
        led_merah.value(), led_kuning.value(), local_time_str
    )

    send_status(status_text, local_time_str)       # Kirim waktu sebagai string ke Flask
    send_to_ubidots(ldr_percentage, motion_detected, led_merah.value(), led_kuning.value(), timestamp_ms)  # Kirim epoch ke Ubidots

    sleep(5)  # Loop setiap 5 detik
