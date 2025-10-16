# rpi_bridge.py
import glob, serial, time, logging, subprocess
from threading import Thread

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

# USB port bulma (esp)
def find_first(pattern):
    import glob
    arr = glob.glob(pattern)
    return arr[0] if arr else None

# ESP port
esp_port = None
while not esp_port:
    esp_port = find_first('/dev/ttyUSB*')
    if not esp_port:
        logging.warning("ESP USB bulunamadı, bekleniyor...")
        time.sleep(2)
logging.info(f"ESP: {esp_port}")

# QR port
qr_port = None
while not qr_port:
    qr_port = find_first('/dev/ttyACM*')
    if not qr_port:
        logging.warning("QR portu bulunamadı, bekleniyor...")
        time.sleep(2)
logging.info(f"QR: {qr_port}")

esp_serial = serial.Serial(esp_port, baudrate=115200, timeout=1)

KEYS = { 4:'a',5:'b',6:'c',7:'d',8:'e',9:'f',10:'g',11:'h',12:'i',13:'j',14:'k',15:'l',16:'m',17:'n',18:'o',19:'p',20:'q',21:'r',22:'s',23:'t',24:'u',25:'v',26:'w',27:'x',28:'y',29:'z',30:'1',31:'2',32:'3',33:'4',34:'5',35:'6',36:'7',37:'8',38:'9',39:'0',40:'\n',44:' ',45:'-',55:'.' }

def parse_keycodes(buffer):
    return ''.join(KEYS.get(b,'') for b in buffer).strip()

def clean_buffer_str(s):
    uuid_len = 36
    if len(s) >= 2*uuid_len:
        first = s[:uuid_len]
        second = s[uuid_len:uuid_len*2]
        if first == second:
            s = s[uuid_len:]
    return s

def read_rfid(timeout=7):
    try:
        with open("/dev/hidraw0", "rb") as rfid_file:
            buffer = b""
            end = time.time()+timeout
            while time.time() < end:
                raw = rfid_file.read(8)
                if not raw:
                    continue
                code = raw[2]
                if code == 0:
                    continue
                if code == 40:
                    card = parse_keycodes(buffer)
                    return clean_buffer_str(card)
                else:
                    buffer += bytes([code])
    except Exception as e:
        logging.warning(f"RFID hatası: {e}")
    return None

def read_qr_uart(port=qr_port, baudrate=9600, timeout=5):
    try:
        ser = serial.Serial(port, baudrate=baudrate, timeout=0.1)
        start = time.time()
        data = b''
        while time.time()-start < timeout:
            if ser.in_waiting:
                data += ser.read(ser.in_waiting)
                if b'\n' in data:
                    break
            time.sleep(0.05)
        ser.close()
        if not data:
            return None
        return data.decode(errors='ignore').strip()
    except Exception as e:
        logging.warning(f"QR read error: {e}")
        return None

def main_loop():
    mode = "RFID"
    logging.info("Başlatıldı. Mod: RFID")
    while True:
        # esp'den mod değişikliği gelebilir
        if esp_serial.in_waiting:
            try:
                line = esp_serial.readline().decode(errors='ignore').strip()
                if line.startswith("MODE:"):
                    mode = line.split(":")[1].upper()
                    logging.info(f"MODE değişti: {mode}")
            except Exception as e:
                logging.warning(f"ESP okuma hatası: {e}")

        if mode == "RFID":
            rfid = read_rfid(timeout=3)
            if rfid:
                logging.info(f"RFID okundu: {rfid}")
                esp_serial.write(f"RFID:{rfid}\n".encode())
        elif mode == "QR":
            qr = read_qr_uart(timeout=5)
            if qr:
                logging.info(f"QR okundu: {qr}")
                # Eğer qr systemd ile başlıyorsa pi kendisi çalıştırsın
                if qr.startswith("systemd:"):
                    cmd = qr.split(":",1)[1]
                    logging.info(f"Systemd komutu: {cmd}")
                    if cmd == "reboot":
                        esp_serial.write(b"QR:ACK_SYSTEMD_REBOOT\n")
                        # reboot çalıştır
                        subprocess.Popen(['sudo','systemctl','reboot'])
                    elif cmd in ("shut","shutdown","poweroff"):
                        esp_serial.write(b"QR:ACK_SYSTEMD_SHUTDOWN\n")
                        subprocess.Popen(['sudo','shutdown','now'])
                    else:
                        esp_serial.write(b"QR:ACK_SYSTEMD_UNKNOWN\n")
                else:
                    esp_serial.write(f"QR:{qr}\n".encode())

        time.sleep(0.1)

if __name__ == "__main__":
    main_loop()
