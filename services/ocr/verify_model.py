"""Opt-in real CPU inference smoke with a synthetic image, not an accuracy test."""
import hashlib
import io
import json
import os
import platform
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from services.ocr.app.engine import PaddleEngine
from services.ocr.app.extraction import decode_image, extract


def main():
    root = Path(os.environ.get('OCR_MODEL_DIR', 'services/ocr/models'))
    engine = PaddleEngine(root)
    image = Image.new('RGB', (1000, 180), 'white')
    draw = ImageDraw.Draw(image)
    font_path = os.environ.get('OCR_TEST_FONT', 'C:/Windows/Fonts/arial.ttf')
    font = ImageFont.truetype(font_path, 48) if Path(font_path).is_file() else ImageFont.load_default(size=48)
    draw.text((35, 50), 'Fraudster synthetic OCR test 123', font=font, fill='black')
    for fmt, mime in [('PNG', 'image/png'), ('JPEG', 'image/jpeg')]:
        data = io.BytesIO()
        image.save(data, format=fmt)
        decoded = decode_image(data.getvalue(), mime)
        code, result = extract(decoded, engine)
        assert code == 200, 'CPU extraction failed'
        assert 'synthetic' in result['text'].lower(), 'Synthetic text was not recognized'
        assert result['image'] == {'width': 1000, 'height': 180}
        assert result['boxes'], 'No boxes returned'
        # Print only test metadata, never recognition output or user data.
        print(f'{fmt}: CPU extraction passed; dimensions and boxes present')
    print(f'Tested: {platform.platform()}, Python {platform.python_version()}')
    for path in sorted(root.glob('*/*')):
        if path.is_file():
            print(json.dumps({'asset': str(path.relative_to(root)), 'bytes': path.stat().st_size,
                              'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
