"""Racing Simulation package.

Modular racing simulation engine built on top of PyBullet.

Layers
------
- ``domain``   : pure business rules (tyre, weather, car, track, driver)
- ``engine``   : physics + orchestration (PyBullet, events, publisher, sim loop)
- ``config``   : race configuration dataclasses and named presets
"""

__version__ = "0.1.0"
