To setup DreamAssemblerXXL do the following steps:
1. Add a personal token, as described in [README.md](https://github.com/GTNewHorizons/DreamAssemblerXXL/blob/master/README.md)
2. clone the repository
3. open terminal/console in the root of the repository and type the following commands:
- `python -m pip install uv`
- `uv sync`

To run DreamAssemblerXXL do type the following commands in a terminal/console at the root of the repository:
- (only if you are on windows) `chcp 65001`
- `uv run python -m daxxl.gui.gui`

DreamAssemblerXXL can be split up in 3 categories: Modpack management (in green), Mod management (in red) and File exclusion management (in yellow)

![image](https://user-images.githubusercontent.com/12850933/187891144-e9cd9402-eaea-4a10-a658-a46094884f8b.png)

The modpack management section is used to manage the pack version: you can load a version in memory, add or update a version and delete a version. It can also build the pack for various plateforms. It also allows you to update the data about mod versions and allows you to do a experimental or daily build.

![image](https://user-images.githubusercontent.com/12850933/187900736-eb3fa793-f994-48c3-ad98-cff9cb3c0810.png)

The mod management section is used to chose mod versions and sides for the version loaded in memory.

![image](https://user-images.githubusercontent.com/12850933/187900515-b1592f86-8c35-4b6b-974c-e3ec1c220299.png)

The file exclusion management section allows you to remove certains files from GT-New-Horizons releases based on the side of the archive: server side or client side.

![image](https://user-images.githubusercontent.com/12850933/187896905-1bb63b0e-fad0-43fc-aa9f-21ebd37d7cd8.png)

## Publish a new version to Technic Solder

### Technic assembly performance

Technic prepares up to four individual mod ZIPs concurrently in worker threads. Their
compression and the outer archive copies run outside the GUI event loop; only one writer
uses each outer ZIP at a time. Temporary packages are bounded to the current batch.
The outer archive stores the already-compressed packages without recompressing them;
the nested ZIP format, compression and permissions remain the same.

Technic produces one `updated mods` ZIP. It contains new or updated client packages
compared with the previous release, configuration if its version changed, and
`gtnh-java-args` for the target release. It does not package unchanged or removed mods.
When the release has no previous release, all selected packages are included. If a
previous release is specified but cannot be loaded, assembly stops.

### Solder publication

Publication is performed manually by an operator through the GUI using `solder.json`.

Requires Solder 1.5.0 and an existing pack. Every publication creates a new build from
the loaded release's complete mod selection; no previous Solder build is read or cloned.
Create a bearer token from the Solder
user profile; the account needs `mods_create`, `mods_manage`, `modpacks_manage` and access
to the target pack. The Technic Platform linking key is not a bearer token.

1. Click **Technic update ZIP**. It creates
   `releases/technic/GT_New_Horizons_<release>_(updated mods).zip`.
2. Extract and upload the individual ZIPs not already registered in Solder to the
   configured mirror. Keep `mods/{name}/{name}-{version}.zip` relative to the mirror
   root. The `technic-selection.json` file stays in the local update ZIP. Do not upload
   the outer ZIP, unpack the individual ZIPs, or overwrite existing versions.
   Keep the mirror URL's trailing slash.
3. Once the upload is done, click **Publish Solder build**. The button does not upload
   any files. It checks the loaded release against the selection saved in the update ZIP,
   then checks the required ZIPs on the mirror before making any writes. If the selection
   changed or an older ZIP has no saved selection, regenerate it and upload the changes.

### GUI configuration file

Start the GUI with `gui.bat`, then click **Publish Solder build**. If `solder.json` is
missing, it is automatically created in the DreamAssemblerXXL root folder (next to
`gui.bat`) with three empty string fields: `url`, `pack`, `token`. Environment values are
never written into the generated file. An existing file is never overwritten.

Fill in the Solder installation URL, existing pack slug and complete bearer token in
that file, then click **Publish Solder build** again. No settings form opens: publication
uses the config, loaded release and its Technic update ZIP directly. The GUI
publishes publicly and updates `latest`, leaving `recommended` unchanged.
Progress and completion are shown in the main window. Missing configuration or archive
produces an error before publication. The file is reread on each click; no restart is needed.

The global bar advances across seven phases: reading the archive, connecting, checking
packages, creating the build, registering new versions, assigning mods, and publishing.
The task bar resets at each phase and advances by processed bytes/files or completed API
operations. Existing versions also count as processed. Rate-limit waits do not add progress
until the operation completes; 100% global progress is reached only after successful publication.

`solder.json` contains the token in plain text and is ignored by Git. Edit the JSON file
to change persistent settings. File values take precedence over environment variables;
missing fields fall back to `SOLDER_URL`, `SOLDER_PACK`, `SOLDER_TOKEN`, then empty strings.
Invalid JSON, unknown fields or non-string values produce an error without displaying secrets.

Build settings default to the current GTNH Technic client: Minecraft `1.7.10`, Forge
`10.13.4.1614`, minimum Java `25`, Mojang runtime `java-runtime-epsilon` (Java 25), and no
declared minimum memory. The Java 25 JVM patch requires `min_java` to remain `25`; an
explicit runtime override must be `java-runtime-epsilon`. Remove/update older Java settings
in `solder.json` if present; incompatible overrides stop publication before any API calls.
Optional string fields in `solder.json` can override these settings: `minecraft`, `forge`,
`min_java`, `java_runtime`, `min_memory` (positive integer in MB, stored as a JSON string).
Omitted/empty optional fields use the defaults. The generated config still contains only
the three empty connection fields; existing config files remain usable unchanged.

The client defaults to the patched server's **1,200 requests/minute** limit, with 5% extra
spacing between request starts (52.5 ms). Override it with the optional string field
`requests_per_minute` in `solder.json` (for example `"1200"`, or `"60"` for an unpatched
server). This configures client pacing; it does not change the server's limit.

### Published packages

The loaded release supplies the complete desired mod and configuration list.
The update ZIP also supplies `gtnh-java-args`. All selected versions are assigned to the new empty build.
Removed mods remain in Solder's shared library but are not assigned to the build.
Every build also includes the mandatory hardcoded mod **`modpack`**, version
**`1.7.10-10.13.4.1614-version-less`**, even when absent from the archive. This exact version must already
be registered in Solder, or its ZIP must be included in the update ZIP and uploaded to
the mirror for normal verification/registration. It is assigned only once. A release
selecting a different `modpack` version is rejected. The final manifest must contain the
mandatory version before the build can be made public or promoted.
Technic includes all release-selected client/both mods, for Java 8 and Java 9+:
`CLIENT`, `BOTH`, `CLIENT_JAVA9`, `BOTH_JAVA9`. This applies to GitHub and external mods,
for both assembly and publication. `SERVER`, `SERVER_JAVA9` and `NONE` are excluded.
Each version comes from the release manifest, not the latest asset version. There is no
special selection rule for `lwjgl3ify`. Regenerate the update ZIP and upload the newly
included ZIPs before publishing; Solder registers and assigns them normally.

### Java arguments and Java 25

Assembly generates a `gtnh-java-args` package containing `patches/gtnh-jvm.json` and
`bin/version.json`. The latter is the **published `version.json` release asset** of the
selected lwjgl3ify version, copied unchanged. Each Technic assembly fetches it again from
the selected tag, even when the local cache already contains a profile. The tagged URL
still works when the asset is replaced under that tag. The downloaded profile is stored
as `cache/mod/lwjgl3ify/lwjgl3ify-<version>-version.json`. There is no fallback to an old
cached copy, the JAR or the latest release. A missing, invalid or mismatched profile stops
assembly before replacing an existing update ZIP. The JVM patch's
`+jvmArgs` list preserves the arguments from `server_assets/forge/java9args.txt`, including
repeated `--add-opens` option/value pairs, and enables `-XX:+UseCompactObjectHeaders` once.
The patch declares Java major version `25` and runtime component `java-runtime-epsilon`.
Compact object headers are a product feature in Java 25, so no additional
`-XX:+UnlockExperimentalVMOptions` flag is needed ([JEP 519](https://openjdk.org/jeps/519)).

This small ZIP is separate from the existing configuration package. Its version is the
normalized release name followed by the first 12 characters of the ZIP's MD5:
`mods/gtnh-java-args/gtnh-java-args-2.9.0-rc-2-<hash>.zip`, for example. Its ZIP timestamp
is fixed so unchanged inputs remain byte-identical. Corrected arguments or a corrected
launcher profile get a new package version without overwriting the old one. Upload it
under `mods/gtnh-java-args/`, then publish.

Use a Technic Launcher version supporting version patches. Automatic Java 25 selection
uses the launcher's **Use Mojang Java runtimes** option; with that option disabled, select
a Java 25 installation manually. The bundled `version.json` supplies lwjgl3ify's libraries
and main class; the JVM patch adds the requested arguments and selects Java 25. The mandatory
Java 25 `modpack` package is still distributed separately.

An exact mod/version already registered in Solder is reused without downloading its
mirror ZIP. For `gtnh-java-args`, publication also checks the stored MD5 and size against
the local ZIP. An existing mod entry alone does not qualify: each new version must
still pass verification.

For a version not yet registered, the update ZIP must contain its package. The publisher
downloads the mirror ZIP and verifies its size and MD5 against that package. No mod or
version is created until all preflight checks have finished successfully. Solder stores
the supplied MD5 and size; publication never requests a server-side rehash. Existing
versions are never overwritten; changed files must use a new package version.

Each package is processed independently. If its version lookup or new ZIP verification or
mirror download fails, the error is reported and checks continue with the next package.
After processing all packages, any failures are listed together and publication stops before
any server writes. Fix the reported files/metadata, then rerun publication.

After successful preflight, publication tries to create the build. If Solder reports
that the target build already exists, including an unpublished draft, the GUI asks
whether to replace it. Declining leaves it untouched. Confirming deletes and recreates
only the target build and its associations; the shared mod/version library is retained.
If preflight or the deletion fails, publication stops.

The Technic Launcher does not offer an update when the build number stays the same.
New installations get the corrected build; players who already installed it need to
reinstall manually. To deliver the fix through the launcher's normal update flow,
publish a new build number and point the relevant channel at it.

Publication creates a new unpublished private build, registers missing mods/versions, and
adds every package selected by the release. Versions already in the global mod library
are reused, without consulting any previous build. It then publishes privately to read back and verify the
manifest (Solder cannot read unpublished builds), makes it public, and finally updates
`latest`. A hidden/private pack stays hidden/private.
Requests are sequential, spaced according to `requests_per_minute` (52.5 ms by default);
HTTP 429 responses are retried
up to three times after `Retry-After`. Per-package verification errors are collected as
described above; errors during shared setup or writes stop immediately.

Publication is not atomic: a replaced version is unavailable between deletion and completed
publication. On failure, the old build may already be gone and the replacement may be absent,
a draft, a private published build, or a public build whose pointer update failed. Fix the
reported error and rerun: after preflight, confirm replacement if the target build still
exists. Registered mod versions are reused. A network timeout leaves the request outcome
uncertain, so inspect the server state before rerunning.
