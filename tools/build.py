"""Embed the state outlines (brmap.json) into index.src.html -> index.html.
The map is inlined so the page also works when opened straight from disk (file://)."""
import pathlib
root = pathlib.Path(__file__).resolve().parent.parent
src = (root / "index.src.html").read_text()
(root / "index.html").write_text(src.replace("__MAP__", (root / "brmap.json").read_text()))
print("wrote index.html")
