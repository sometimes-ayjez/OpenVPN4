from scapy.all import rdpcap
from scapy.layers.inet import UDP, IP, TCP
# import cryptography
import opcode_algorithm
import ack_algorithm
import sys, tqdm
from openvpn_header import OpenVPN, OpenVPN

def get_key(packet):
    key = None
    if IP in packet:
        packet_ip = packet[IP]

        port_src = 0
        port_dst = 0
        if UDP in packet:
            port_src = packet[UDP].sport
            port_dst = packet[UDP].dport
        if TCP in packet:
            port_src = packet[TCP].sport
            port_dst = packet[TCP].dport

        key = [(packet_ip.src, port_src), (packet_ip.dst, port_dst)]
        key.sort(key=lambda k : k[0] + str(k[1]))
        key = tuple(key)

    return key

def group_conversations(packets):
    conversations = {}
    ids = {}
    for i, packet in enumerate(packets):
        key = get_key(packet)
        if key is None:
            continue
        if not key in conversations:
            conversations[key] = []
            ids[key] = i
        conversations[key].append(packet)
    
    conversations_with_id = {ids[key]:v for key, v in conversations.items()}
    return conversations, conversations_with_id

def find_opcodes(packets):
    opcodes = []
    for packet in packets:
        if UDP in packet:
            # application data packets
            packet_udp:UDP = packet[UDP]
            payload = bytes(packet_udp.payload)

            opcode = (payload[0] & 0b11111000) >> 3
            opcodes.append(opcode)
    return opcodes

def flag_openvpn_in_capture(filename):
    packets = rdpcap(filename)
    conversations, conversations_with_id = group_conversations(packets)

    results = {}
    for key, packets_in_conversation in conversations.items():
        opcodes = find_opcodes(packets_in_conversation)
        opcode_result = opcode_algorithm.opcode_fingerprinting(opcodes)
        ack_result = ack_algorithm.ack_fingerprinting(packets_in_conversation)
        results[key] = (opcode_result, ack_result)
    return results, conversations

def main(argv):
    files = [
        "pcap-dumps/mullvad-ovpn-bridge-mode.pcap",
        # "pcap-dumps/synthesized-openvpn-server-dump.pcap",
        # "pcap-dumps/non-vpn.pcap",
        # "pcap-dumps/email1a.pcap",
        # "pcap-dumps/vpn_skype_files1b.pcap",
        # "pcap-dumps/vpn_icq_chat1a.pcap",
        # "pcap-dumps/nonvpn_rdp_capture4.pcap",
        # "pcap-dumps/vpn_rdp_capture1.pcap",
        # "pcap-dumps/vpn_skype-chat_capture1.pcap",
    ]

    if len(argv) > 1:
        files = argv[1:]

    for file in files:
        results, conversations = flag_openvpn_in_capture(file)

        items = list(results.items())
        items.sort(key=lambda k : sum([int(v) for v in k[1]]))
        for (ip1, ip2), result in items:
            print(f"Flagged: {result[0]}\tIn conversation between {ip1} and {ip2}")
            
            print(f"ACK flag result: {result[1]}")
        
        print(f"############ Summary for file {file} ############")
        print(f"Found {len(conversations)} conversations")
        print(f"{len([v for v in items if v[1][0]])} flagged as VPN by the opcode algorithm")
        print(f"{len([v for v in items if v[1][1]])} flagged as VPN by the ACK algorithm")

if __name__ == "__main__":
    main(sys.argv)