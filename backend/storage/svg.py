"""Validated, database-backed F1DB SVG cache."""
from __future__ import annotations

import hashlib
import logging
import threading
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from . import postgres

logger = logging.getLogger(__name__)
PREFIX = 'https://raw.githubusercontent.com/f1db/f1db/'
MAX_SIZE = 512 * 1024


class _AllowedRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith(PREFIX):
            raise ValueError('Redirecionamento de SVG não permitido')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch(url):
    if not url.startswith(PREFIX): raise ValueError('Fonte de SVG não permitida')
    request = urllib.request.Request(url, headers={'User-Agent':'F1Simulator/1.0'})
    opener = urllib.request.build_opener(_AllowedRedirects())
    with opener.open(request, timeout=5) as response:
        if not response.geturl().startswith(PREFIX): raise ValueError('Redirecionamento de SVG não permitido')
        data = response.read(MAX_SIZE + 1)
    if len(data) > MAX_SIZE or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('SVG inválido ou muito grande')
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError('SVG inválido') from exc
    if root.tag.split('}')[-1] != 'svg': raise ValueError('Documento não é SVG')
    for element in root.iter():
        if element.tag.split('}')[-1].lower() in {'script', 'foreignobject'}: raise ValueError('Conteúdo ativo no SVG')
        for key, value in element.attrib.items():
            name = key.split('}')[-1].lower()
            if name.startswith('on') or (name == 'href' and not value.startswith('#')):
                raise ValueError('Referência ativa no SVG')
    return data.decode('utf-8')


def get_svg(layout_id, style, source_url):
    with postgres.connect() as conn:
        row = conn.execute('SELECT svg FROM catalog_svg WHERE layout_id=%s AND style=%s', (layout_id,style)).fetchone()
    if row: return row['svg']
    text = _fetch(source_url)
    digest = hashlib.sha256(text.encode()).hexdigest()
    with postgres.connect() as conn:
        conn.execute('INSERT INTO catalog_svg(layout_id,style,source_url,svg,sha256) VALUES (%s,%s,%s,%s,%s) ON CONFLICT(layout_id,style) DO NOTHING',
                     (layout_id,style,source_url,text,digest))
        return conn.execute('SELECT svg FROM catalog_svg WHERE layout_id=%s AND style=%s', (layout_id,style)).fetchone()['svg']


def warm_catalog(circuits, available):
    def run():
        def warm(item):
            layout_id, style, url = item
            try:
                get_svg(layout_id, style, url)
            except (OSError, ValueError) as exc:
                logger.warning('SVG %s/%s indisponível: %s', layout_id, style, exc)

        try:
            # Only one backend imports at a time. Aborting the process also releases the lock.
            with postgres.connect() as conn:
                if not conn.execute('SELECT pg_try_advisory_lock(73021489) AS locked').fetchone()['locked']:
                    return
                existing = {(row['layout_id'], row['style'])
                            for row in conn.execute('SELECT layout_id, style FROM catalog_svg')}
                missing = [(layout['id'], style, url) for circuit in circuits
                           for layout in circuit.get('layouts', []) if layout['id'] in available
                           for style, url in (layout.get('svg') or {}).items()
                           if url and (layout['id'], style) not in existing]
                with ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(warm, missing))
        except Exception:
            logger.exception('Falha ao pré-carregar catálogo de SVG')
    thread = threading.Thread(target=run, name='svg-bootstrap', daemon=True)
    thread.start()
