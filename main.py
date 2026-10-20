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

print("Laptop image size:", len(laptop_bytes), "bytes")
laptop_bits = (len(laptop_bytes) + 9) * 8
laptop_percentage = (laptop_bits / 151875) * 100
print("Laptop percentage:", laptop_percentage, "%")

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

#Task 2
def bits_to_bytes(bits):
    while len(bits) % 8 != 0:
        bits.append(0)
    out = bytearray()

    for i in range(0, len(bits), 8):
        byte = 0
        for bit in bits[i:i+8]:
            byte = (byte << 1) | int(bit)
        out.append(byte)

    return bytes(out)

def extract(stego_path, password):
    image = Image.open(stego_path).convert("RGB")
    arr = np.array(image)

    H, W, _ = arr.shape
    total_channels = H * W * 3

    rng = np.random.default_rng(seed_from_password(password))
    perm = rng.permutation(total_channels)

    bits = []
    header_seen = False

    for i in range(total_channels):
        channel_pos = perm[i]

        pixel = channel_pos // 3
        ch = channel_pos % 3

        y = pixel // W
        x = pixel % W

        bit = int(arr[y, x, ch]) & 1
        bits.append(bit)

        if len(bits) == 72:
            header = bits_to_bytes(bits)
            if header[:4] != b"STEG":
                print("No payload found. Wrong password?")
                return None, None
            
            payload_type = "text" if header[4] == 0 else "image"
            length = int.from_bytes(header[5:9], "big")
            total_bits_needed = (9 + length) * 8

            if total_bits_needed > total_channels:
                print("Invalid payload length.")
                return None, None
            header_seen = True

        if header_seen and len(bits) >= total_bits_needed:
            break

    if not header_seen or len(bits) < total_bits_needed:
        print("Incomplete payload.")
        return None, None

    payload_bytes = bits_to_bytes(bits[72:72 + length * 8])

    if payload_type == "text":
        return "text", payload_bytes.decode("utf-8")
    else:
        return "image", payload_bytes

# Recover hidden text
print("\nExtracting hidden text...")
payload_type, data = extract("stego_text.png", "secret")

if payload_type == "text":
    print("Recovered text:", data)

#Recover hidden laptop image
print("\nExtracting hidden laptop image...")

payload_type, data = extract("stego_laptop.png", "secret")

if payload_type == "image":
    recovered_image = Image.open(BytesIO(data))
    recovered_image.save("recovered_laptop.png")
    recovered_image.show()

    print("Laptop image recovered successfully!")

#Wrong password
print("\nTesting incorrect password...")
payload_type, data = extract("stego_text.png", "wrongpassword")
print("Wrong password result:", payload_type, data)
