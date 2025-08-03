from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp, icmp, arp

HIGH_QUEUE = 1
LOW_QUEUE = 0
EF_DSCP = 46
PRIO_TCP_PORT = 5001

class DSCPQoS(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst
        )
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        ofproto = dp.ofproto
        parser = dp.ofproto_parser
        print("[+] Installing base flow rules")

        # --- High-priority VoIP rule (TCP dst 5001) ---
        match_voip = parser.OFPMatch(
            eth_type=0x0800,
            ip_proto=6,
            tcp_dst=PRIO_TCP_PORT
        )
        actions_voip = [
            parser.OFPActionSetField(ip_dscp=EF_DSCP),
            parser.OFPActionSetQueue(HIGH_QUEUE),
            parser.OFPActionOutput(ofproto.OFPP_NORMAL)
        ]
        self.add_flow(dp, 100, match_voip, actions_voip)
        print("[+] High-priority VoIP rule installed")

        # --- Generic TCP (bulk traffic like iperf3) ---
        match_tcp_out = parser.OFPMatch(
            in_port=1,
            eth_type=0x0800,
            ip_proto=6
        )
        actions_tcp_out = [
            parser.OFPActionSetQueue(LOW_QUEUE),
            parser.OFPActionOutput(2)
        ]
        self.add_flow(dp, 50, match_tcp_out, actions_tcp_out)
        print("[+] Bulk TCP h1-h2 rule installed")

        match_tcp_in = parser.OFPMatch(
            in_port=2,
            eth_type=0x0800,
            ip_proto=6
        )
        actions_tcp_in = [
            parser.OFPActionSetQueue(LOW_QUEUE),
            parser.OFPActionOutput(1)
        ]
        self.add_flow(dp, 50, match_tcp_in, actions_tcp_in)
        print("[+] Bulk TCP h2-h1 rule installed")

        # --- ICMP (ping) ---
        match_icmp = parser.OFPMatch(eth_type=0x0800, ip_proto=1)
        actions_icmp = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self.add_flow(dp, 900, match_icmp, actions_icmp)
        print("[+] ICMP rule installed")

        # --- ARP ---
        match_arp = parser.OFPMatch(eth_type=0x0806)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self.add_flow(dp, 1000, match_arp, actions_arp)
        print("[+] ARP rule installed")

        # --- Catch-all IPv4 (low queue fallback) ---
        match_ipv4_out = parser.OFPMatch(
            in_port=1,
            eth_type=0x0800
        )
        actions_ipv4_out = [
            parser.OFPActionSetQueue(LOW_QUEUE),
            parser.OFPActionOutput(2)
        ]
        self.add_flow(dp, 1, match_ipv4_out, actions_ipv4_out)

        match_ipv4_in = parser.OFPMatch(
            in_port=2,
            eth_type=0x0800
        )
        actions_ipv4_in = [
            parser.OFPActionSetQueue(LOW_QUEUE),
            parser.OFPActionOutput(1)
        ]
        self.add_flow(dp, 1, match_ipv4_in, actions_ipv4_in)
        print("[+] Catch-all IPv4 fallback rules installed")
