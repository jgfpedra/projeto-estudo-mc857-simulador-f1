"""Camada HTTP/WebSocket do backend.

Expõe:
- POST /races            — cria e inicia uma nova corrida
- WS   /ws/races/{race_id} — transmite o estado da corrida em tempo real
"""
