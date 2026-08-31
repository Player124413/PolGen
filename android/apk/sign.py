#!/usr/bin/env python3
"""Подпись APK схемой v1 (JAR signing) на чистом Python.

Зависимость: pip install cryptography

Использование:
    python3 sign.py input-unsigned.apk output.apk [ключ.pem]

Если PEM-файла с ключом нет — он создаётся (RSA-2048, self-signed) и
сохраняется рядом, чтобы будущие версии APK подписывались той же подписью
(иначе Android потребует удалить старое приложение перед обновлением).

Почему v1: APK с targetSdkVersion < 30 корректно устанавливается на всех
версиях Android (7–15+) только с v1-подписью. Для публикации в Google Play
нужна v2+ и targetSdk 34 — этот лаунчер предназначен для прямой установки.
"""

import base64
import hashlib
import sys
import zipfile

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509.oid import NameOID


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


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    key_path = sys.argv[3] if len(sys.argv) > 3 else "polgen-launcher-key.pem"
    key, cert = load_or_create_key(key_path)

    with zipfile.ZipFile(src) as zin:
        entries = [(i.filename, zin.read(i.filename)) for i in zin.infolist() if not i.is_dir()]

    # ---- MANIFEST.MF: дайджесты всех файлов кроме META-INF ----
    manifest = "Manifest-Version: 1.0\r\nCreated-By: PolGen build\r\n\r\n"
    sections = {}
    for name, data in entries:
        if name.startswith("META-INF/"):
            continue
        sec = f"Name: {name}\r\nSHA-256-Digest: {digest_b64(data)}\r\n\r\n"
        sections[name] = sec
        manifest += sec
    manifest_bytes = manifest.encode("utf-8")

    # ---- CERT.SF: дайджест манифеста и дайджесты секций манифеста ----
    sf = (
        "Signature-Version: 1.0\r\nCreated-By: PolGen build\r\n"
        f"SHA-256-Digest-Manifest: {digest_b64(manifest_bytes)}\r\n\r\n"
    )
    for name, sec in sections.items():
        sf += f"Name: {name}\r\nSHA-256-Digest: {digest_b64(sec.encode('utf-8'))}\r\n\r\n"
    sf_bytes = sf.encode("utf-8")

    # ---- CERT.RSA: отсоединённая PKCS#7 (CMS) подпись CERT.SF ----
    signature = (
        pkcs7.PKCS7SignatureBuilder()
        .set_data(sf_bytes)
        .add_signer(cert, key, hashes.SHA256())
        .sign(
            serialization.Encoding.DER,
            options=[pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.Binary],
        )
    )

    # ---- итоговый APK: все файлы DEFLATE (выравнивание не требуется при targetSdk<30) ----
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in entries:
            zout.writestr(name, data)
        zout.writestr("META-INF/MANIFEST.MF", manifest_bytes)
        zout.writestr("META-INF/CERT.SF", sf_bytes)
        zout.writestr("META-INF/CERT.RSA", signature)

    print(f"Подписано: {dst} ({len(entries)} файлов, SHA-256, v1)")


if __name__ == "__main__":
    main()
