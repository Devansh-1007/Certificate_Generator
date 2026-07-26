"""Offline tests for the template-engine certificate pipeline (no DB/S3/network)."""

import os
import base64

import pytest

from certificates import default_template, build_data, render_certificate


def test_build_data_fills_all_placeholders():
    t = default_template()
    d = build_data(t, "Devansh Choudhary", "devansh", {"EVENT_NAME": "CertifyAI Launch"})
    assert d["RECIPIENT_NAME"] == "Devansh Choudhary"
    assert d["EVENT_NAME"] == "CertifyAI Launch"
    assert d["ISSUE_DATE"] and d["SIGNATORY_NAME"] and d["VERIFY_URL"]


def test_render_certificate_produces_files_and_base64(tmp_path, monkeypatch):
    import certificates as c
    monkeypatch.setattr(c, "allCertImgPath", str(tmp_path / "img"))
    monkeypatch.setattr(c, "allCertPdfPath", str(tmp_path / "pdf"))
    monkeypatch.setattr(c, "upload_file", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no storage")))

    result = c.render_certificate("Devansh Choudhary", "devansh")
    assert result["CERTIFICATE_DETAILS"]["CERTIFICATE_NAME"] == "Devansh Choudhary"
    # storage is down -> URLs None, but the local render + base64 must still work
    assert result["CERTIFICATE_DETAILS"]["IMAGE_URL"] is None
    b64 = result["CERTIFICATE_DETAILS"]["BASE64"]
    assert base64.b64decode(b64)[:8] == b"\x89PNG\r\n\x1a\n"
    # names are sanitised for object keys (spaces/punctuation are unsafe)
    assert os.path.exists(os.path.join(str(tmp_path / "img"), "devansh", "Devansh_Choudhary.png"))
    assert os.path.exists(os.path.join(str(tmp_path / "pdf"), "devansh", "Devansh_Choudhary.pdf"))


def test_render_certificate_with_overrides(tmp_path, monkeypatch):
    import certificates as c
    monkeypatch.setattr(c, "allCertImgPath", str(tmp_path / "img"))
    monkeypatch.setattr(c, "allCertPdfPath", str(tmp_path / "pdf"))
    monkeypatch.setattr(c, "upload_file", lambda *a, **k: True)
    monkeypatch.setattr(c, "getSignedUrl", lambda *a, **k: "https://signed.example/x")

    result = c.render_certificate("A B", "devansh", overrides={"VERIFY_URL": "https://v.example/123"})
    assert result["CERTIFICATE_DETAILS"]["IMAGE_URL"] == "https://signed.example/x"


def test_file_key_isolates_reissues(tmp_path, monkeypatch):
    """
    Two certificates for the same person must not overwrite each other:
    files are keyed by the issuance uid, not the recipient name.
    """
    import certificates as c
    monkeypatch.setattr(c, "allCertImgPath", str(tmp_path / "img"))
    monkeypatch.setattr(c, "allCertPdfPath", str(tmp_path / "pdf"))
    monkeypatch.setattr(c, "upload_file", lambda *a, **k: True)
    monkeypatch.setattr(c, "getSignedUrl", lambda *a, **k: "https://x/y")

    c.render_certificate("Alice Sharma", "acme", file_key="uid-one")
    c.render_certificate("Alice Sharma", "acme", file_key="uid-two")
    folder = os.path.join(str(tmp_path / "img"), "acme")
    assert sorted(os.listdir(folder)) == ["uid-one.png", "uid-two.png"]


def test_unsafe_names_are_sanitised(tmp_path, monkeypatch):
    import certificates as c
    monkeypatch.setattr(c, "allCertImgPath", str(tmp_path / "img"))
    monkeypatch.setattr(c, "allCertPdfPath", str(tmp_path / "pdf"))
    monkeypatch.setattr(c, "upload_file", lambda *a, **k: True)
    monkeypatch.setattr(c, "getSignedUrl", lambda *a, **k: "https://x/y")

    c.render_certificate("../../etc/passwd", "acme")
    files = os.listdir(os.path.join(str(tmp_path / "img"), "acme"))
    assert files == ["etc_passwd.png"]  # separators and dot-runs collapsed
