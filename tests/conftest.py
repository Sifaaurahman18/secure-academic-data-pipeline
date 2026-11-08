"""Penyiapan bersama untuk seluruh pengujian proyek.

Berkas bernama `conftest.py` dibaca pytest secara otomatis sebelum berkas uji
mana pun dijalankan. Di sini berkas itu dipakai untuk satu hal saja:
memastikan folder proyek berada pada jalur impor, sehingga
`from api.main import app` bekerja ketika pytest dijalankan dari mana pun.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROYEK = Path(__file__).resolve().parents[1]

if str(PROYEK) not in sys.path:
    sys.path.insert(0, str(PROYEK))
