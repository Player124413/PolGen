#!/usr/bin/env python3
"""Подпись APK схемами v1 (JAR) + v2 (APK Signature Scheme v2) на чистом Python.

Зависимость: pip install cryptography

Использование:
    python3 sign.py input-unsigned.apk output.apk [ключ.pem]

Почему обе схемы:
- v1-only APK современные прошивки (Android 11+, MIUI/HyperOS, One UI) часто
  отказываются устанавливать с ошибкой «Приложение не установлено»;
- v2 (Android 7.0+) подписывает весь файл целиком и проверяется первой;
- v1 оставлена как запасная для старых инструментов.

Дополнительно zip перезаписывается собственным райтером:
- resources.arsc хранится без сжатия (STORED) с выравниванием по 4 байта —
  требование Android 11+ (для targetSdk 30+; нам это просто запас прочности);
- остальные файлы DEFLATE.

Если PEM-файла с ключом нет — он создаётся (RSA-2048, self-signed) и
сохраняется рядом, чтобы будущие версии APK подписывались той же подписью
(иначе Android потребует удалить старое приложение перед обновлением).
"""

import base64
import hashlib
import struct
import sys
import zipfile
import zlib

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509.oid import NameOID

V2_BLOCK_ID = 0x7109871A
SIG_ALGO_RSA_PKCS1_SHA256 = 0x0103
CHUNK_SIZE = 1048576
MAGIC = b"APK Sig Block 42"

# файлы, которые в APK хранятся без сжатия и с выравниванием
STORED_ENTRIES = {"resources.arsc"}


def load_or_create_key(path):
    try:
        with open(path, "rb") as f:
            blob = f.read()
        key = serialization.load_pem_private_key(blob, password=None)
        cert = x509.load_pem_x509_certificate(blob)
        return key, cert
    except FileNotFoundError:
        pass

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "PolGen Launcher")])
    from datetime import datetime, timedelta, timezone

    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=36500))
        .sign(key, hashes.SHA256())
    )

    pem = (
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        + cert.public_bytes(serialization.Encoding.PEM)
    )
    with open(path, "wb") as f:
        f.write(pem)
    print(f"Создан новый ключ подписи: {path}")
    return key, cert


def digest_b64(data: bytes) -> str:
    return base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")


# ────────────────────────── v1 (JAR signing) ──────────────────────────

def build_v1_meta(entries, key, cert):
    """entries: [(name, data)] без META-INF. → {META-INF-имя: байты}."""
    manifest = "Manifest-Version: 1.0\r\nCreated-By: PolGen build\r\n\r\n"
    sections = {}
    for name, data in entries:
        if name.startswith("META-INF/"):
            continue
        sec = f"Name: {name}\r\nSHA-256-Digest: {digest_b64(data)}\r\n\r\n"
        sections[name] = sec
        manifest += sec
    manifest_bytes = manifest.encode("utf-8")

    sf = (
        "Signature-Version: 1.0\r\nCreated-By: PolGen build\r\n"
        f"SHA-256-Digest-Manifest: {digest_b64(manifest_bytes)}\r\n"
        "X-Android-APK-Signed: 2\r\n\r\n"
    )
    for name, sec in sections.items():
        sf += f"Name: {name}\r\nSHA-256-Digest: {digest_b64(sec.encode('utf-8'))}\r\n\r\n"
    sf_bytes = sf.encode("utf-8")

    signature = (
        pkcs7.PKCS7SignatureBuilder()
        .set_data(sf_bytes)
        .add_signer(cert, key, hashes.SHA256())
        .sign(
            serialization.Encoding.DER,
            options=[pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.Binary],
        )
    )
    return {
        "META-INF/MANIFEST.MF": manifest_bytes,
        "META-INF/CERT.SF": sf_bytes,
        "META-INF/CERT.RSA": signature,
    }


# ──────────────────────── zip-райтер с выравниванием ────────────────────────

def write_zip(path, entries):
    """entries: [(name, data, method, align)] → [локальные заголовки+данные][CD][EOCD]."""
    contents = bytearray()
    central = bytearray()
    for name, data, method, align in entries:
        offset = len(contents)
        crc = zlib.crc32(data) & 0xFFFFFFFF
        if method == 8:
            comp = zlib.compressobj(9, zlib.DEFLATED, -15)
            cdata = comp.compress(data) + comp.flush()
        else:
            cdata = data
        extra = b""
        if align > 1 and method == 0:
            data_off = offset + 30 + len(name)
            pad = (align - (data_off % align)) % align
            extra = b"\x00" * pad
        contents += struct.pack(
            "<IHHHHHIIIHH", 0x04034B50, 20, 0, method, 0, 0x5EE1,
            crc, len(cdata), len(data), len(name), len(extra),
        )
        contents += name.encode("ascii")
        contents += extra
        contents += cdata
        central += struct.pack(
            "<IHHHHHHIIIHHHHHII", 0x02014B50, (3 << 8) | 20, 20, 0, method, 0, 0x21,
            crc, len(cdata), len(data), len(name), 0, 0, 0, 0, 0, offset,
        )
        central += name.encode("ascii")

    cd_offset = len(contents)
    eocd = struct.pack(
        "<IHHHHIIH", 0x06054B50, 0, 0, len(entries), len(entries),
        len(central), cd_offset, 0,
    )
    with open(path, "wb") as f:
        f.write(bytes(contents))
        f.write(bytes(central))
        f.write(eocd)
    return bytes(contents), bytes(central), eocd


# ──────────────────────── v2 (APK Signature Scheme v2) ────────────────────────

def lp(data: bytes) -> bytes:
    """Поле с префиксом-длиной uint32 LE."""
    return struct.pack("<I", len(data)) + data


def chunk_digests(data: bytes):
    for i in range(0, len(data), CHUNK_SIZE):
        chunk = data[i:i + CHUNK_SIZE]
        yield hashlib.sha256(b"\xa5" + struct.pack("<I", len(chunk)) + chunk).digest()


def content_digest(contents: bytes, cd: bytes, eocd: bytes) -> bytes:
    digests = list(chunk_digests(contents)) + list(chunk_digests(cd)) + list(chunk_digests(eocd))
    return hashlib.sha256(b"\x5a" + struct.pack("<I", len(digests)) + b"".join(digests)).digest()


def build_v2_block(contents: bytes, cd: bytes, eocd: bytes, key, cert) -> bytes:
    digest = content_digest(contents, cd, eocd)

    # signed_data = lp(digests) + lp(certs) + lp(attrs); внутри каждой секции
    # записи тоже имеют префикс-длину (см. parse_signed_data/parse_digests)
    digest_entry = struct.pack("<II", SIG_ALGO_RSA_PKCS1_SHA256, len(digest)) + digest
    digests_field = lp(lp(digest_entry))
    certs_field = lp(lp(cert.public_bytes(serialization.Encoding.DER)))
    attrs_field = lp(b"")
    signed_data = digests_field + certs_field + attrs_field  # подпись — именно по этим байтам

    signature = key.sign(signed_data, padding.PKCS1v15(), hashes.SHA256())
    sig_entry = struct.pack("<II", SIG_ALGO_RSA_PKCS1_SHA256, len(signature)) + signature
    sigs_field = lp(lp(sig_entry))

    pubkey = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    signer = lp(signed_data) + sigs_field + lp(pubkey)
    # value блока = [длина секции] + конкатенация lp(signer);
    # т.е. seq_len-префикс + собственный lp-префикс подписанта
    v2_value = lp(lp(signer))

    pairs = struct.pack("<Q", 4 + len(v2_value)) + struct.pack("<I", V2_BLOCK_ID) + v2_value
    size = len(pairs) + 8 + 16  # пары + хвостовой size + magic (без первого size)
    return struct.pack("<Q", size) + pairs + struct.pack("<Q", size) + MAGIC


# ────────────────────────────── основной поток ──────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    key_path = sys.argv[3] if len(sys.argv) > 3 else "polgen-launcher-key.pem"
    key, cert = load_or_create_key(key_path)

    with zipfile.ZipFile(src) as zin:
        files = [(i.filename, zin.read(i.filename)) for i in zin.infolist() if not i.is_dir()]

    # v1: дайджесты всех файлов, кроме META-INF
    meta = build_v1_meta(files, key, cert)

    # итоговый список записей (v1-файлы в конце)
    entries = []
    for name, data in files:
        if name in STORED_ENTRIES:
            entries.append((name, data, 0, 4))       # STORED + выравнивание 4 байта
        else:
            entries.append((name, data, 8, 0))
    for name, data in meta.items():
        entries.append((name, data, 8, 0))

    unsigned_zip = dst + ".unsigned"
    contents, cd, eocd = write_zip(unsigned_zip, entries)

    # v2: блок вставляется между содержимым и Central Directory
    block = build_v2_block(contents, cd, eocd, key, cert)
    new_cd_offset = len(contents) + len(block)
    new_eocd = eocd[:16] + struct.pack("<I", new_cd_offset) + eocd[20:]

    with open(dst, "wb") as f:
        f.write(contents)
        f.write(block)
        f.write(cd)
        f.write(new_eocd)
    import os

    os.remove(unsigned_zip)

    print(f"Подписано: {dst}")
    print(f"  v1 (JAR, SHA-256): {len(files)} файлов")
    print(f"  v2 (APK Signature Scheme v2, RSA-2048/SHA-256): блок {len(block)} байт")
    print(f"  resources.arsc: STORED, выровнен по 4 байта")


if __name__ == "__main__":
    main()
