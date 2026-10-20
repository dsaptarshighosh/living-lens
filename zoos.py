"""Shared zoo choices used by registration and observation reports."""

ZOOS = [
    {"name": "Alipore Zoological Garden", "place": "Kolkata, West Bengal"},
    {"name": "Padmaja Naidu Himalayan Zoological Park", "place": "Darjeeling, West Bengal"},
    {"name": "North Bengal Wild Animals Park (Bengal Safari)", "place": "Siliguri, West Bengal"},
    {"name": "Tata Steel Zoological Park", "place": "Jamshedpur, Jharkhand"},
    {"name": "Bhagwan Birsa Biological Park", "place": "Ranchi, Jharkhand"},
    {"name": "Nandankanan Zoological Park", "place": "Bhubaneswar, Odisha"},
]

ZOO_NAMES = {z["name"] for z in ZOOS}
