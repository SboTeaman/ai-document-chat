from unittest.mock import MagicMock, patch

from common import storage
from common.ollama import get_ollama_client


def test_sanitize_filename_strips_path_and_unsafe_chars():
    assert storage._sanitize_filename("../../etc/passwd") == "passwd"
    assert storage._sanitize_filename("a\\b\\c.txt") == "c.txt"
    assert storage._sanitize_filename("we ird!@#name.pdf") == "we_ird_name.pdf"


def test_sanitize_filename_falls_back_to_file_for_empty_result():
    assert storage._sanitize_filename("...") == "file"
    assert storage._sanitize_filename("\x00\x00") == "file"


def test_sanitize_filename_truncates_to_200_chars():
    assert len(storage._sanitize_filename("x" * 500 + ".txt")) <= 200


@patch("common.storage.boto3.client")
def test_upload_file_builds_namespaced_key(mock_client):
    s3 = MagicMock()
    mock_client.return_value = s3
    key = storage.upload_file(MagicMock(), workspace_id=7, original_filename="report.pdf")
    assert key.startswith("workspaces/7/")
    assert key.endswith("report.pdf")
    s3.upload_fileobj.assert_called_once()


@patch("common.storage.boto3.client")
def test_delete_file_calls_s3(mock_client):
    s3 = MagicMock()
    mock_client.return_value = s3
    storage.delete_file("workspaces/1/x.pdf")
    s3.delete_object.assert_called_once()


@patch("common.storage.boto3.client")
def test_get_presigned_url_returns_signed_url(mock_client):
    s3 = MagicMock()
    s3.generate_presigned_url.return_value = "https://signed"
    mock_client.return_value = s3
    assert storage.get_presigned_url("k") == "https://signed"


@patch("common.storage.boto3.client")
def test_download_file_bytes_reads_body(mock_client):
    s3 = MagicMock()
    s3.get_object.return_value = {"Body": MagicMock(read=lambda: b"data")}
    mock_client.return_value = s3
    assert storage.download_file_bytes("k") == b"data"


@patch("common.ollama.OpenAI")
def test_get_ollama_client_builds_openai_instance(mock_openai):
    client = get_ollama_client()
    mock_openai.assert_called_once()
    assert client is mock_openai.return_value
