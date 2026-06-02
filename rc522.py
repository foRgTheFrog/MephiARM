from machine import Pin, SoftSPI
import time

class RC522:
    OK = 0
    NOTAGERR = 1
    ERR = 2

    REQIDL = 0x26
    REQALL = 0x52
    AUTHENT1A = 0x60
    AUTHENT1B = 0x61

    CommandReg = 0x01
    ComIEnReg = 0x02
    DivlEnReg = 0x03
    ComIrqReg = 0x04
    DivIrqReg = 0x05
    ErrorReg = 0x06
    Status1Reg = 0x07
    Status2Reg = 0x08
    FIFODataReg = 0x09
    FIFOLevelReg = 0x0A
    WaterLevelReg = 0x0B
    ControlReg = 0x0C
    BitFramingReg = 0x0D
    CollReg = 0x0E
    ModeReg = 0x11
    TxModeReg = 0x12
    RxModeReg = 0x13
    TxControlReg = 0x14
    TxAutoReg = 0x15
    TxSelReg = 0x16
    RxSelReg = 0x17
    RxThresholdReg = 0x18
    DemodReg = 0x19
    MfTxReg = 0x1C
    MfRxReg = 0x1D
    SerialSpeedReg = 0x1F
    CRCResultRegH = 0x21
    CRCResultRegL = 0x22
    ModWidthReg = 0x24
    RFCfgReg = 0x26
    GsNReg = 0x27
    CWGsPReg = 0x28
    ModGsPReg = 0x29
    TModeReg = 0x2A
    TPrescalerReg = 0x2B
    TReloadRegH = 0x2C
    TReloadRegL = 0x2D
    TCounterValueRegH = 0x2E
    TCounterValueRegL = 0x2F
    TestSel1Reg = 0x31
    TestSel2Reg = 0x32
    TestPinEnReg = 0x33
    TestPinValueReg = 0x34
    TestBusReg = 0x35
    AutoTestReg = 0x36
    VersionReg = 0x37
    AnalogTestReg = 0x38
    TestDAC1Reg = 0x39
    TestDAC2Reg = 0x3A
    TestADCReg = 0x3B

    CMD_IDLE = 0x00
    CMD_CALC_CRC = 0x03
    CMD_TRANSCEIVE = 0x0C
    CMD_MF_AUTHENT = 0x0E
    CMD_SOFT_RESET = 0x0F

    def __init__(self, sck=5, mosi=6, miso=7, cs=4, rst=8):
        self.spi = SoftSPI(baudrate=100000, polarity=0, phase=0,
                           sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso))
        self.cs = Pin(cs, Pin.OUT)
        self.rst = Pin(rst, Pin.OUT)
        self.cs.value(1)
        self.rst.value(0)
        time.sleep_ms(50)
        self.reset()
        self.init()
        self.default_key_a = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
        self.default_key_b = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
        self.custom_key = self.hex_to_bytes("425245414B4D454946594F5543414E21")
        self.last_uid = None
        self.last_time = 0
        self.debounce_time = 1000

    def hex_to_bytes(self, hex_string):
        if len(hex_string) % 2 != 0:
            hex_string = '0' + hex_string
        result = []
        for i in range(0, len(hex_string), 2):
            result.append(int(hex_string[i:i+2], 16))
        return result

    def reset(self):
        self.rst.value(0)
        time.sleep_us(2)
        self.rst.value(1)
        time.sleep_ms(50)
        self.write_register(self.CommandReg, self.CMD_SOFT_RESET)
        time.sleep_ms(50)
        while self.read_register(self.CommandReg) & (1 << 4):
            time.sleep_us(10)

    def write_register(self, addr, val):
        self.cs.value(0)
        self.spi.write(bytes([((addr << 1) & 0x7E), val]))
        self.cs.value(1)

    def read_register(self, addr):
        self.cs.value(0)
        self.spi.write(bytes([((addr << 1) & 0x7E) | 0x80]))
        data = self.spi.read(1)
        self.cs.value(1)
        return data[0]

    def set_bitmask(self, reg, mask):
        self.write_register(reg, self.read_register(reg) | mask)

    def clear_bitmask(self, reg, mask):
        self.write_register(reg, self.read_register(reg) & (~mask))

    def init(self):
        self.write_register(self.Status2Reg, 0x00)
        self.write_register(self.TModeReg, 0x8D)
        self.write_register(self.TPrescalerReg, 0x3E)
        self.write_register(self.TReloadRegL, 30)
        self.write_register(self.TReloadRegH, 0)
        self.write_register(self.TxAutoReg, 0x40)
        self.write_register(self.ModeReg, 0x3D)
        self.antenna_on()
        time.sleep_ms(10)

    def antenna_on(self):
        current = self.read_register(self.TxControlReg)
        if not (current & 0x03):
            self.set_bitmask(self.TxControlReg, 0x03)

    def antenna_off(self):
        self.clear_bitmask(self.TxControlReg, 0x03)

    def to_card(self, command, send_data):
        back_data = []
        back_len = 0
        status = self.ERR
        irq_en = 0x00
        wait_irq = 0x00

        if command == self.CMD_MF_AUTHENT:
            irq_en = 0x12
            wait_irq = 0x10
        elif command == self.CMD_TRANSCEIVE:
            irq_en = 0x77
            wait_irq = 0x30

        self.write_register(self.ComIEnReg, irq_en | 0x80)
        self.clear_bitmask(self.ComIrqReg, 0x80)
        self.set_bitmask(self.FIFOLevelReg, 0x80)
        self.write_register(self.CommandReg, self.CMD_IDLE)

        for i in range(len(send_data)):
            self.write_register(self.FIFODataReg, send_data[i])

        self.write_register(self.CommandReg, command)

        if command == self.CMD_TRANSCEIVE:
            self.set_bitmask(self.BitFramingReg, 0x80)

        i = 1000
        while True:
            n = self.read_register(self.ComIrqReg)
            i -= 1
            if not ((i != 0) and not (n & 0x01) and not (n & wait_irq)):
                break
            time.sleep_us(100)

        self.clear_bitmask(self.BitFramingReg, 0x80)

        if i != 0:
            if (self.read_register(self.ErrorReg) & 0x1B) == 0x00:
                status = self.OK
                if n & irq_en & 0x01:
                    status = self.NOTAGERR
                elif command == self.CMD_TRANSCEIVE:
                    n = self.read_register(self.FIFOLevelReg)
                    last_bits = self.read_register(self.ControlReg) & 0x07
                    if last_bits != 0:
                        back_len = (n - 1) * 8 + last_bits
                    else:
                        back_len = n * 8
                    if n > 16:
                        n = 16
                    for i in range(n):
                        back_data.append(self.read_register(self.FIFODataReg))

        return (status, back_data, back_len)

    def request(self, req_mode):
        self.write_register(self.BitFramingReg, 0x07)
        (status, _, back_bits) = self.to_card(self.CMD_TRANSCEIVE, [req_mode])
        if (status != self.OK) or (back_bits != 0x10):
            status = self.ERR
        return (status, back_bits)

    def anticoll(self):
        self.write_register(self.BitFramingReg, 0x00)
        (status, back_data, _) = self.to_card(self.CMD_TRANSCEIVE, [0x93, 0x20])
        if status == self.OK and len(back_data) == 5:
            checksum = 0
            for i in range(4):
                checksum ^= back_data[i]
            if checksum != back_data[4]:
                status = self.ERR
        return (status, back_data)

    def calculate_crc(self, data):
        self.clear_bitmask(self.DivIrqReg, 0x04)
        self.set_bitmask(self.FIFOLevelReg, 0x80)
        for b in data:
            self.write_register(self.FIFODataReg, b)
        self.write_register(self.CommandReg, self.CMD_CALC_CRC)
        i = 255
        while i:
            n = self.read_register(self.DivIrqReg)
            if n & 0x04:
                break
            i -= 1
            time.sleep_ms(1)
        crcL = self.read_register(self.CRCResultRegL)
        crcH = self.read_register(self.CRCResultRegH)
        return [crcL, crcH]

    def select_tag(self, serial):
        buffer = [0x93, 0x70] + serial[:5]
        crc = self.calculate_crc(buffer)
        buffer += crc
        (status, _, _) = self.to_card(self.CMD_TRANSCEIVE, buffer)
        return self.OK if status == self.OK else self.ERR

    def authenticate(self, auth_type, block_addr, key, uid):
        buffer = [auth_type, block_addr] + key[:6] + uid[:4]
        (status, _, _) = self.to_card(self.CMD_MF_AUTHENT, buffer)
        return status

    def stop_crypto(self):
        self.clear_bitmask(self.Status2Reg, 0x08)

    def read_block(self, block_addr, key=None, key_type='A', uid=None):
        if key is None:
            need_auth = False
        else:
            need_auth = True
            if uid is None:
                uid = self.read_uid()
                if not uid:
                    return None

        if need_auth:
            auth_type = self.AUTHENT1A if key_type == 'A' else self.AUTHENT1B
            if self.authenticate(auth_type, block_addr, key, uid) != self.OK:
                print(f"Ошибка аутентификации блока {block_addr}")
                return None

        cmd = [0x30, block_addr]
        cmd += self.calculate_crc(cmd)
        (status, back_data, _) = self.to_card(self.CMD_TRANSCEIVE, cmd)

        if need_auth:
            self.stop_crypto()

        if status == self.OK and len(back_data) >= 4:
            return back_data[:4]
        return None

    def get_version(self):
        return self.read_register(self.VersionReg)

    def read_uid(self):
        current_time = time.ticks_ms()
        (status, _) = self.request(self.REQIDL)
        if status != self.OK:
            return None
        (status, uid_data) = self.anticoll()
        if status != self.OK or not uid_data:
            return None
        if (self.last_uid == uid_data and
            time.ticks_diff(current_time, self.last_time) < self.debounce_time):
            return None
        self.last_uid = uid_data
        self.last_time = current_time
        return uid_data[:4]

    def read_ntag_with_key(self, key_hex=None, key_type='A', uid=None):
        if uid is None:
            uid = self.read_uid()
        if not uid:
            return False, None, None, None

        uid_with_crc = uid + [uid[0] ^ uid[1] ^ uid[2] ^ uid[3]]
        if self.select_tag(uid_with_crc) != self.OK:
            print("[DEBUG] Ошибка выбора метки")
            return True, uid, None, None

        all_data = {}
        for page in range(0, 36):
            data = self.read_block(page, key=None, key_type=key_type, uid=uid)
            if data:
                all_data[page] = data
            else:
                all_data[page] = [0, 0, 0, 0]
        user_data = {p: all_data[p] for p in range(4, 36)}
        return True, uid, all_data, user_data

    def format_uid(self, uid):
        if not uid:
            return ""
        return ''.join('{:02X}'.format(b) for b in uid)

    def parse_ntag_data(self, all_data):
        if not all_data:
            return {}
        result = {
            'system_data': {p: all_data[p] for p in range(0,4) if p in all_data},
            'user_data': {p: all_data[p] for p in range(4,36) if p in all_data},
            'raw_text': '',
            'hex_data': ''
        }
        result['raw_text'] = self.extract_text_from_data(result['user_data'])
        result['hex_data'] = self.data_to_hex(result['user_data'])
        return result

    def extract_text_from_data(self, user_data):
        if not user_data:
            return ""
        all_bytes = bytearray()
        for page in sorted(user_data.keys()):
            all_bytes.extend(user_data[page])
        # Ищем начало текстовой NDEF-записи
        for i in range(len(all_bytes) - 4):
            if all_bytes[i] == 0x54:
                # Пропускаем 3 служебных байта (флаги + длина языка + первый символ языка)
                text_start = i + 4
                text_end = text_start
                while text_end < len(all_bytes) and all_bytes[text_end] != 0xFE:
                    text_end += 1
                if text_end > text_start:
                    try:
                        return all_bytes[text_start:text_end].decode('utf-8')
                    except:
                        return ""
        return ""

    def data_to_hex(self, user_data):
        if not user_data:
            return ""
        all_bytes = bytearray()
        for page in sorted(user_data.keys()):
            all_bytes.extend(user_data[page])
        hex_str = ""
        for i, byte in enumerate(all_bytes):
            if i > 0 and i % 16 == 0:
                hex_str += "\n"
            hex_str += f"{byte:02X} "
        return hex_str.strip()

    def print_ntag_info(self, uid, parsed_data):
        if not uid or not parsed_data:
            return
        uid_str = self.format_uid(uid)
        print("\n" + "="*60)
        print(f"NTAG213 МЕТКА")
        print("="*60)
        print(f"UID: {uid_str}")
        print(f"Время: {time.ticks_ms()} мс")
        print("-"*60)
        print("СИСТЕМНЫЕ ДАННЫЕ:")
        for page, data in sorted(parsed_data['system_data'].items()):
            hex_str = ' '.join([f'{b:02X}' for b in data])
            ascii_str = ''.join([chr(b) if 32 <= b < 127 else '.' for b in data])
            print(f"  Страница {page:2d}: {hex_str}  |  {ascii_str}")
        print("\nПОЛЬЗОВАТЕЛЬСКИЕ ДАННЫЕ:")
        for page, data in sorted(parsed_data['user_data'].items()):
            hex_str = ' '.join([f'{b:02X}' for b in data])
            ascii_str = ''.join([chr(b) if 32 <= b < 127 else '.' for b in data])
            print(f"  Страница {page:2d}: {hex_str}  |  {ascii_str}")
        if parsed_data['raw_text']:
            print(f"\nТЕКСТОВЫЕ ДАННЫЕ:\n  {parsed_data['raw_text']}")
        if parsed_data['hex_data']:
            print(f"\nHEX ДАННЫЕ:\n  {parsed_data['hex_data']}")
        print("="*60)

    def test_keys(self, uid):
        print("Тестирование ключей не требуется для открытых NTAG")
        return None