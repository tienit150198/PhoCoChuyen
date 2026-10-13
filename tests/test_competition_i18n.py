"""Every newly authored competition line must be in the shipped English pack."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_authored_competition_copy_is_in_runtime_pack():
    pack = json.loads((ROOT / 'public/i18n/en.json').read_text(encoding='utf-8'))
    for filename in ('content-en.json', 'backend-en.json', 'ui-en.json'):
        source = json.loads((ROOT / 'output/career-competition' / filename).read_text(encoding='utf-8'))
        for text in source['strings']:
            assert pack['strings'].get(text), text
    assert pack['strings']['Thưởng thi đua nghề']
