"""Regression tests for cross-chat scientific data discovery."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from pantheon.toolsets.file import FileManagerToolSet


@pytest.fixture(autouse=True)
def _reset_tool_context():
    """Keep explicit workdir context in one test from leaking into others."""
    yield
    from pantheon.toolset import get_current_context_variables

    context = get_current_context_variables()
    for key in ("workdir", "project_root", "chat_id"):
        context.pop(key, None)


def _pbmc_archive() -> bytes:
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w:gz") as archive:
        for name, content in (
            ("filtered_gene_bc_matrices/hg19/matrix.mtx", "%%MatrixMarket matrix coordinate integer general\n"),
            ("filtered_gene_bc_matrices/hg19/barcodes.tsv", "cell-1\n"),
            ("filtered_gene_bc_matrices/hg19/genes.tsv", "gene-1\tGENE1\n"),
        ):
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return payload.getvalue()


@pytest.mark.asyncio
async def test_discover_data_files_finds_previous_chat_workspace(tmp_path, monkeypatch):
    volume = tmp_path / "volume"
    current_chat = volume / ".pantheon" / "workspaces" / "new-chat"
    old_chat = volume / ".pantheon" / "workspaces" / "old-chat"
    endpoint_project = volume / "default_workspace"
    current_chat.mkdir(parents=True)
    old_chat.mkdir(parents=True)
    endpoint_project.mkdir(parents=True)

    (old_chat / "pbmc3k_clustering.h5ad").write_bytes(b"old-data")
    (current_chat / "notes.csv").write_text("gene,count\n", encoding="utf-8")
    monkeypatch.setenv("WORKSPACE_PATH", str(volume))

    toolset = FileManagerToolSet("file_manager", endpoint_project)
    result = await toolset.discover_data_files(
        context_variables={"workdir": str(current_chat)}
    )

    assert result["success"] is True
    assert result["has_user_data"] is True
    paths = {Path(item["path"]) for item in result["files"]}
    assert old_chat / "pbmc3k_clustering.h5ad" in paths
    assert current_chat / "notes.csv" in paths
    old_entry = next(
        item for item in result["files"] if item["name"] == "pbmc3k_clustering.h5ad"
    )
    assert old_entry["source"] == "existing_chat_workspace"
    assert old_entry["in_current_workspace"] is False


@pytest.mark.asyncio
async def test_prepare_default_dataset_downloads_only_when_no_user_data(
    tmp_path, monkeypatch
):
    volume = tmp_path / "volume"
    current_chat = volume / ".pantheon" / "workspaces" / "new-chat"
    current_chat.mkdir(parents=True)
    monkeypatch.setenv("WORKSPACE_PATH", str(volume))

    class FakeResponse:
        def __init__(self, payload: bytes):
            self._payload = io.BytesIO(payload)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, size=-1):
            return self._payload.read(size)

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *_args, **_kwargs: FakeResponse(_pbmc_archive()),
    )

    toolset = FileManagerToolSet("file_manager", current_chat)
    result = await toolset.prepare_default_dataset(
        context_variables={"workdir": str(current_chat)}
    )

    assert result["success"] is True
    assert result["status"] == "downloaded"
    dataset_path = Path(result["dataset_path"])
    assert dataset_path == current_chat / "data" / "pbmc3k_demo" / "filtered_gene_bc_matrices" / "hg19"
    assert (dataset_path / "matrix.mtx").is_file()
    assert (current_chat / "data" / "pbmc3k_demo" / "README.md").is_file()
    assert "10x Genomics" in (current_chat / "data" / "pbmc3k_demo" / "README.md").read_text(
        encoding="utf-8"
    )


@pytest.mark.asyncio
async def test_prepare_default_dataset_does_not_download_when_data_exists(tmp_path, monkeypatch):
    current_chat = tmp_path / "chat"
    current_chat.mkdir()
    (current_chat / "input.h5ad").write_bytes(b"user-data")
    toolset = FileManagerToolSet("file_manager", current_chat)

    def should_not_download(*_args, **_kwargs):
        raise AssertionError("default dataset must not replace user data")

    monkeypatch.setattr("urllib.request.urlopen", should_not_download)
    result = await toolset.prepare_default_dataset()

    assert result["success"] is True
    assert result["status"] == "user_data_available"
    assert any(item["name"] == "input.h5ad" for item in result["files"])
