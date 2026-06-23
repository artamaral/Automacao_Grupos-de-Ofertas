import hashlib

from ofertas_bot.local_manifest_hash_cli import run


def test_local_manifest_hash_cli_prints_hash_and_size(tmp_path, capsys) -> None:
    path = tmp_path / "manifest.json"
    content = b"[]"
    path.write_bytes(content)

    exit_code = run(["--file", str(path)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Tamanho: 2 bytes" in output
    assert hashlib.sha256(content).hexdigest() in output
    assert "Nenhum envio" in output


def test_local_manifest_hash_cli_returns_error_for_missing_file(tmp_path) -> None:
    path = tmp_path / "missing.json"

    exit_code = run(["--file", str(path)])

    assert exit_code == 3
