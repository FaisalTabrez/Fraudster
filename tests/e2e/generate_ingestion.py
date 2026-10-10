"""Generate only synthetic local smoke inputs; never use private screenshots."""
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont


root = Path('.venv/ingestion-fixtures')
root.mkdir(parents=True, exist_ok=True)
image = Image.new('RGB', (1000, 180), 'white')
font_path = Path('C:/Windows/Fonts/arial.ttf')
font = ImageFont.truetype(str(font_path), 48) if font_path.is_file() else ImageFont.load_default(size=48)
ImageDraw.Draw(image).text((35, 50), 'Fraudster synthetic OCR test 123', font=font, fill='black')
image.save(root / 'synthetic-ocr.png')
Image.new('RGB', (100, 100), 'white').save(root / 'synthetic-no-code.png')
(root / 'synthetic-invalid.png').write_bytes(b'Not a real PNG')
for name, value in [('url', 'https://example.test/qr'), ('text', 'Synthetic plain text'),
                    ('note', 'Note:hello'), ('meeting', 'Meeting:10am'),
                    ('payment', 'upi://pay?pa=synthetic@example')]:
    qrcode.make(value).save(root / f'synthetic-qr-{name}.png')
print('Synthetic OCR/QR smoke inputs generated under ignored .venv/ingestion-fixtures.')
