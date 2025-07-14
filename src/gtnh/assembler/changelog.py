from typing import List, Optional

from gtnh.defs import Side

a = """## What's Changed
* Corrected Aluminum to Aluminium by @ChibiChoko in https://github.com/GTNewHorizons/WitchingGadgets/pull/78

## New Contributors
* @ChibiChoko made their first contribution in https://github.com/GTNewHorizons/WitchingGadgets/pull/78

**Full Changelog**: https://github.com/GTNewHorizons/WitchingGadgets/compare/1.7.9-GTNH...1.7.10-GTNH
"""

b = """## What's Changed
* Fixed IBF particle crash due to particle entities by @70000hp in https://github.com/GTNewHorizons/WitchingGadgets/pull/76

## New Contributors
* @70000hp made their first contribution in https://github.com/GTNewHorizons/WitchingGadgets/pull/76

**Full Changelog**: https://github.com/GTNewHorizons/WitchingGadgets/compare/1.7.7-GTNH...1.7.9-GTNH
"""

class ChangelogEntry:
    def __init__(self,version:str, changelog_str:Optional[str], prerelease=False)->None:
        self.version = version
        self.no_changelog: bool = changelog_str is None
        self.prerelease = prerelease
        self.changelog_entries = []
        self.new_contributors = []
        self.full_comparison_url: Optional[str] = None

        if changelog_str is not None:
            self.changelog_categories = changelog_str.split("\n\n")
            self.changelog_entries = self.changelog_categories[0].split("\n")[1:]
            if len(self.changelog_categories) == 3:
                self.new_contributors = self.changelog_categories[1].split("\n")[1:]


class ChangelogCollection:
    def __init__(self,pack_release_version:str, mod_name:str, changelog_entries:List[ChangelogEntry],oldest_side:Optional[Side], newest_side:Side, new_mod = False) -> None:
        self.pack_release_version: str = pack_release_version
        self.mod_name: str = mod_name
        self.new_mod: bool = new_mod
        self.oldest_side:Optional[Side]=oldest_side
        self.newest_side:Side=newest_side
        self.changelog_entries: List[ChangelogEntry] = sorted(changelog_entries,key=lambda x: x.version, reverse=True)
        self.oldest = self.changelog_entries[0]
        self.newest = self.changelog_entries[-1]

    @classmethod
    def get_pretty_side_string(cls, side: Optional[Side]) -> str:
        if side == Side.CLIENT:
            return "client-side only"
        if side == Side.CLIENT_JAVA9:
            return "client-side Java 9+ only"
        elif side == Side.SERVER:
            return "server-side only"
        elif side == Side.SERVER_JAVA9:
            return "server-side Java 9+ only"
        elif side == Side.BOTH:
            return "on both sides"
        elif side == Side.BOTH_JAVA9:
            return "on both sides, Java 9+ only"
        elif side is None:
            return "unknown"
        else:
            return str(side)

    @classmethod
    def blockquote(cls, strs:List[str])->List[str]:
        return [f">{s}" for s in strs]

    def generate_changelog(self) -> str:
        lines = []
        # define the header for the changelog of the mod
        if self.new_mod:
            header = f"# New Mod - {self.mod_name}:{self.newest.version}"
        else:
            header = f"# Updated - {self.mod_name} - {self.oldest.version} --> {self.newest.version}"
        lines.append(header)

        # side detection: only comparing oldest and newest version, as it's the only thing that matter for the release
        if not self.new_mod and self.oldest_side != self.newest_side:
            side_change = f"Mod side changed from {self.get_pretty_side_string(self.oldest_side)} to {self.get_pretty_side_string(self.newest_side)}."
            lines.append(side_change)

        # side precision:
        if self.newest_side not in [Side.BOTH, Side.BOTH_JAVA9]:
            side_precision = f"Mod is {self.get_pretty_side_string(self.newest_side)}."
            lines.append(side_precision)

        # what's changed text:
        lines.append("## What's Changed:")

        version_changelog: List[str] = []
        new_contributors: List[str] = []

        # actual mod version processing:
        for i, changelog_entry in enumerate(self.changelog_entries):
            if (
                    i != 0
                    and self.pack_release_version != "experimental"
                    and (
                    changelog_entry.prerelease
                    or (changelog_entry.version.endswith("-pre") or changelog_entry.version.endswith("-dev"))
            )
            ):
                # Only include prerelease changes if it's the latest release
                continue


            if not self.new_mod and changelog_entry.version == self.oldest.version:
                # skipping the oldest version as it has already been released in the previous pack release
                continue

            version_changelog.append((f"## *{changelog_entry.version}*"))
            if changelog_entry.no_changelog or len(changelog_entry.changelog_entries) == 0:
                version_changelog.append("**No Changelog Found for this version**")
            else:
                version_changelog.extend(self.blockquote(changelog_entry.changelog_entries))

            # add potential new contributors if any
            new_contributors.extend(changelog_entry.new_contributors)

            # spacer between releases
            version_changelog.append("")

        # spacer between changelog and new contributors
        version_changelog.append("")

        lines.extend(version_changelog)

        # New contributor section
        lines.append('## New contributors on the mod:')
        lines.extend(new_contributors)

        return "\n".join(lines)

if __name__ == "__main__":
    entry_a = ChangelogEntry(version="1.7.10-GTNH", changelog_str=a, side=Side.BOTH)
    entry_b = ChangelogEntry(version="1.7.9-GTNH", changelog_str=b, side=Side.BOTH)

    print(ChangelogCollection(pack_release_version="Daily",mod_name="WitchingGadget", changelog_entries=[entry_a, entry_b]).generate_changelog())

