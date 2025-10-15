import serial, glob, time

def find_qr_port():
    ports = glob.glob('/dev/ttyACM*')
    if not ports:
        print("❌ QR portu bulunamadı. Takılı mı?")
        return None
    print(f"📡 Bulunan QR Port: {ports[0]}")
    return ports[0]

def read_qr(port, baudrate=9600):
    try:
        ser = serial.Serial(port, baudrate=baudrate, timeout=0.1)
        print("🎯 QR okuyucu hazır. Kodu okutun...")
        qr_data = b""
        while True:
            if ser.in_waiting > 0:
                qr_data += ser.read(ser.in_waiting)
                if b'\n' in qr_data:
                    text = qr_data.decode(errors="ignore").strip()
                    print(f"✅ QR Okundu: {text}")
                    qr_data = b""
            time.sleep(0.05)
    except Exception as e:
        print(f"⚠️ QR Hata: {e}")

if __name__ == "__main__":
    qr_port = find_qr_port()
    if qr_port:
        read_qr(qr_port)
