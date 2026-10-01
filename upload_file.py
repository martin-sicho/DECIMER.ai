#!/usr/bin/env python3
"""Run DECIMER OCSR on a single structure image and print the resolved SMILES.

OCSR is the last step of a three-stage server pipeline, each stage a CSRF-protected
Laravel web route that returns server-rendered HTML (not JSON). This script drives the
same flow a browser does, reusing one session and scraping the hidden form fields that
each stage hands to the next:

    1. GET  /file-upload            -> session cookie + CSRF token
    2. POST /file-upload (file[])   -> stores the image; response embeds img_paths +
                                       single_image_upload for the segmentation form
    3. POST /decimer-segmentation   -> detects structures; response embeds
                                       structure_depiction_img_paths for the OCSR form
    4. POST /decimer-ocsr           -> runs OCSR; response embeds smiles_array

Only the resolved SMILES are written to stdout, in the requested format.

Usage:
    python3 upload_file.py structure.png
    python3 upload_file.py structure.png --format csv
    python3 upload_file.py structure.png --format json --base-url http://localhost:8181/decimer
"""
import argparse
import csv
import html
import json
import os
import re
import sys

import requests

# Image formats the uploader accepts. PDF is intentionally excluded.
VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".heic"}

META_TOKEN_RE = re.compile(r'name="csrf-token"\s+content="([^"]+)"')
INPUT_TOKEN_RE = re.compile(r'name="_token"\s+value="([^"]+)"')


def hidden_field(markup, field_name):
    """Return the (HTML-unescaped) value of <input name="field_name" value="..."> or None."""
    pattern = re.compile(
        r'name="' + re.escape(field_name) + r'"[^>]*?\svalue="([^"]*)"',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(markup)
    return html.unescape(match.group(1)) if match else None


def get_csrf_token(session, base_url):
    """GET the upload page to obtain the session cookie + CSRF token."""
    resp = session.get(f"{base_url}/file-upload")
    resp.raise_for_status()
    for pattern in (META_TOKEN_RE, INPUT_TOKEN_RE):
        match = pattern.search(resp.text)
        if match:
            return match.group(1)
    raise RuntimeError("Could not find a CSRF token on /file-upload.")


def upload_file(session, base_url, token, path):
    """POST the image to /file-upload; return the response markup."""
    with open(path, "rb") as handle:
        resp = session.post(
            f"{base_url}/file-upload",
            data={"_token": token},
            files=[("file[]", (os.path.basename(path), handle))],
            allow_redirects=True,
        )
    resp.raise_for_status()
    return resp.text


def segment(session, base_url, token, upload_markup):
    """POST the uploaded image path to /decimer-segmentation; return the markup."""
    img_paths = hidden_field(upload_markup, "img_paths")
    if not img_paths or img_paths == "[]":
        raise RuntimeError(
            "Upload succeeded but returned no image paths "
            "(the server may have rejected the image)."
        )
    resp = session.post(
        f"{base_url}/decimer-segmentation",
        data={
            "_token": token,
            "img_paths": img_paths,
            "single_image_upload": hidden_field(upload_markup, "single_image_upload") or "true",
        },
        allow_redirects=True,
    )
    resp.raise_for_status()
    return resp.text


def run_ocsr(session, base_url, token, seg_markup):
    """POST the segmented structure path(s) to /decimer-ocsr; return the markup."""
    structure_paths = hidden_field(seg_markup, "structure_depiction_img_paths")
    if not structure_paths or structure_paths == "[]":
        raise RuntimeError("Segmentation found no chemical structures in the image.")
    resp = session.post(
        f"{base_url}/decimer-ocsr",
        data={
            "_token": token,
            "img_paths": hidden_field(seg_markup, "img_paths") or "",
            "structure_depiction_img_paths": structure_paths,
            "has_segmentation_already_run": hidden_field(seg_markup, "has_segmentation_already_run") or "true",
            "single_image_upload": hidden_field(seg_markup, "single_image_upload") or "",
        },
        allow_redirects=True,
    )
    resp.raise_for_status()
    return resp.text


def parse_smiles(ocsr_markup):
    """Pull the smiles_array JSON out of the OCSR response.

    Entries are kept as-is, including the empty strings the OCSR endpoint uses to pad
    results for structures past its 20-structure cap (and any that failed to resolve).
    """
    raw = hidden_field(ocsr_markup, "smiles_array")
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return value


def resolve_smiles(image, base_url, verify_tls):
    session = requests.Session()
    session.verify = verify_tls
    token = get_csrf_token(session, base_url)
    upload_markup = upload_file(session, base_url, token, image)
    seg_markup = segment(session, base_url, token, upload_markup)
    ocsr_markup = run_ocsr(session, base_url, token, seg_markup)
    return parse_smiles(ocsr_markup)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", help="A single structure image to run OCSR on")
    parser.add_argument("--format", choices=("json", "csv"), default="json",
                        help="Output format for the SMILES (default: %(default)s)")
    parser.add_argument("--base-url", default="http://localhost:8181/decimer",
                        help="App base URL (default: %(default)s)")
    parser.add_argument("--insecure", action="store_true",
                        help="Skip TLS verification (for https with self-signed certs)")
    args = parser.parse_args()

    if not os.path.isfile(args.image):
        sys.exit(f"error: file not found: {args.image}")
    ext = os.path.splitext(args.image)[1].lower()
    if ext not in VALID_EXTENSIONS:
        sys.exit(f"error: unsupported extension {ext!r} "
                 f"(allowed: {', '.join(sorted(VALID_EXTENSIONS))})")

    smiles = resolve_smiles(args.image, args.base_url.rstrip("/"), not args.insecure)

    if args.format == "json":
        print(json.dumps(smiles))
    else:
        writer = csv.writer(sys.stdout)
        for entry in smiles:
            writer.writerow([entry])


if __name__ == "__main__":
    main()
