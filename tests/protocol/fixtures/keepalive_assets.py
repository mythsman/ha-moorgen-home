"""Assets for docs/protocol/keepalive.md."""

# Gateway -> client ping, sent every ~10s.
PING_HEX = "231100646f6f79617368637001060d0000000023"
# Client -> gateway reply that keeps the socket open.
ACK_HEX = "231100646f6f79617368637001060e0000000023"
