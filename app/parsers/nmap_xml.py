from __future__ import annotations
from lxml import etree
from typing import Dict, Any
from ..schema import NmapSummary, Host

def parse_nmap_xml_text(xml_text: str) -> NmapSummary:
    try:
        root = etree.fromstring(xml_text.encode())
        hosts: list[Host] = []
        for h in root.findall("host"):
            addr = h.find("address[@addrtype='ipv4']")
            mac = h.find("address[@addrtype='mac']")
            hostnames = [hn.get("name") for hn in h.findall("hostnames/hostname") if hn.get("name")]
            hosts.append(
                Host(
                    ip=addr.get("addr") if addr is not None else None,
                    mac=mac.get("addr") if mac is not None else None,
                    hostnames=hostnames,
                )
            )
        return NmapSummary(hosts=hosts)
    except Exception:
        return NmapSummary()
