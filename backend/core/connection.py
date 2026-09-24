import serial
import time

RESPONSE_TYPES = {
    0: "OK",
    1: "PACKET_ERROR",
    2: "CRC_ERROR",
    3: "DATA_ERROR",
    4: "FIFO_ERROR",
    5: "POWER_ERROR",
    6: "BATTERY_ERROR",
    7: "LOG_NOT_EXISTS",
    8: "TEAM_NOT_EXISTS",
    9: "SPONSOR_NOT_EXISTS",
    16: "LIST_IS_EMPTY",
    17: "PLAYER_NOT_EXISTS"
}


class MockConnection:
    """For local testing"""

    def __init__(self):
        self.is_open = True

    def write(self, data: bytes, timeout: float = 2.0):
        hex_data = " ".join([f"{b:02X}" for b in data])
        return f"[MOCK TX] {hex_data}"

    def close(self):
        self.is_open = False


class SerialConnection:
    """For real serial communication"""

    def __init__(self, port: str, baudrate: int = 9600):
        self.ser = serial.Serial(port, baudrate, timeout=1)
        self.is_open = self.ser.is_open

    def write(self, data: bytes, timeout: float = 5.0):
        self.ser.reset_input_buffer()
        self.ser.write(data)
        self.ser.flush()

        expected_cmd = data[4] if len(data) > 4 else None
        expected_resp_cmd = (expected_cmd + 0x80) & 0xFF if expected_cmd else None
        hex_data = " ".join([f"{b:02X}" for b in data])
        log_msg = f"[TX] {hex_data}"

        start_time = time.time()
        response_bytes = bytearray()

        while time.time() - start_time < timeout:
            if self.ser.in_waiting > 0:
                response_bytes.extend(self.ser.read(self.ser.in_waiting))

                while b'\xc3\xc3' in response_bytes:
                    start_idx = response_bytes.find(b'\xc3\xc3')
                    if start_idx > 0:
                        discarded = response_bytes[:start_idx]
                        print(f"[RX GARBAGE] {' '.join([f'{b:02X}' for b in discarded])}")
                        response_bytes = response_bytes[start_idx:]

                    # Packet needs to be 9 bytes long
                    if len(response_bytes) < 9:
                        break

                    pkt_len = response_bytes[2]
                    expected_total_len = 3 + pkt_len + 2

                    if expected_total_len < 9 or expected_total_len > 255:
                        print(f"[RX INVALID LEN] Invalid packet length detected: {expected_total_len}")
                        response_bytes = response_bytes[2:]
                        continue

                    if len(response_bytes) >= expected_total_len:
                        packet = response_bytes[:expected_total_len]

                        if packet[-2:] == b'\xdb\xdb':
                            response_bytes = response_bytes[expected_total_len:]
                            rx_cmd = packet[4] if pkt_len >= 2 else None

                            if rx_cmd == expected_cmd:
                                continue

                            if rx_cmd == expected_resp_cmd:
                                hex_resp = " ".join([f"{b:02X}" for b in packet])
                                status_byte = packet[5] if pkt_len >= 3 else 0xFF

                                # Try to get status name
                                status_name = RESPONSE_TYPES.get(status_byte, f"UNKNOWN_ERROR_0x{status_byte:02X}")

                                # 0x00 means OK
                                if status_byte == 0x00:
                                    return True, status_byte, f"{log_msg}\n[RX] {hex_resp} (OK)"
                                else:
                                    return False, status_byte, f"{log_msg}\n[RX ERROR] {hex_resp} ({status_name})"

                            continue
                        else:
                            hex_err = " ".join([f"{b:02X}" for b in packet])
                            print(f"[RX MALFORMED] Malformed ending of packet payload (missing DB DB): {hex_err}")
                            response_bytes = response_bytes[2:]
                    else:
                        break
            else:
                time.sleep(0.005)

        if response_bytes:
            hex_resp = " ".join([f"{b:02X}" for b in response_bytes])
            return False, 0xFF, f"{log_msg}\n[RX INCOMPLETE] {hex_resp} (Timeout)"

        return False, 0xFF, f"{log_msg}\n[RX] TIMEOUT - No response."

    def close(self):
        self.ser.close()
        self.is_open = False
