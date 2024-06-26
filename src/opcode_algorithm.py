from scapy.layers.inet import UDP, TCP
import logging
from scapy.all import PcapReader
from src.utils import group_conversations, print_summary

# fingerprint packets in pcap files
def fingerprint_packets(file, conversations=None, params={}, printer=lambda x : x):
    if conversations is None:
        packets = PcapReader(file)
        conversations = group_conversations(packets)

    results = {}
    for key, packets_in_conversation in conversations.items():
        opcodes = find_opcodes(packets_in_conversation)
        opcode_result = opcode_fingerprinting(opcodes, params=params)

        results[key] = opcode_result

    print_summary(file, conversations, [(k,tuple([v])) for k,v in results.items()], printer=printer, algorithm_labels=["opcode"])

    return results

def find_opcodes(packets):
    opcodes = []
    for packet in packets:
        payload_location = 0
        payload = None
        try:
            if UDP in packet:
                # application data packets
                packet_udp:UDP = packet[UDP]
                payload = bytes(packet_udp.payload)
            if TCP in packet:
                payload_location = 2
                packet_tcp:TCP = packet[TCP]
                payload = bytes(packet_tcp.payload)
        except Exception as e:
            logging.error(f"Could not read package: {e}")
            continue

        if payload is None or len(payload) < payload_location + 1:
            continue

        opcode = (payload[payload_location] & 0b11111000) >> 3
        opcodes.append(opcode)
    return opcodes

XOR_OPCODES_KEY = "xor_opcodes"
def opcode_fingerprinting(opcodes, params=None):
    if params is None:
        params = {}
    # opcodes is a list of different opcodes
    if len(opcodes) < 2:
        return False
    CR=opcodes[0]
    SR=opcodes[1]

    if XOR_OPCODES_KEY in params and params[XOR_OPCODES_KEY] and not CR ^ SR in [1^2, 7^8]:
        return False

    OCSet=set([SR,CR])
    for opcode in opcodes:
        if opcode in [CR, SR] and len(OCSet)>=4:
            return False
        OCSet.add(opcode)
    return 4 <= len(OCSet) <= 10
