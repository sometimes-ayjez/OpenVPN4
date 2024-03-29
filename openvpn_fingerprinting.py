from scapy.all import PcapReader
from scapy.layers.inet import UDP, IP, TCP
# import cryptography
import opcode_algorithm
import ack_algorithm
from utils import group_conversations, print_summary
import sys, tqdm

def flag_openvpn_in_capture(filename, params={}):
    packets = PcapReader(filename)
    print(f"Reading file {filename}...")
    conversations, conversations_with_id = group_conversations(packets, progressbar=True)
    results_opcode = opcode_algorithm.fingerprint_packets(filename, conversations=conversations, params=params)
    results_ack = ack_algorithm.fingerprint_packets(filename, conversations=conversations, params=params)

    results = {}
    for key, packets_in_conversation in conversations.items():
        results[key] = (results_opcode[key], results_ack[key])

    return results, conversations


def main(argv):
    files = [
        # "docker-pcaps/udp.pcap",
        "docker-pcaps/tcp.pcap",
        "pcap-dumps/mullvad-ovpn-bridge-mode.pcap",
        "pcap-dumps/synthesized-openvpn-server-dump.pcap",
        "pcap-dumps/non-vpn.pcap",
    ]

    params = {}
    if "-o" in argv:
        i = argv.index("-o")
        params[opcode_algorithm.XOR_OPCODES_KEY] = True
        argv.pop(i)

    if len(argv) > 1:
        files = argv[1:]

    for file in files:
        results, conversations = flag_openvpn_in_capture(file, params=params)

        items = list(results.items())
        items.sort(key=lambda k : sum([int(v) for v in k[1]]))
        for (ip1, ip2), result in items:
            print(f"Flagged: {result[0]}\tIn conversation between {ip1} and {ip2}")
            
            print(f"ACK flag result: {result[1]}")
        
        print_summary(file, conversations, items)

if __name__ == "__main__":
    main(sys.argv)
