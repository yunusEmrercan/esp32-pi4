import time

KEYS = {
    4: 'a', 5: 'b', 6: 'c', 7: 'd', 8: 'e',
    9: 'f', 10: 'g', 11: 'h', 12: 'i', 13: 'j',
    14: 'k', 15: 'l', 16: 'm', 17: 'n', 18: 'o',
    19: 'p', 20: 'q', 21: 'r', 22: 's', 23: 't',
    24: 'u', 25: 'v', 26: 'w', 27: 'x', 28: 'y',
    29: 'z', 30: '1', 31: '2', 32: '3', 33: '4',
    34: '5', 35: '6', 36: '7', 37: '8', 38: '9',
    39: '0', 40: '\n', 44: ' ', 45: '-', 55: '.'
}

def parse_keycodes(buffer):
    return ''.join(KEYS.get(b, '') for b in buffer).strip()

def clean_buffer_str(s):
    uuid_len = 36
    if len(s) >= 2 * uuid_len:
        first = s[:uuid_len]
        second = s[uuid_len:uuid_len*2]
        if first == second:
            s = s[uuid_len:]
    return s

def read_rfid():
    try:
        with open("/dev/hidraw0", "rb") as rfid_file:
            print("🎯 RFID okuyucu hazır. Kartı okutun...")
            buffer = b""
            while True:
                raw = rfid_file.read(8)
                code = raw[2]
                if code == 0:
                    continue
                if code == 40:  # Enter tuşu
                    card = parse_keycodes(buffer)
                    card = clean_buffer_str(card)
                    if card:
                        print(f"✅ Kart Okundu: {card}")
                    buffer = b""
                else:
                    buffer += bytes([code])
    except FileNotFoundError:
        print("❌ /dev/hidraw0 bulunamadı. RFID takılı mı?")
    except Exception as e:
        print(f"⚠️ Hata: {e}")

if __name__ == "__main__":
    read_rfid()
