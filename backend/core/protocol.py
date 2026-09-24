START_BYTE = 0xC3
STOP_BYTE = 0xDB
DEFAULT_ADDRESS = 175  # 0xAF


def build_packet(cmd: int, data_bytes: list[int], address: int = DEFAULT_ADDRESS) -> bytes:
    """
    Returns: [C3][C3][Len][Addr][Cmd][Data][CRC_H][CRC_L][DB][DB]
    """
    crc_data = [address, cmd] + data_bytes
    crc_val = sum(crc_data)

    crc_msb = (crc_val >> 8) & 0xFF
    crc_lsb = crc_val & 0xFF

    length = 1 + 1 + len(data_bytes) + 2  # Addr + Cmd + Data + CRC(2)

    packet = [START_BYTE, START_BYTE, length] + crc_data + [crc_msb, crc_lsb, STOP_BYTE, STOP_BYTE]
    return bytes(packet)
