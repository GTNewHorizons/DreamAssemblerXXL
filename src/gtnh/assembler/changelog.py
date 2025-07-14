from typing import List, Optional

from gtnh.defs import Side

class ChangelogEntry:
    def __init__(self,version:str, changelog_str:Optional[str], prerelease=False)->None:
        self.version = version
        self.no_changelog: bool = changelog_str is None
        self.prerelease = prerelease
        self.changelog_entries = []
        self.new_contributors = []
        self.full_comparison_url: Optional[str] = None

        if changelog_str is not None:
            lines = changelog_str.split("\n")
            index = 0

        if "What's Changed" in changelog_str:
            while not "##" in lines[index]:
                index+=1

            index+=1 # skip the what's changed line

            while lines[index].startswith("*"):
                self.changelog_entries.append(lines[index].strip())
                index+=1

        if "New Contributors" in changelog_str:
            while "New Contributors" not in lines[index]:
                index+=1

            while lines[index].startswith("*"):
                self.new_contributors.append(lines[index].strip())
                index += 1
        if "Full Changelog" in changelog_str:
            while not "Full Changelog" in lines[index]:
                index += 1
            self.full_comparison_url=lines[index].strip()


class ChangelogCollection:
    def __init__(self,pack_release_version:str, mod_name:str, changelog_entries:List[ChangelogEntry],oldest_side:Optional[Side], newest_side:Side, new_mod = False) -> None:
        self.pack_release_version: str = pack_release_version
        self.mod_name: str = mod_name
        self.new_mod: bool = new_mod
        self.oldest_side:Optional[Side]=oldest_side
        self.newest_side:Side=newest_side
        self.changelog_entries: List[ChangelogEntry] = changelog_entries[::-1]
        self.oldest = self.changelog_entries[-1]
        self.newest = self.changelog_entries[0]

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
            if changelog_entry.no_changelog:
                version_changelog.append("**No Changelog Found for this version**")
            elif len(changelog_entry.changelog_entries) == 0:
                version_changelog.append("**No PR detected for this version, check commit history for more details.**")
                if changelog_entry.full_comparison_url is not None:
                    version_changelog.append(changelog_entry.full_comparison_url)
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

