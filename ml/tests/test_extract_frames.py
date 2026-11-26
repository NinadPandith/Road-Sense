from datetime import datetime, timedelta, timezone

import cv2
import numpy as np

from scripts.extract_frames import dhash, extract, hamming, load_gpx

START = datetime(2026, 11, 30, 2, 0, 0, tzinfo=timezone.utc)


def _gpx(path, n=20):
    pts = "".join(
        f'<trkpt lat="{12.97 + i * 0.0001}" lon="77.59"><time>'
        f"{(START + timedelta(seconds=i)).strftime('%Y-%m-%dT%H:%M:%SZ')}</time></trkpt>"
        for i in range(n)
    )
    path.write_text(
        '<?xml version="1.0"?><gpx version="1.1" creator="t" '
        'xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>'
        f"{pts}</trkseg></trk></gpx>"
    )


def test_dhash_detects_duplicates():
    rng = np.random.default_rng(0)
    a = rng.integers(0, 255, (120, 160, 3), dtype=np.uint8)
    assert hamming(dhash(a), dhash(a)) == 0
    assert hamming(dhash(a), dhash(rng.integers(0, 255, a.shape, dtype=np.uint8))) > 10


def test_extract_one_fps_with_gps(tmp_path):
    video = tmp_path / "ride.avi"
    vw = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 10, (160, 120))
    rng = np.random.default_rng(1)
    for i in range(50):  # 5 s; a new random scene every second, one static second
        if i % 10 == 0 and i != 30:
            scene = rng.integers(0, 255, (120, 160, 3), dtype=np.uint8)
        vw.write(scene)
    vw.release()
    gpx = tmp_path / "ride.gpx"
    _gpx(gpx)
    rows = extract(video, tmp_path / "frames", load_gpx(gpx), START)
    assert len(rows) == 4  # second 3 repeats second 2 -> dropped as duplicate
    assert rows[1]["lat"] == round(12.97 + 0.0001, 7)
    assert (tmp_path / "frames" / "frames.csv").exists()
