from pathlib import Path

import numpy as np
import yaml
from PIL import Image

from scripts.prepare_rdd2022 import prepare, split_names, voc_to_yolo

XML = """<annotation><size><width>600</width><height>600</height></size>
<object><name>D40</name><bndbox><xmin>100</xmin><ymin>200</ymin><xmax>300</xmax><ymax>400</ymax></bndbox></object>
<object><name>D00</name><bndbox><xmin>0</xmin><ymin>0</ymin><xmax>60</xmax><ymax>600</ymax></bndbox></object>
<object><name>Repair</name><bndbox><xmin>1</xmin><ymin>1</ymin><xmax>50</xmax><ymax>50</ymax></bndbox></object>
</annotation>"""


def test_voc_to_yolo_keeps_four_classes(tmp_path):
    p = tmp_path / "a.xml"
    p.write_text(XML)
    lines, counts = voc_to_yolo(p)
    assert lines[0] == "3 0.333333 0.500000 0.333333 0.333333"
    assert lines[1].startswith("0 ")
    assert dict(counts) == {"D40": 1, "D00": 1}


def test_split_is_reproducible_and_complete():
    names = [f"img{i}" for i in range(100)]
    a, b = split_names(names, 42), split_names(list(reversed(names)), 42)
    assert a == b
    assert [len(a[s]) for s in ("train", "val", "test")] == [70, 15, 15]


def test_prepare_writes_yolo_dataset(tmp_path):
    src = tmp_path / "RDD2022"
    for country in ("India", "Japan"):
        xml_dir = src / country / "train" / "annotations" / "xmls"
        img_dir = src / country / "train" / "images"
        xml_dir.mkdir(parents=True)
        img_dir.mkdir(parents=True)
        for i in range(10):
            (xml_dir / f"{country}_{i}.xml").write_text(XML)
            Image.fromarray(np.zeros((8, 8, 3), np.uint8)).save(img_dir / f"{country}_{i}.jpg")
    out = tmp_path / "out"
    stats = prepare(src, out, ["India"], 42, copy=False)
    assert stats["countries"] == {"India": 10}
    assert stats["class_counts"] == {"D00": 10, "D10": 0, "D20": 0, "D40": 10}
    data = yaml.safe_load((out / "data.yaml").read_text())
    assert data["names"][3] == "pothole"
    assert len(list((out / "labels" / "train").glob("*.txt"))) == 7
    assert Path(out / "images" / "train").exists()
