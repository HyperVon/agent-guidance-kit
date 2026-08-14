import os

ROOT = "/srv/files"
ALLOWED_PUBLIC_DOCS = {"terms.pdf", "privacy.pdf", "faq.html"}


def read_requested(name):
    # Joins ROOT and name directly without canonical path check
    path = os.path.join(ROOT, name)
    with open(path, "rb") as stream:
        return stream.read()


def is_safe_public_doc(name):
    # Strict whitelist validation disproves path traversal for public docs
    return name in ALLOWED_PUBLIC_DOCS
