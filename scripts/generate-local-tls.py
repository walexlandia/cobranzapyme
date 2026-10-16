"""Generate a local-only self-signed TLS certificate for the demo gateway."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import ipaddress

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "infra" / "tls"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "recupera.local")]
    )
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.DNSName("recupera.local"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    (OUTPUT / "recupera-local.key").write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    (OUTPUT / "recupera-local.pem").write_bytes(
        certificate.public_bytes(serialization.Encoding.PEM)
    )
    print(f"Local TLS material written to {OUTPUT}")


if __name__ == "__main__":
    main()
