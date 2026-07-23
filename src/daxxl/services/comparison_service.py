from collections import defaultdict
from typing import List, Optional, Set, Tuple

from daxxl.assembler.changelog import ChangelogCollection, ChangelogEntry
from daxxl.gtnh_logger import get_logger
from daxxl.models.available_assets import AvailableAssets
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.gtnh_version import GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.models.mod_version_info import ModVersionInfo

log = get_logger(__name__)


class ComparisonService:
    def __init__(self, assets: AvailableAssets) -> None:
        self.assets = assets

    @staticmethod
    def remove_false_positive_in_mod_removed(removed_mods: Set[str], added_mods: Set[str]) -> None:
        false_removed_mods: List[str] = []
        false_added_mods: List[str] = []
        for removed_mod in removed_mods:
            for added_mod in added_mods:
                stripped_removed_mod = "".join(filter(str.isalnum, removed_mod))
                stripped_added_mod = "".join(filter(str.isalnum, added_mod))
                if stripped_added_mod == stripped_removed_mod:
                    false_removed_mods.append(removed_mod)
                    false_added_mods.append(added_mod)
                    break
        for false_positive in false_removed_mods:
            removed_mods.remove(false_positive)

        for false_positive in false_added_mods:
            added_mods.remove(false_positive)

    def _mod_additions_and_removals(
        self, release: GTNHRelease, previous_release: GTNHRelease
    ) -> tuple[Set[str], Set[str]]:
        removed_mods = set(previous_release.github_mods) - set(release.github_mods)
        removed_mods |= set(previous_release.external_mods) - set(release.external_mods)
        new_mods = set(release.github_mods) - set(previous_release.github_mods)
        new_mods |= set(release.external_mods) - set(previous_release.external_mods)
        self.remove_false_positive_in_mod_removed(removed_mods, new_mods)
        return removed_mods, new_mods

    def get_removed_mods(self, release: GTNHRelease, previous_release: GTNHRelease) -> Set[str]:
        """
        Generate the list of removed mods between two releases.

        :returns: set[str]
        """
        removed_mods, _ = self._mod_additions_and_removals(release, previous_release)
        return removed_mods

    def get_new_mods(self, release: GTNHRelease, previous_release: GTNHRelease) -> Set[str]:
        """
        Generate the list of new mods between two releases.

        :returns: set[str]
        """
        _, new_mods = self._mod_additions_and_removals(release, previous_release)
        return new_mods

    def get_changed_mods(self, release: GTNHRelease, previous_release: GTNHRelease) -> Set[str]:
        """
        Generate the list of updated/added mods between two releases. If the `previous_release` is None, generate
        it for all history.

        :returns: set[str]
        """
        removed_mods, new_mods = self._mod_additions_and_removals(release, previous_release)

        current_releases_github = set(release.github_mods.keys())
        current_releases_external = set(release.external_mods.keys())

        common_github_mods = current_releases_github - removed_mods - new_mods
        common_external_mods = current_releases_external - removed_mods - new_mods

        changed_github_mods = {
            x
            for x in common_github_mods
            if x in release.github_mods
            and x in previous_release.github_mods
            and release.github_mods[x].version != previous_release.github_mods[x].version
        }
        changed_external_mods = {
            x
            for x in common_external_mods
            if x in release.external_mods
            and x in previous_release.external_mods
            and release.external_mods[x].version != previous_release.external_mods[x].version
        }

        return changed_github_mods | changed_external_mods

    def generate_changelog(
        self, release: GTNHRelease, previous_release: GTNHRelease | None = None
    ) -> dict[str, list[str]]:
        """
        Generate a changelog between two releases.  If the `previous_release` is None, generate it for all of history
        :returns: dict[mod_name, list[version_changes]]
        """
        removed_mods = set()
        new_mods = set()
        version_changes: dict[str, Tuple[Optional[ModVersionInfo], ModVersionInfo]] = {}

        changelog: dict[str, list[str]] = defaultdict(list)

        contributors: Set[str] = set()
        if previous_release is not None:
            removed_mods, new_mods = self._mod_additions_and_removals(release, previous_release)

            changed_github_mods = set(release.github_mods.keys() & previous_release.github_mods.keys())
            changed_external_mods = set(release.external_mods.keys() & previous_release.external_mods.keys())

            for mod_name in changed_github_mods | changed_external_mods | new_mods:
                # looks like here there are some shenanigans happening, so i'm just going to check for mod presence before anything
                # i don't quite get what's happenning here.

                previous_source = (
                    previous_release.github_mods if mod_name in release.github_mods else previous_release.external_mods
                )
                current_source = release.github_mods if mod_name in release.github_mods else release.external_mods

                version_changes[mod_name] = (previous_source.get(mod_name, None), current_source[mod_name])
        else:
            changed_github_mods = set(release.github_mods.keys())
            changed_external_mods = set(release.external_mods.keys())

            for mod_name in changed_github_mods:
                version_changes[mod_name] = (None, release.github_mods[mod_name])

            for mod_name in changed_external_mods:
                version_changes[mod_name] = (None, release.external_mods[mod_name])

        if new_mods:
            changelog["new_mods"].append("# New Mods: ")
            changelog["new_mods"].extend([f"> * {mod_name}" for mod_name in sorted(new_mods)])

        if removed_mods:
            changelog["removed_mods"].append("# Mods Removed: ")
            changelog["removed_mods"].extend([f"> * {mod_name}" for mod_name in sorted(removed_mods)])

        # Changes
        for mod_name in sorted(version_changes.keys()):
            (old_version, new_version) = version_changes[mod_name]
            if old_version == new_version:
                continue

            mod = self.assets.get_mod(mod_name)
            mod_versions: List[GTNHVersion] = mod.get_versions(
                left=old_version.version if old_version else None, right=new_version.version
            )

            # Something bad happens if we have empty mod_versions, but better to have an improper changelog than a crash
            if not len(mod_versions):
                continue

            changes = changelog[mod_name]

            mod_version_changelogs = [
                ChangelogEntry(version=v.version_tag, changelog_str=v.changelog, prerelease=v.prerelease)
                for v in mod_versions
            ]
            is_new_mod = old_version is None
            mod_changelog = ChangelogCollection(
                pack_release_version=release.version,
                mod_name=mod_name,
                changelog_entries=mod_version_changelogs,
                oldest_side=None if is_new_mod else old_version.side,
                newest_side=new_version.side, # type: ignore
                new_mod=is_new_mod,
            )

            changes.append(mod_changelog.generate_mod_changelog())
            contributors |= mod_changelog.contributors

        if len(contributors) > 0:
            changelog["credits"].append("# Credits")
            changelog["credits"].append(
                f"Special thanks to {', '.join(sorted(list(contributors), key=str.casefold))}, "
                "for their code contributions listed above, and to everyone else who helped, "
                "including all of our beta testers! <3"
            )

        return changelog
