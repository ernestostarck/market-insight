#!/usr/bin/env python3
"""Cross-platform TLS Certificate Generator for Development & Staging.

Generates self-signed TLS certificates (fullchain.pem and privkey.pem) with
proper Subject Alternative Names (SAN) for local development, docker testing,
and staging environments.

Usage:
    python generate-dev-certs.py
    python generate-dev-certs.py --output-dir docker/nginx/certs --domain mercadoinsight.cl
"""

import argparse
import datetime
import ipaddress
import sys
from pathlib import Path

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
except ImportError:
    print(
        "[ERROR] 'cryptography' package is required. Install with: pip install cryptography",
        file=sys.stderr,
    )
    sys.exit(1)


def generate_self_signed_certificate(
    output_dir: Path,
    domain: str = "mercadoinsight.cl",
    valid_days: int = 365,
) -> tuple[Path, Path]:
    """Generate private key and self-signed X.509 certificate."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cert_path = output_dir / "fullchain.pem"
    key_path = output_dir / "privkey.pem"

    print(f"Generating 2048-bit RSA private key...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Subject and Issuer
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CL"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Santiago"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Santiago"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MercadoInsight"),
        x509.NameAttribute(NameOID.COMMON_NAME, domain),
    ])

    # Subject Alternative Names (SAN)
    san_list = [
        x509.DNSName(domain),
        x509.DNSName(f"www.{domain}"),
        x509.DNSName(f"staging.{domain}"),
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
    ]

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=valid_days))
        .add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )

    # Write private key
    with open(key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    # Write certificate
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"[SUCCESS] Certificate created at: {cert_path}")
    print(f"[SUCCESS] Private key created at: {key_path}")
    print(f"Valid for domains: {[str(san.value) for san in san_list]}")
    return cert_path, key_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate self-signed TLS certificates for development/staging.")
    parser.add_argument("--output-dir", type=Path, default=Path("docker/nginx/certs"),
                        help="Directory to save fullchain.pem and privkey.pem")
    parser.add_argument("--domain", default="mercadoinsight.cl",
                        help="Primary common name for certificate")
    parser.add_argument("--days", type=int, default=365,
                        help="Validity in days (default: 365)")

    args = parser.parse_args()
    generate_self_signed_certificate(
        output_dir=args.output_dir,
        domain=args.domain,
        valid_days=args.days,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
