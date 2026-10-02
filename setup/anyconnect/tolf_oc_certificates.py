"""Certificate authority for personal TOLF AnyConnect devices (UK only)."""
import datetime as dt
import os
from pathlib import Path
import secrets
import string
import shutil
import tempfile
import uuid

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID


def now():
    return dt.datetime.now(dt.timezone.utc)


def private_write(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def initialize(directory):
    """Create once; an incomplete or mismatched authority is never replaced."""
    directory = Path(directory)
    if directory.exists():
        authority = Authority(directory)
        return authority.fingerprint
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".oc-ca-", dir=directory.parent))
    try:
        password = secrets.token_bytes(48)
        key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        subject = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "TOLF"),
            x509.NameAttribute(NameOID.COMMON_NAME, "TOLF AnyConnect Device CA"),
        ])
        created = now()
        cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
                .public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(created - dt.timedelta(minutes=5))
                .not_valid_after(created + dt.timedelta(days=3650))
                .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
                .add_extension(x509.KeyUsage(
                    digital_signature=True, content_commitment=False, key_encipherment=False,
                    data_encipherment=False, key_agreement=False, key_cert_sign=True,
                    crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
                .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)
                .sign(key, hashes.SHA256()))
        private_write(staging / "key-password.bin", password)
        private_write(staging / "ca-key.pem", key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(password)))
        private_write(staging / "ca.pem", cert.public_bytes(serialization.Encoding.PEM))
        authority = Authority(staging)
        private_write(staging / "ca.crl.pem", authority.crl([]))
        # A concurrent initializer must not replace an existing CA.
        os.rename(staging, directory)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return Authority(directory).fingerprint


class Authority:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.password = (self.directory / "key-password.bin").read_bytes()
        self.key = serialization.load_pem_private_key(
            (self.directory / "ca-key.pem").read_bytes(), self.password)
        self.cert = x509.load_pem_x509_certificate((self.directory / "ca.pem").read_bytes())
        if self.cert.public_key().public_numbers() != self.key.public_key().public_numbers():
            raise RuntimeError("AnyConnect CA key does not match its certificate")
        if not self.cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise RuntimeError("AnyConnect authority is not a CA")
        if self.cert.not_valid_after_utc <= now():
            raise RuntimeError("AnyConnect CA expired")

    @property
    def fingerprint(self):
        return self.cert.fingerprint(hashes.SHA256()).hex()

    def issue(self, device_id, days=365):
        device_id = uuid.UUID(device_id).hex
        if not isinstance(days, int) or not 1 <= days <= 365:
            raise ValueError("Invalid certificate lifetime")
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        created = now()
        expires = min(created + dt.timedelta(days=days), self.cert.not_valid_after_utc)
        if expires <= created + dt.timedelta(days=1):
            raise RuntimeError("AnyConnect CA needs renewal")
        cn = "tolf-oc-" + device_id
        cert = (x509.CertificateBuilder()
                .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)]))
                .issuer_name(self.cert.subject).public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(created - dt.timedelta(minutes=5)).not_valid_after(expires)
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .add_extension(x509.KeyUsage(
                    digital_signature=True, content_commitment=False, key_encipherment=True,
                    data_encipherment=False, key_agreement=False, key_cert_sign=False,
                    crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), False)
                .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)
                .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(self.key.public_key()), False)
                .sign(self.key, hashes.SHA256()))
        return {
            "username": cn, "serial": format(cert.serial_number, "x"),
            "created_at": created.isoformat(), "expires_at": expires.isoformat(),
            "certificate": cert.public_bytes(serialization.Encoding.PEM),
            "encrypted_key": key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                serialization.BestAvailableEncryption(self.password)),
        }

    def bundle(self, record):
        key = serialization.load_pem_private_key(record["encrypted_key"], self.password)
        cert = x509.load_pem_x509_certificate(record["certificate"])
        if key.public_key().public_numbers() != cert.public_key().public_numbers():
            raise RuntimeError("Device certificate does not match its key")
        alphabet = string.ascii_letters + string.digits
        while True:
            password = "".join(secrets.choice(alphabet) for _ in range(8))
            if (any(c.isupper() for c in password) and any(c.islower() for c in password)
                    and any(c.isdigit() for c in password)):
                break
        data = pkcs12.serialize_key_and_certificates(
            record["username"].encode("ascii"), key, cert, [self.cert],
            serialization.BestAvailableEncryption(password.encode("ascii")))
        return data, password

    def crl(self, revoked, number=1):
        created = now()
        builder = (x509.CertificateRevocationListBuilder().issuer_name(self.cert.subject)
                   .last_update(created - dt.timedelta(minutes=1))
                   .next_update(created + dt.timedelta(days=7))
                   .add_extension(x509.CRLNumber(number), False)
                   .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(
                       self.key.public_key()), False))
        for serial, revoked_at in revoked:
            entry = (x509.RevokedCertificateBuilder().serial_number(int(serial, 16))
                     .revocation_date(revoked_at).build())
            builder = builder.add_revoked_certificate(entry)
        return builder.sign(self.key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM)
