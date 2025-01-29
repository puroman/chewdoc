from src.chewdoc.formatters.myst_writer import MystWriter
from pathlib import Path

def test_myst_writer_basic(tmp_path):
    writer = MystWriter()
    package_info = {
        "package": "testpkg",
        "modules": [{
            "name": "testmod",
            "docstrings": {"module": "Test module"}
        }],
        "config": {}
    }
    
    writer.generate(package_info, tmp_path)
    assert (tmp_path / "index.md").exists()
    assert "## Modules" in (tmp_path / "index.md").read_text()

def test_myst_writer_simple_module(tmp_path):
    writer = MystWriter()
    package_info = {
        "package": "testpkg",
        "modules": [{
            "name": "testmod",
            "docstrings": {"module": "Test docs"},
            "examples": [{"type": "doctest", "content": ">>> 1+1"}]
        }]
    }
    writer.generate(package_info, tmp_path)
    assert (tmp_path / "testmod.md").exists()