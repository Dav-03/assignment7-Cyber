import hashlib
from io import BytesIO
import numpy as np
from PIL import Image

def seed_from_password(password):
    h = hashlib.sha256(password.encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big")


def capacity_bytes(height, width, channels=3):
    return (height * width * channels) // 8


def bytes_to_bits(data):
    bits = []

    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)

    return bits


def frame_payload(payload_type, payload_bytes):
    magic = b"STEG"

    if payload_type == "text":
        type_byte = b"\x00"
    elif payload_type == "image":
        type_byte = b"\x01"
    else:
        raise ValueError("type must be text or image")

    length = len(payload_bytes).to_bytes(4, "big")

    return magic + type_byte + length + payload_bytes


def embed(cover_path, out_path, payload_type, payload_bytes, password):
    with Image.open(cover_path) as image:
        arr = np.array(image.convert("RGB"))

    height, width, _ = arr.shape
    total_channels = height * width * 3

    framed = frame_payload(payload_type, payload_bytes)
    bits = bytes_to_bits(framed)

    if len(bits) > total_channels:
        raise ValueError("payload too large for this cover")

    rng = np.random.default_rng(seed_from_password(password))
    perm = rng.permutation(total_channels)

    out = arr.copy()

    for i in range(len(bits)):
        channel_pos = int(perm[i])

        pixel = channel_pos // 3
        ch = channel_pos % 3
        y = pixel // width
        x = pixel % width

        out[y, x, ch] = (int(out[y, x, ch]) & 0xFE) | bits[i]

    Image.fromarray(out).save(out_path, format="PNG")
    print(f"created {out_path}")


message = "This is a secret".encode("utf-8")

embed(
    "apple_logo_cover.png",
    "stego_text.png",
    "text",
    message,
    "secret"
)

with Image.open("laptop_secret.png") as laptop:
    buffer = BytesIO()
    laptop.save(buffer, format="PNG")
    laptop_bytes = buffer.getvalue()

embed(
    "apple_logo_cover.png",
    "stego_laptop.png",
    "image",
    laptop_bytes,
    "secret"
)

with Image.open("apple_logo_cover.png") as cover:
    width, height = cover.size

max_payload = capacity_bytes(height, width) - 9
oversized_payload = b"A" * (max_payload + 1)

try:
    embed(
        "apple_logo_cover.png",
        "oversized.png",
        "text",
        oversized_payload,
        "secret"
    )
except ValueError as error:
    print("Payload is too large: ", error)
else:
    print("ERROR: oversized payload was not rejected")

    