"""data.json → images/  — pipeline.py 로 위임하는 진입점."""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import pipeline

if __name__ == "__main__":
    b = pathlib.Path(sys.argv[1])
    pipeline.build_images(json.loads((b / "data.json").read_text(encoding="utf-8")), b)
