"""Display colors for sources that do not provide team colors."""
from colorsys import hls_to_rgb
from hashlib import blake2s
import re


_PALETTE = {
    team: color
    for color, teams in (
        ('#3671C6', ('red bull', 'red bull racing', 'oracle red bull racing', 'aston martin red bull racing')),
        ('#FF8000', ('mclaren', 'mclaren f1 team', 'mclaren mastercard f1 team')),
        ('#E8002D', ('ferrari', 'scuderia ferrari', 'scuderia ferrari hp')),
        ('#27F4D2', ('mercedes', 'mercedes amg petronas f1 team', 'mercedes amg petronas motorsport')),
        ('#229971', ('aston martin', 'aston martin aramco f1 team', 'aston martin aramco cognizant f1 team')),
        ('#64C4FF', ('williams', 'williams racing', 'atlassian williams racing', 'atlassian williams f1 team')),
        ('#0093CC', ('alpine', 'bwt alpine f1 team')),
        ('#B6BABD', ('haas', 'haas f1 team', 'moneygram haas f1 team', 'tgr haas f1 team')),
        ('#6692FF', ('alphatauri', 'scuderia alphatauri', 'rb', 'racing bulls',
                     'visa cash app rb f1 team', 'visa cash app racing bulls f1 team')),
        ('#C92D4B', ('alfa romeo', 'alfa romeo f1 team orlen', 'alfa romeo f1 team stake', 'alfa romeo f1 team kick')),
        ('#52E252', ('kick sauber', 'kick sauber f1 team', 'stake f1 team kick sauber')),
        ('#F50537', ('audi', 'audi revolut f1 team')),
        ('#9F7A42', ('cadillac', 'cadillac f1 team')),
    )
    for team in teams
}


def resolve_team_color(team, color=None, source=None):
    """Keep a provider's valid color, or assign a stable color for the team."""
    hex_code = str(color or '').strip().lstrip('#')
    if source != 'unknown' and re.fullmatch(r'[0-9a-fA-F]{6}', hex_code):
        return f'#{hex_code.upper()}', source or 'provided'

    name = ' '.join((team or '').casefold().split())
    if not name or name == 'unknown':
        return '#808080', 'unknown'
    if name in _PALETTE:
        return _PALETTE[name], 'team_palette'

    digest = blake2s(name.encode(), digest_size=4).digest()
    hue = int.from_bytes(digest, 'big') / 2**32
    rgb = hls_to_rgb(hue, .53, .68)
    return '#' + ''.join(f'{round(channel * 255):02X}' for channel in rgb), 'generated_for_team'
