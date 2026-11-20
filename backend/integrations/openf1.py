"""Transporte HTTP pequeno para a API histórica pública da OpenF1."""
from __future__ import annotations
import json
from urllib.parse import urlencode
from urllib.request import urlopen


class OpenF1Client:
    def __init__(self, timeout: float = 3.0, base_url: str = 'https://api.openf1.org/v1'):
        self.timeout = timeout
        self.base_url = base_url.rstrip('/')

    def get(self, resource: str, **params):
        url = f'{self.base_url}/{resource}?{urlencode(params)}'
        with urlopen(url, timeout=self.timeout) as response:
            return json.load(response)
