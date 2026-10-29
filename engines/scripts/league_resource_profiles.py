"""Named P16/P192 test resource profiles for the C engine league.

The existing portfolio contract owns ``ResourceProfile`` and all historical
profiles. This separate owner supplies the two new league profiles without
changing those historical producer pins. It neither launches an engine nor
establishes rule, runtime, placement, size or strength qualification.
"""

from types import MappingProxyType


LEAGUE_PROFILES = MappingProxyType({
    "test-p16": (16, 16 << 30),
    "test-p192": (192, 192 << 30),
})


def resource_profile(api, profile_id):
    """Resolve through the C production contract and a finite league domain."""
    if type(profile_id) is not str:
        raise ValueError("a named immutable resource profile is required")
    if profile_id not in LEAGUE_PROFILES:
        return api.resource_profile(profile_id)
    workers, tt_cap = LEAGUE_PROFILES[profile_id]
    return api.ResourceProfile(profile_id, "test", workers, tt_cap)
