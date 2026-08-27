"""Payment gateway integrations — one module per gateway.

Each module exposes ``initiate(payment) -> dict`` (the redirect/form data the
frontend needs to start payment) and ``verify(payload) -> bool`` (whether a
callback payload is a genuine, successful confirmation from that gateway).
"""
