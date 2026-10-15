# Updated - AE2FluidCraft-Rework - 1.5.110-gtnh --> 1.5.113-gtnh
**Full Changelog**: https://github.com/GTNewHorizons/AE2FluidCraft-Rework/compare/1.5.110-gtnh...1.5.113-gtnh

## What's Changed:
>* Avoid redundant stock lookups in ME Level Maintainer by @Elios5014 in https://github.com/GTNewHorizons/AE2FluidCraft-Rework/pull/474 (1.5.113-gtnh)
>* Use vanilla tooltip renderer for Level Terminal buttons by @Eldrinn-Elantey in https://github.com/GTNewHorizons/AE2FluidCraft-Rework/pull/476 (1.5.112-gtnh)
>* Rename (fluid) Encoded Pattern to Fluid Processing Pattern by @shironakoushi in https://github.com/GTNewHorizons/AE2FluidCraft-Rework/pull/473 (1.5.111-gtnh)

# Updated - Angelica - 2.2.19 --> 2.2.28
Mod is client-side only.
**Full Changelog**: https://github.com/GTNewHorizons/Angelica/compare/2.2.19...2.2.28

## What's Changed:
>* Fix splash issues  by @DeathFuel in https://github.com/GTNewHorizons/Angelica/pull/2200 (2.2.28)
>* Settle frame pacing after an inconsistent vsync gate by @mvanhorn in https://github.com/GTNewHorizons/Angelica/pull/2197 (2.2.28)
>* Default raw custom textures to bilinear filtering and clamping by @zerosignal0101 in https://github.com/GTNewHorizons/Angelica/pull/2198 (2.2.28)
>* Plenty of fixes for GTNH by @Eclipse-Sol in https://github.com/GTNewHorizons/Angelica/pull/2202 (2.2.28)
>* Fix HUD caching flicker and match non-cached GL state by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2201 (2.2.28)
>* Fix crash when mods measure text off-thread with a custom font by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2204 (2.2.28)
>* Add Darkmode Transformer target by @Ranzuu in https://github.com/GTNewHorizons/Angelica/pull/2205 (2.2.28)
>* Cache Iris Shaders by @Eclipse-Sol in https://github.com/GTNewHorizons/Angelica/pull/2206 (2.2.28)
>* Cut per-frame allocations in rendering mixins by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2182 (2.2.27)
>* Add Darkmode Transformer target by @Ranzuu in https://github.com/GTNewHorizons/Angelica/pull/2184 (2.2.27)
>* Fix signs being ungodly bright by @Eclipse-Sol in https://github.com/GTNewHorizons/Angelica/pull/2185 (2.2.27)
>* Fix the look of EFR Boats under batching by @Eclipse-Sol in https://github.com/GTNewHorizons/Angelica/pull/2186 (2.2.27)
>* Fix shader batching and instancing by @Eclipse-Sol in https://github.com/GTNewHorizons/Angelica/pull/2187 (2.2.27)
>* Fix voxeliation performance under SDL GPU by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2188 (2.2.27)
>* Cut redundant GLSM state tracking by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2189 (2.2.27)
>* Speed up boot by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2190 (2.2.27)
>* Work around SDL Metal fence bugs and pump during present by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2191 (2.2.27)
>* Fix DSA binding restore and liquid colors by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2192 (2.2.27)
>* Cut more per-frame allocations in terrain and rendering by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2193 (2.2.27)
>* Cache transformed and compiled shaders on disk by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2194 (2.2.27)
>* Fix Complementary + Euphoria Patches ULTRA on SDL-GPU by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2195 (2.2.27)
>* Fix by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2196 (2.2.27)
>* Improve biome blending and improve compat by @Eclipse-Sol in https://github.com/GTNewHorizons/Angelica/pull/2180 (2.2.26)
>* Internal format fix by @DeathFuel in https://github.com/GTNewHorizons/Angelica/pull/2179 (2.2.26)
>* Add more targets for darkmode transformer by @Ranzuu in https://github.com/GTNewHorizons/Angelica/pull/2178 (2.2.26)
>* Improve shader support for custom block rendering by @Eclipse-Sol in https://github.com/GTNewHorizons/Angelica/pull/2176 (2.2.26)
>* Fix async atlas with KaizPatchX by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2175 (2.2.25)
>* Fix shadow pass receiving a full-bright lightmap constant and misreporting terrain renderStage by @zerosignal0101 in https://github.com/GTNewHorizons/Angelica/pull/2170 (2.2.25)
>* Dark mode text recoloring with resource packs configs by @DeathFuel in https://github.com/GTNewHorizons/Angelica/pull/2118 (2.2.25)
>* Various font improvements and fixes by @DeathFuel in https://github.com/GTNewHorizons/Angelica/pull/2165 (2.2.24)
>* Fix held and dropped blocks rendering off-center (snow golem pumpkin) by @micvog in https://github.com/GTNewHorizons/Angelica/pull/2164 (2.2.24)
>* Parallelize atlas loading and fix SDL-GPU mip-level targets by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2167 (2.2.24)
>* Add option to change mouse movement from Cinematic to Standard while in Angelica Zoom by @Lumarin in https://github.com/GTNewHorizons/Angelica/pull/2166 (2.2.24)
>* Fix Depth Mask Issue for Nametags, etc for Text by @KAMKEEL in https://github.com/GTNewHorizons/Angelica/pull/2168 (2.2.24)
>* Font Texture Crash Fix on Splash Screen by @KAMKEEL in https://github.com/GTNewHorizons/Angelica/pull/2169 (2.2.24)
>* Fix attrib stack overflow from world-less TESR item renderers by @micvog in https://github.com/GTNewHorizons/Angelica/pull/2159 (2.2.23)
>* TESR state and batching leak fixes by @Eclipse-Sol in https://github.com/GTNewHorizons/Angelica/pull/2162 (2.2.23)
>* Update to Celeritas 2.5.12 with translucency sorting v3 by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2151 (2.2.22)
>* Fix NEI items vanishing with ModularUI2 screens open on SDL-GPU by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2153 (2.2.22)
>* Better Biome Blending by @Eclipse-Sol in https://github.com/GTNewHorizons/Angelica/pull/2152 (2.2.22)
>* Add in-game Tracy capture by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2156 (2.2.22)
>* Emulate color logic ops and fix pixel readback on SDL-GPU by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2157 (2.2.22)
>* Fix Iris issues with instancing and batching by @Eclipse-Sol in https://github.com/GTNewHorizons/Angelica/pull/2158 (2.2.22)
>* Stop blocking chunk workers on deferred ISBRH blocks by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2136 (2.2.21)
>* Fix shader packs in modded dimensions by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2137 (2.2.21)
>* Fix scissor clears wiping the whole screen on SDL-GPU by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2138 (2.2.21)
>* Use actual camera when doing cloud related culling and fuctions by @Eclipse-Sol in https://github.com/GTNewHorizons/Angelica/pull/2139 (2.2.21)
>* Optimize Enchant Glint Rendering by @Eclipse-Sol in https://github.com/GTNewHorizons/Angelica/pull/2140 (2.2.21)
>* Give each GL drawable its own GLSM context by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2142 (2.2.21)
>* Weather instancing by @Eclipse-Sol in https://github.com/GTNewHorizons/Angelica/pull/2127 (2.2.20)
>* Only enable shader DH compat if DH is enabled by @DarkShadow44 in https://github.com/GTNewHorizons/Angelica/pull/2130 (2.2.20)
>* Add Galaxy Space compat and fix culling issues by @Eclipse-Sol in https://github.com/GTNewHorizons/Angelica/pull/2131 (2.2.20)
>* Properly reset/flush state for crash interceptors by @mitchej123 in https://github.com/GTNewHorizons/Angelica/pull/2133 (2.2.20)

# Updated - Applied-Energistics-2-Unofficial - rv3-beta-1073-GTNH --> rv3-beta-1080-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/compare/rv3-beta-1073-GTNH...rv3-beta-1080-GTNH

## What's Changed:
>* Copy terminal pins with memory cards by @DreamYao520 in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1680 (rv3-beta-1080-GTNH)
>* Add encoding timestamps to patterns by @DreamYao520 in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1681 (rv3-beta-1079-GTNH)
>* Copy terminal type filters with memory cards by @DreamYao520 in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1670 (rv3-beta-1078-GTNH)
>* Fix Advanced Network Tool slots overflowing in Inscriber and Crystal Growth Chamber by @Eldrinn-Elantey in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1640 (rv3-beta-1078-GTNH)
>* Open the crafting amount screen for out-of-stock pick-block items by @Jesse-njx in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1661 (rv3-beta-1078-GTNH)
>* Restore replacing block with cable parts by @AnsonYeung in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1654 (rv3-beta-1078-GTNH)
>* Fix NEI search overlays rendering on hidden slots by @Kogepan229 in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1674 (rv3-beta-1078-GTNH)
>* perf(crafting): reduce repeated dispatch overhead by @Worive in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1671 (rv3-beta-1078-GTNH)
>* Rename pattern items to match the Pattern Terminal by @shironakoushi in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1678 (rv3-beta-1078-GTNH)
>* Fix pattern terminal focus by @Kogepan229 in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1673 (rv3-beta-1078-GTNH)
>* Allow configuring reshuffler access on ME storage buses by @Worive in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1659 (rv3-beta-1078-GTNH)
>* Fix Advanced Inscriber crash with IC2 by @Kogepan229 in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1677 (rv3-beta-1078-GTNH)
>* Fix NEI recipe transfer for wildcard metadata ingredients by @Kogepan229 in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1676 (rv3-beta-1078-GTNH)
>* Skip EnderIO conduits and GT pipes when naming interfaces by @Eldrinn-Elantey in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1668 (rv3-beta-1078-GTNH)
>* Fix conflicting reshuffle access defaults by @Worive in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1669 (rv3-beta-1077-GTNH)
>* Fix ME terminal lag from re-sorting on every inventory update by @mitchej123 in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1665 (rv3-beta-1076-GTNH)
>* Fix inventory scrollbar's drag state after mouse release by @Ressed in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1666 (rv3-beta-1075-GTNH)
>* fix shift not locking items into place by @MarloGr in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1663 (rv3-beta-1075-GTNH)
>* Prevent inactive GT EU P2P outputs from injecting energy by @Worive in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1667 (rv3-beta-1075-GTNH)
>* fix(middle-click): Prevent middle click craft when an item is picked up by the player by @vermz99 in https://github.com/GTNewHorizons/Applied-Energistics-2-Unofficial/pull/1660 (rv3-beta-1074-GTNH)

# Updated - ArchitectureCraft - 1.12.17 --> 1.12.18
**Full Changelog**: https://github.com/GTNewHorizons/ArchitectureCraft/compare/1.12.17...1.12.18

## What's Changed:
>* making so concrete speeds players up even if modified by architecturecraft by @kin-fuyuki in https://github.com/GTNewHorizons/ArchitectureCraft/pull/51 (1.12.18)

# Updated - Backhand - 1.8.15 --> 1.8.16
**Full Changelog**: https://github.com/GTNewHorizons/Backhand/compare/1.8.15...1.8.16

## What's Changed:
>* Add ExU watering can to default config by @C0bra5 in https://github.com/GTNewHorizons/Backhand/pull/201 (1.8.16)

# Updated - Baubles-Expanded - 2.2.24-GTNH --> 2.2.25-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/Baubles-Expanded/compare/2.2.24-GTNH...2.2.25-GTNH

## What's Changed:
>* Fixed problem with large PlayerId crashing the client. by @Lainiel in https://github.com/GTNewHorizons/Baubles-Expanded/pull/36 (2.2.25-GTNH)

# Updated - BetterP2P - 1.4.7 --> 1.4.8
**Full Changelog**: https://github.com/GTNewHorizons/BetterP2P/compare/1.4.7...1.4.8

## What's Changed:
>* Fix NullPointerException when right-clicking a sound p2p with advance… by @GreatBrandon in https://github.com/GTNewHorizons/BetterP2P/pull/47 (1.4.8)

# Updated - BetterQuesting - 3.8.87-GTNH --> 3.8.89-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/BetterQuesting/compare/3.8.87-GTNH...3.8.89-GTNH

## What's Changed:
>* Only parse PanelTextField text when it's not empty by @koolkrafter5 in https://github.com/GTNewHorizons/BetterQuesting/pull/259 (3.8.89-GTNH)
>* Add extensible quest UI context APIs by @ABKQPO in https://github.com/GTNewHorizons/BetterQuesting/pull/245 (3.8.88-GTNH)

# Updated - BlockRenderer6343 - 1.4.23 --> 1.4.24
**Full Changelog**: https://github.com/GTNewHorizons/BlockRenderer6343/compare/1.4.23...1.4.24

## What's Changed:
>* Fix incorrect PCB Factory hatch highlight by @DreamYao520 in https://github.com/GTNewHorizons/BlockRenderer6343/pull/66 (1.4.24)

# Updated - BloodMagic - 1.9.13 --> 1.9.14
**Full Changelog**: https://github.com/GTNewHorizons/BloodMagic/compare/1.9.13...1.9.14

## What's Changed:
>* Fix item foci not being recognised by the spell table by @micvog in https://github.com/GTNewHorizons/BloodMagic/pull/151 (1.9.14)
>* Fix inverted owner check in Teleport, Watery Grave and Lightning Bolt spells by @micvog in https://github.com/GTNewHorizons/BloodMagic/pull/152 (1.9.14)

# Updated - Botania - 1.13.36-GTNH --> 1.13.37-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/Botania/compare/1.13.36-GTNH...1.13.37-GTNH

## What's Changed:
>* Fix Ring of Far Reach stacking reach on every dimension change by @micvog in https://github.com/GTNewHorizons/Botania/pull/157 (1.13.37-GTNH)

# Updated - BuildCraft - 7.1.63 --> 7.1.64
**Full Changelog**: https://github.com/GTNewHorizons/BuildCraft/compare/7.1.63...7.1.64

## What's Changed:
>* expose some variables for access for guidenh by @ABKQPO in https://github.com/GTNewHorizons/BuildCraft/pull/36 (7.1.64)

# Updated - Chisel - 2.17.33-GTNH --> 2.17.34-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/Chisel/compare/2.17.33-GTNH...2.17.34-GTNH

## What's Changed:
>* Fix Matter Manipulator copying chiseled glowstone by @DreamYao520 in https://github.com/GTNewHorizons/Chisel/pull/106 (2.17.34-GTNH)

# Updated - CropsNH - 2.0.129 --> 2.0.134
**Full Changelog**: https://github.com/GTNewHorizons/CropsNH/compare/2.0.129...2.0.134

## What's Changed:
>* Watering can fix for good this time by @C0bra5 in https://github.com/GTNewHorizons/CropsNH/pull/282 (2.0.134)
>* Default the seed amount to one when planting or harvesting seeds. by @C0bra5 in https://github.com/GTNewHorizons/CropsNH/pull/276 (2.0.133)
>* Cleanup fertilizer recipes declarations by @C0bra5 in https://github.com/GTNewHorizons/CropsNH/pull/275 (2.0.132)
>* Re-add growth reqs in mutation tab by @C0bra5 in https://github.com/GTNewHorizons/CropsNH/pull/274 (2.0.131)
>* Re-add growth reqs in mutation tab by @C0bra5 in https://github.com/GTNewHorizons/CropsNH/pull/274 (2.0.130)

# Updated - EnderIO - 2.10.46 --> 2.10.48
**Full Changelog**: https://github.com/GTNewHorizons/EnderIO/compare/2.10.46...2.10.48

## What's Changed:
>* Prevent fall-through when clicking on the "Show Range" button in Vacuum Chest GUI by @Angry3vilbot in https://github.com/GTNewHorizons/EnderIO/pull/274 (2.10.48)
>* Make specialmobs really availale for soul binder by @fehling135 in https://github.com/GTNewHorizons/EnderIO/pull/270 (2.10.47)

# Updated - Et-Futurum-Requiem - 2.6.59-GTNH --> 2.6.60-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/Et-Futurum-Requiem/compare/2.6.59-GTNH...2.6.60-GTNH

## What's Changed:
>* Prevent dead armor stands from dropping twice by @Chitak985 in https://github.com/GTNewHorizons/Et-Futurum-Requiem/pull/125 (2.6.60-GTNH)

# Updated - FindIt - 1.4.6 --> 1.4.7
**Full Changelog**: https://github.com/GTNewHorizons/FindIt/compare/1.4.6...1.4.7

## What's Changed:
>* Fix incorrect block highlights with Cubic Chunks by @5-Esania in https://github.com/GTNewHorizons/FindIt/pull/38 (1.4.7)

# Updated - ForestryMC - 4.11.38 --> 4.11.39
**Full Changelog**: https://github.com/GTNewHorizons/ForestryMC/compare/4.11.38...4.11.39

## What's Changed:
>* Fix alveary inventory drops on chunk unload by @Worive in https://github.com/GTNewHorizons/ForestryMC/pull/134 (4.11.39)

# Updated - ForgeMultipart - 1.7.15 --> 1.7.16
**Full Changelog**: https://github.com/GTNewHorizons/ForgeMultipart/compare/1.7.15...1.7.16

## What's Changed:
>* Fix MissingMicroMaterial microblock crafted instead of Minecraft:stone by @Ressed in https://github.com/GTNewHorizons/ForgeMultipart/pull/61 (1.7.16)

# Updated - GT5-Unofficial - 5.09.54.183 --> 5.09.54.205
**Full Changelog**: https://github.com/GTNewHorizons/GT5-Unofficial/compare/5.09.54.183...5.09.54.205

## What's Changed:
>* increase detector hatch amount from 20 to 41 by @boubou19 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8324 (5.09.54.205)
>* Fix Config option invertCircuitScrollDirection in both MUI1 and MUI2 by @Ressed in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8226 (5.09.54.204)
>* Cryogenic Freezer: localize the tooltip by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8284 (5.09.54.203)
>* Make MSHP stacksize equal to LINAC length by @fehling135 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8308 (5.09.54.202)
>* fix: oc calc fp err caused eut err by @Nana-Sakura in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8012 (5.09.54.202)
>* Kubatech tooltips by @MLGfruitshoot in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8293 (5.09.54.202)
>* Change `outputted` to `output` so it flows better by @SuperficialCake in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8301 (5.09.54.202)
>* fix wetware calibration line format error by @chrombread in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8313 (5.09.54.202)
>* Fix item deleted while shift-click in Extreme Industrial Greenhouse inventory GUI by @Ressed in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8180 (5.09.54.202)
>* Algae, charcoal pit and cleanroom tooltips by @MLGfruitshoot in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8314 (5.09.54.202)
>* Fix "Active Transformer voids energy when trying to fill a big laser hatch with several smaller, partially filled laser hatches" by @Xela10001 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8304 (5.09.54.202)
>* fix bec coil taking a c4 instead of a c4 coil by @chrombread in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8317 (5.09.54.202)
>* Support spray painting ProjectRed bundled cables by @DreamYao520 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8309 (5.09.54.202)
>* Unify circuit tooltips to match their tiers by @shironakoushi in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8307 (5.09.54.201)
>* Sync the Russian IMS tooltip with the merged English text by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8305 (5.09.54.200)
>* Unify: Give the Circuit Assembler the standard tier names by @shironakoushi in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8268 (5.09.54.200)
>* improve pgs tooltip by @MLGfruitshoot in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8201 (5.09.54.199)
>* Industrial Maceration Stack: show controller tier and localize the tooltip by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8283 (5.09.54.199)
>* Beam Crafter - Allow particle buffering with no active recipe by @ham-corp in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8303 (5.09.54.199)
>* Linked Input Bus: name interfaces after the multiblock by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8110 (5.09.54.198)
>* fix nac module structure build giving the wrong output message by @chrombread in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8302 (5.09.54.197)
>* Fix MTEBuffer handling of heterogeneous target inventories by @lfpraca in https://github.com/GTNewHorizons/GT5-Unofficial/pull/7850 (5.09.54.196)
>* Render GT fluids with custom renderers in NEI by @slprime in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8295 (5.09.54.196)
>* Tooltip recolour by @MLGfruitshoot in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8205 (5.09.54.196)
>* Remove duplicate lanthanum hexaboride EIC recipe by @DreamYao520 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8300 (5.09.54.196)
>* Fix NAC splitter rule deletion UI desync issues by @serenibyss in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8297 (5.09.54.196)
>* Add TooltipHelper.anyCasingText and use it in markdown multiblocks by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8292 (5.09.54.195)
>* add ability to use data stick / mm to copy foundry data by @chrombread in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8291 (5.09.54.194)
>* improve the eoh tooltip by @MLGfruitshoot in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8216 (5.09.54.194)
>* Improve Godforge info panel by @serenibyss in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8294 (5.09.54.194)
>* [BEC] Casing Recipe Adjustments by @Auynonymous in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8182 (5.09.54.194)
>* Fix IsaMill front texture missing on casings around the controller by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8288 (5.09.54.194)
>* Void miner tooltips by @MLGfruitshoot in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8265 (5.09.54.193)
>* aal cal assline tooltips by @MLGfruitshoot in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8264 (5.09.54.193)
>* Keep the configured batch mode default when placing a multiblock with item NBT by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8281 (5.09.54.193)
>* Move remaining creative tab, enchantment, fluid and comb names into the asset lang by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8254 (5.09.54.193)
>* Add a cooldown to NAC module running on changing ratio by @serenibyss in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8282 (5.09.54.193)
>* remove kubatech locale mixin by @danyadev in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8209 (5.09.54.193)
>* Make Warded Glass EV-tier by @DreamYao520 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8277 (5.09.54.193)
>* add scroll option to nac power slider by @chrombread in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8290 (5.09.54.193)
>* Use latin Bio Vat culture names and drop the unused latin tooltip by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8279 (5.09.54.193)
>* Remove unused world-aware getIcon overrides from casing blocks by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8289 (5.09.54.193)
>* Add configurable refresh time to ME output hatches and buses by @mak8427 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8106 (5.09.54.193)
>* Translate structure subchannel names by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8286 (5.09.54.193)
>* Fusion tooltips by @MLGfruitshoot in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8242 (5.09.54.193)
>* Translate multiblock tooltip labels per builder instead of once at class load by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8285 (5.09.54.193)
>* [BEC] Fix BEC entangle apparatus's EU consumption & change its logic by @fehling135 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/7992 (5.09.54.193)
>* Add direct electrolysis for liquid calcium fluoride by @DreamYao520 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8199 (5.09.54.193)
>* Fix NAC power routing issues on non-laser hatches by @serenibyss in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8274 (5.09.54.192)
>* Name the Rock Breaker free item from a lang key on display by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8258 (5.09.54.192)
>* Name wildcard blocks through one lang key instead of GTLanguageManager by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8252 (5.09.54.192)
>* show recipe stackstace on hover by @danyadev in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8212 (5.09.54.192)
>* Fix NAC color separation not working properly by @serenibyss in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8271 (5.09.54.192)
>* Fix NAC calibration saving issues by @serenibyss in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8280 (5.09.54.192)
>* give FBID automatic flushing functionality with redstone by @chrombread in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8269 (5.09.54.191)
>* Revert generics fix, update buildscript and AE2 by @Kogepan229 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8275 (5.09.54.191)
>* Fix GT FluidDisplay NBT by @slprime in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8276 (5.09.54.191)
>* NEI FluidStack migration by @danyadev in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8217 (5.09.54.191)
>* Remove side name registration from GTLanguageManager by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8246 (5.09.54.190)
>* Unify the invalid A/t unit from the amperage strings by @shironakoushi in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8243 (5.09.54.190)
>* Fix generics errors caused by buildscript update by @Nikolay-Sitnikov in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8250 (5.09.54.190)
>* Build field generator names from one key per family by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8248 (5.09.54.190)
>* Remove 144 unused interface strings from GTLanguageManager by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8253 (5.09.54.190)
>* Localize fluid cell names on display instead of freezing them at startup by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8255 (5.09.54.190)
>* Move material flavor texts and pipe names into the asset lang by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8260 (5.09.54.190)
>* Sync outdated GT++ tooltip strings in the Russian lang by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8263 (5.09.54.190)
>* Add missing periods to two purification unit tooltips by @GhostCoder6969 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8266 (5.09.54.190)
>* Fix EEC WoS Mode when doDaylightCycle is false by @s-yh-china in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8244 (5.09.54.190)
>* Add the missing localization key for the Vajra item name by @shironakoushi in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8241 (5.09.54.190)
>* Unify the missing "Steam" to the High Pressure Alloy Smelter name by @shironakoushi in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8239 (5.09.54.190)
>* Fix crash when holding a wildcard machine item by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8256 (5.09.54.190)
>* Fix shutdown reasons showing in the server language by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8245 (5.09.54.190)
>* fix null error in cc nei representation by @chrombread in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8267 (5.09.54.190)
>* Make FRF Coils AAL Friendly by @Auynonymous in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8227 (5.09.54.189)
>* adjust late game turbine tiers for spinmatron by @chrombread in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8224 (5.09.54.189)
>* uncaps OCs for spinmatron heavy mode by @chrombread in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8225 (5.09.54.189)
>* Spinmatron tooltip by @MLGfruitshoot in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8196 (5.09.54.189)
>* Fix Microwave Transmitter Cross-dim Without Nitrogen Plasma by @fehling135 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8228 (5.09.54.189)
>* Fix ME output hatch and bus tooltips by @DreamYao520 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8230 (5.09.54.188)
>* change primitive calibration text to be more succinct by @chrombread in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8233 (5.09.54.188)
>* Issue 26952 by @PierceC7 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8213 (5.09.54.188)
>* Add ingotHotBrickNether into the IngotHot prefix by @Ressed in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8235 (5.09.54.188)
>* VCO/VCI name alias by @MarloGr in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8236 (5.09.54.188)
>* Big typo by @MLGfruitshoot in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8222 (5.09.54.187)
>* Add NEI dumper for space miner asteroids by @C0bra5 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8168 (5.09.54.187)
>* Give the late game pumps and fluid regulators the same four times rate growth as the conveyors by @shironakoushi in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8215 (5.09.54.186)
>* Fix Chunk Info showing raw fluid key instead of fluid name by @Eldrinn-Elantey in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8218 (5.09.54.186)
>* fix a typo in calabi yau manifold item by @chrombread in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8211 (5.09.54.185)
>* Optical fiber cable consistency by @PierceC7 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8202 (5.09.54.184)
>* Changed ICO Multi Amp Hatch Error Message by @PierceC7 in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8198 (5.09.54.184)
>* cryo tooltip by @MLGfruitshoot in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8203 (5.09.54.184)
>* Fix NAC sound range by @GreatBrandon in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8200 (5.09.54.184)
>* Fix non-electric basic machines showing a EU bar in WAILA by @Ranzuu in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8210 (5.09.54.184)
>* fix: nac keeps calibration on game reload by @MarloGr in https://github.com/GTNewHorizons/GT5-Unofficial/pull/8207 (5.09.54.184)

# Updated - GTNHExtLib - 1.0.4 --> 1.0.5
**Full Changelog**: https://github.com/GTNewHorizons/GTNHExtLib/compare/1.0.4...1.0.5

## What's Changed:
>* Delegate JVM to the child class loader by @mitchej123 in https://github.com/GTNewHorizons/GTNHExtLib/pull/9 (1.0.5)

# Updated - GTNHLib - 0.11.51 --> 0.11.52
**Full Changelog**: https://github.com/GTNewHorizons/GTNHLib/compare/0.11.51...0.11.52

## What's Changed:
>* Bump nhextlib and add jvmdg child delegation by @mitchej123 in https://github.com/GTNewHorizons/GTNHLib/pull/478 (0.11.52)

# Updated - Gadomancy - 1.5.16 --> 1.5.17
**Full Changelog**: https://github.com/GTNewHorizons/Gadomancy/compare/1.5.16...1.5.17

## What's Changed:
>* Fix duplicate ResearchItem constructors to avoid id collision by @Antaresque in https://github.com/GTNewHorizons/Gadomancy/pull/62 (1.5.17)

# Updated - Galaxy-Space-GTNH - 1.1.142-GTNH --> 1.1.143-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/Galaxy-Space-GTNH/compare/1.1.142-GTNH...1.1.143-GTNH

## What's Changed:
>* Make clouds respect client's render distance by @Eclipse-Sol in https://github.com/GTNewHorizons/Galaxy-Space-GTNH/pull/157 (1.1.143-GTNH)

# Updated - GuideNH - 1.3.36 --> 1.3.41
**Full Changelog**: https://github.com/GTNewHorizons/GuideNH/compare/1.3.36...1.3.41

## What's Changed:
>* remove all unnecessary feature integration mixins by @ABKQPO in https://github.com/GTNewHorizons/GuideNH/pull/94 (1.3.41)
>* Site fix by @ABKQPO in https://github.com/GTNewHorizons/GuideNH/pull/91 (1.3.40)
>* fix exportsite tooltip render by @ABKQPO in https://github.com/GTNewHorizons/GuideNH/pull/93 (1.3.40)
>* Optimize ExportSite by @ABKQPO in https://github.com/GTNewHorizons/GuideNH/pull/90 (1.3.39)
>* enhanced web editor, rework export site by @ABKQPO in https://github.com/GTNewHorizons/GuideNH/pull/88 (1.3.38)
>* Unify path resolution by @ABKQPO in https://github.com/GTNewHorizons/GuideNH/pull/89 (1.3.38)
>* Add MediaWiki style MDX templates for guide pages by @ABKQPO in https://github.com/GTNewHorizons/GuideNH/pull/84 (1.3.37)
>* Create GuideNH web view editor github page by @ABKQPO in https://github.com/GTNewHorizons/GuideNH/pull/87 (1.3.37)

# Updated - Hodgepodge - 2.7.211 --> 2.7.215
**Full Changelog**: https://github.com/GTNewHorizons/Hodgepodge/compare/2.7.211...2.7.215

## What's Changed:
>* Fix Thaumcraft labyrinth data key in threaded saves by @Chitak985 in https://github.com/GTNewHorizons/Hodgepodge/pull/1006 (2.7.215)
>* Fix potion timers longer than 27 minutes by @Eldrinn-Elantey in https://github.com/GTNewHorizons/Hodgepodge/pull/970 (2.7.215)
>* Fix items placed on Bibliocraft shelves and tables not being saved by @micvog in https://github.com/GTNewHorizons/Hodgepodge/pull/1013 (2.7.214)
>* Fix chunks loading outdated data while their save is being written by @micvog in https://github.com/GTNewHorizons/Hodgepodge/pull/1018 (2.7.213)
>* Fix bed height overflow on multiplayer by @DreamYao520 in https://github.com/GTNewHorizons/Hodgepodge/pull/1016 (2.7.213)
>* fix reactor crash by @MarloGr in https://github.com/GTNewHorizons/Hodgepodge/pull/1022 (2.7.213)
>* Fix BOP generating vanilla emerald ore regardless of config by @Ressed in https://github.com/GTNewHorizons/Hodgepodge/pull/1014 (2.7.213)
>* Fix Flatworld Customization NPE by @Eclipse-Sol in https://github.com/GTNewHorizons/Hodgepodge/pull/956 (2.7.212)

# Updated - LittleTiles - 1.6.53 --> 1.6.59
**Full Changelog**: https://github.com/GTNewHorizons/LittleTiles/compare/1.6.53...1.6.59

## What's Changed:
>* Refactor in preparation for a big update by @DarkShadow44 in https://github.com/GTNewHorizons/LittleTiles/pull/187 (1.6.59)
>* Improve dumping command by @DarkShadow44 in https://github.com/GTNewHorizons/LittleTiles/pull/186 (1.6.59)
>* Implement Little Bag by @DarkShadow44 in https://github.com/GTNewHorizons/LittleTiles/pull/137 (1.6.59)
>* Deformable boxes by @DarkShadow44 in https://github.com/GTNewHorizons/LittleTiles/pull/169 (1.6.58)
>* Fix raytrace to allow placing tiles against shapes by @DarkShadow44 in https://github.com/GTNewHorizons/LittleTiles/pull/184 (1.6.58)
>* Add undo/redo keys by @S4mpsa in https://github.com/GTNewHorizons/LittleTiles/pull/141 (1.6.58)
>* Allow chisel two hit mode to select and move corners with marked hit - #178 by @DarkShadow44 in https://github.com/GTNewHorizons/LittleTiles/pull/185 (1.6.58)
>* Threadsafety fixes by @DarkShadow44 in https://github.com/GTNewHorizons/LittleTiles/pull/159 (1.6.58)
>* Hardening by @DarkShadow44 in https://github.com/GTNewHorizons/LittleTiles/pull/171 (1.6.57)
>* Add smooth lighting for cutouts if Angelica is present by @DarkShadow44 in https://github.com/GTNewHorizons/LittleTiles/pull/175 (1.6.55)
>* Hardening by @DarkShadow44 in https://github.com/GTNewHorizons/LittleTiles/pull/171 (1.6.54)
>* Allow chisel two hit mode to select and move corners with marked hit by @DarkShadow44 in https://github.com/GTNewHorizons/LittleTiles/pull/178 (1.6.54)

# Updated - MatterManipulator - 0.1.59-GTNH --> 0.1.61-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/MatterManipulator/compare/0.1.59-GTNH...0.1.61-GTNH

## What's Changed:
>* Fix planning AE cells by @Azusfin in https://github.com/GTNewHorizons/MatterManipulator/pull/91 (0.1.61-GTNH)
>* Fix GT IItemLockable compatibility by @Azusfin in https://github.com/GTNewHorizons/MatterManipulator/pull/90 (0.1.60-GTNH)

# Updated - Minecraft-Backpack-Mod - 2.6.17-GTNH --> 2.6.18-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/Minecraft-Backpack-Mod/compare/2.6.17-GTNH...2.6.18-GTNH

## What's Changed:
>* Block opening a backpack another player already has open by @Eldrinn-Elantey in https://github.com/GTNewHorizons/Minecraft-Backpack-Mod/pull/38 (2.6.18-GTNH)

# Updated - ModularUI2 - 2.3.91-1.7.10 --> 2.3.92-1.7.10
**Full Changelog**: https://github.com/GTNewHorizons/ModularUI2/compare/2.3.91-1.7.10...2.3.92-1.7.10

## What's Changed:
>* give slider widgets the ability to scroll to change values by @chrombread in https://github.com/GTNewHorizons/ModularUI2/pull/167 (2.3.92-1.7.10)

# Updated - NewHorizonsCoreMod - 2.9.76 --> 2.9.84
**Full Changelog**: https://github.com/GTNewHorizons/NewHorizonsCoreMod/compare/2.9.76...2.9.84

## What's Changed:
>* Unify wooden door assembler recipes by @DreamYao520 in https://github.com/GTNewHorizons/NewHorizonsCoreMod/pull/1981 (2.9.84)
>* remove lumipod sapling from infused seed drop table by @chrombread in https://github.com/GTNewHorizons/NewHorizonsCoreMod/pull/1985 (2.9.84)
>* Add illumar buttons to assembler by @boubou19 in https://github.com/GTNewHorizons/NewHorizonsCoreMod/pull/1983 (2.9.83)
>* Remove furnace charcoal recipes for Fether and Extra Trees logs by @DreamYao520 in https://github.com/GTNewHorizons/NewHorizonsCoreMod/pull/1982 (2.9.82)
>* Fix/futurum stripped logs to planks by @vakus in https://github.com/GTNewHorizons/NewHorizonsCoreMod/pull/1952 (2.9.82)
>* Fix UEV circuit recycling drops by @Worive in https://github.com/GTNewHorizons/NewHorizonsCoreMod/pull/1979 (2.9.81)
>* Fix bookshelf assembler recipes for modded planks by using oredict and adding circuit by @Ressed in https://github.com/GTNewHorizons/NewHorizonsCoreMod/pull/1977 (2.9.81)
>* Remove Lootbag Upgrade Assembler Recipes by @UltraProdigy in https://github.com/GTNewHorizons/NewHorizonsCoreMod/pull/1978 (2.9.80)
>* Fix Gardener Coin sprite by Embri by @YannickMG in https://github.com/GTNewHorizons/NewHorizonsCoreMod/pull/1975 (2.9.79)
>* add the UV monster repellator to assembler recipes by @chrombread in https://github.com/GTNewHorizons/NewHorizonsCoreMod/pull/1970 (2.9.78)
>* Add Hardness to Metal Bars by @fehling135 in https://github.com/GTNewHorizons/NewHorizonsCoreMod/pull/1972 (2.9.78)
>* add the UV monster repellator to assembler recipes by @chrombread in https://github.com/GTNewHorizons/NewHorizonsCoreMod/pull/1970 (2.9.77)
>* Add Hardness to Metal Bars by @fehling135 in https://github.com/GTNewHorizons/NewHorizonsCoreMod/pull/1972 (2.9.77)

# Updated - NotEnoughEnergistics - 1.7.45 --> 1.7.46
**Full Changelog**: https://github.com/GTNewHorizons/NotEnoughEnergistics/compare/1.7.45...1.7.46

## What's Changed:
>* Use selected item on transfer in arcane inscriber by @Azusfin in https://github.com/GTNewHorizons/NotEnoughEnergistics/pull/87 (1.7.46)

# Updated - NotEnoughItems - 2.8.145-GTNH --> 2.8.155-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/NotEnoughItems/compare/2.8.145-GTNH...2.8.155-GTNH

## What's Changed:
>* Add Custom Renderer API for Fluids by @slprime in https://github.com/GTNewHorizons/NotEnoughItems/pull/1059 (2.8.155-GTNH)
>* Fix Subset Width Calculation by @slprime in https://github.com/GTNewHorizons/NotEnoughItems/pull/1058 (2.8.154-GTNH)
>* Fix EnderIo Tank by @slprime in https://github.com/GTNewHorizons/NotEnoughItems/pull/1056 (2.8.153-GTNH)
>* Fix NPE on GT fluid display without NBT by @slprime in https://github.com/GTNewHorizons/NotEnoughItems/pull/1057 (2.8.153-GTNH)
>* Recipe Group Optimization by @slprime in https://github.com/GTNewHorizons/NotEnoughItems/pull/1054 (2.8.152-GTNH)
>* fix cycling for fluid permutations by @danyadev in https://github.com/GTNewHorizons/NotEnoughItems/pull/1048 (2.8.151-GTNH)
>* Add widget size to recipe event by @slprime in https://github.com/GTNewHorizons/NotEnoughItems/pull/1053 (2.8.150-GTNH)
>* Save Tree State by @slprime in https://github.com/GTNewHorizons/NotEnoughItems/pull/1052 (2.8.149-GTNH)
>* Add Recipe Groups to GuiRecipe by @slprime in https://github.com/GTNewHorizons/NotEnoughItems/pull/1049 (2.8.148-GTNH)
>* Rename PositionStack.Fluid to Tank by @slprime in https://github.com/GTNewHorizons/NotEnoughItems/pull/1051 (2.8.148-GTNH)
>* Fix search autofocus losing the first typed character by @slprime in https://github.com/GTNewHorizons/NotEnoughItems/pull/1045 (2.8.147-GTNH)
>* Fix Keybinding Category Names by @slprime in https://github.com/GTNewHorizons/NotEnoughItems/pull/1046 (2.8.147-GTNH)
>* Add Flowinf Texture to PositionStack by @slprime in https://github.com/GTNewHorizons/NotEnoughItems/pull/1047 (2.8.147-GTNH)
>* Refactoring Chain Tooltip by @slprime in https://github.com/GTNewHorizons/NotEnoughItems/pull/1044 (2.8.146-GTNH)

# Updated - Nuclear-Control - 2.7.14 --> 2.7.16
**Full Changelog**: https://github.com/GTNewHorizons/Nuclear-Control/compare/2.7.14...2.7.16

## What's Changed:
>* Fix ClassCastException when info panel text renders without Angelica font mixin by @HalfCooler in https://github.com/GTNewHorizons/Nuclear-Control/pull/52 (2.7.16)
>* Fix howler alarm sound behaviors by @boubou19 in https://github.com/GTNewHorizons/Nuclear-Control/pull/51 (2.7.15)

# Updated - OpenComputers - 1.12.62-GTNH --> 1.12.64-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/OpenComputers/compare/1.12.62-GTNH...1.12.64-GTNH

## What's Changed:
>* Raise default max signal queue size to 1024 by @shironakoushi in https://github.com/GTNewHorizons/OpenComputers/pull/226 (1.12.64-GTNH)
>* Fluid Interface 1-indexed API by @Azusfin in https://github.com/GTNewHorizons/OpenComputers/pull/225 (1.12.63-GTNH)

# Updated - Postea - 1.2.6 --> 1.2.7
**Full Changelog**: https://github.com/GTNewHorizons/Postea/compare/1.2.6...1.2.7

## What's Changed:
>* better compat with other mixins for AnvilChunkLoader.readChunkFromNBT by @danyadev in https://github.com/GTNewHorizons/Postea/pull/27 (1.2.7)

# Updated - ProjectBlue - 1.2.10-GTNH --> 1.2.11-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/ProjectBlue/compare/1.2.10-GTNH...1.2.11-GTNH

## What's Changed:
>* Fix control panel labels: second line drawn inside the control by @micvog in https://github.com/GTNewHorizons/ProjectBlue/pull/10 (1.2.11-GTNH)

# Updated - ProjectRed - 4.12.44-GTNH --> 4.12.47-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/ProjectRed/compare/4.12.44-GTNH...4.12.47-GTNH

## What's Changed:
>* Allow spray cans to recolor bundled cables by @DreamYao520 in https://github.com/GTNewHorizons/ProjectRed/pull/98 (4.12.47-GTNH)
>* Added textured scroll bars for pan nodes by @Ranzuu in https://github.com/GTNewHorizons/ProjectRed/pull/92 (4.12.46-GTNH)
>* Fixed missing right and bottom border on the IC redraw name textbox by @Ranzuu in https://github.com/GTNewHorizons/ProjectRed/pull/94 (4.12.46-GTNH)
>* Fix flipped comparator sign rendering by @Algent in https://github.com/GTNewHorizons/ProjectRed/pull/97 (4.12.45-GTNH)

# Updated - ServerUtilities - 2.4.13 --> 2.4.14
**Full Changelog**: https://github.com/GTNewHorizons/ServerUtilities/compare/2.4.13...2.4.14

## What's Changed:
>* Handle perm check on incomplete profiles by @Niki4tap in https://github.com/GTNewHorizons/ServerUtilities/pull/342 (2.4.14)
>* Remove FTB import leftovers from the translated lang files by @sivaDog in https://github.com/GTNewHorizons/ServerUtilities/pull/348 (2.4.14)

# Updated - SpecialMobs - 3.7.7 --> 3.7.8
**Full Changelog**: https://github.com/GTNewHorizons/SpecialMobs/compare/3.7.7...3.7.8

## What's Changed:
>* Prevent Witch Cave Spider infinite projectile duplication by @Ressed in https://github.com/GTNewHorizons/SpecialMobs/pull/35 (3.7.8)

# Updated - ThaumicEnergistics - 1.7.60-GTNH --> 1.7.64-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/ThaumicEnergistics/compare/1.7.60-GTNH...1.7.64-GTNH

## What's Changed:
>* fix: refresh provider connections when changing color by @Worive in https://github.com/GTNewHorizons/ThaumicEnergistics/pull/145 (1.7.64-GTNH)
>* Fix Arcane Assembler dividing by zero on patterns with a zero-size ingredient (Warded Glass) by @micvog in https://github.com/GTNewHorizons/ThaumicEnergistics/pull/144 (1.7.63-GTNH)
>* Show vis interface links in Waila by @Eldrinn-Elantey in https://github.com/GTNewHorizons/ThaumicEnergistics/pull/142 (1.7.62-GTNH)
>* Fix: set worked flag for essential import bus by @Ressed in https://github.com/GTNewHorizons/ThaumicEnergistics/pull/143 (1.7.61-GTNH)

# Updated - ThaumicHorizons - 1.8.25 --> 1.8.27
**Full Changelog**: https://github.com/GTNewHorizons/ThaumicHorizons/compare/1.8.25...1.8.27

## What's Changed:
>* fix liquefaction focus not making lava by @Edgaru089 in https://github.com/GTNewHorizons/ThaumicHorizons/pull/147 (1.8.27)
>* Fix Synthskin draining Nutrition while the hunger bar is full by @micvog in https://github.com/GTNewHorizons/ThaumicHorizons/pull/148 (1.8.26)

# Updated - ThaumicMachina - 0.2.5-GTNH --> 0.2.6-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/ThaumicMachina/compare/0.2.5-GTNH...0.2.6-GTNH

## What's Changed:
DreamAssemblerXXL wasn't able to find the changelog related to this update. It is usually caused by updates done outside of pull-requests or if the mod is maintained by a 3rd party.
# Updated - Thaumic_Exploration - 1.5.28-GTNH --> 1.5.29-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/Thaumic_Exploration/compare/1.5.28-GTNH...1.5.29-GTNH

## What's Changed:
>* Fix Everburn Urn tank capacity and remove broken WAILA lava line by @Eldrinn-Elantey in https://github.com/GTNewHorizons/Thaumic_Exploration/pull/65 (1.5.29-GTNH)

# Updated - TinkersConstruct - 1.14.115-GTNH --> 1.14.118-GTNH
**Full Changelog**: https://github.com/GTNewHorizons/TinkersConstruct/compare/1.14.115-GTNH...1.14.118-GTNH

## What's Changed:
>* Backport the Width++ and Height++ expanders from TiC2 by @Aintripin in https://github.com/GTNewHorizons/TinkersConstruct/pull/341 (1.14.118-GTNH)
>* reduce lag from large smelteries by @Pxx500 in https://github.com/GTNewHorizons/TinkersConstruct/pull/338 (1.14.117-GTNH)
>* fix nei bookmark pull from crafting station inventories by @Pxx500 in https://github.com/GTNewHorizons/TinkersConstruct/pull/345 (1.14.116-GTNH)

# Updated - VendingMachine - 0.4.100 --> 0.4.101
**Full Changelog**: https://github.com/GTNewHorizons/VendingMachine/compare/0.4.100...0.4.101

## What's Changed:
>* Make category tabs and IO panel scrollable on small GUI scales by @Ranzuu in https://github.com/GTNewHorizons/VendingMachine/pull/168 (0.4.101)
>* Keep background music (silently) playing when not inside the GUI by @wlhlm in https://github.com/GTNewHorizons/VendingMachine/pull/169 (0.4.101)

# Updated - lwjgl3ify - 3.0.35 --> 3.0.37
**Full Changelog**: https://github.com/GTNewHorizons/lwjgl3ify/compare/3.0.35...3.0.37

## What's Changed:
>* Fix applying incorrect delta on cursor grab by @danyadev in https://github.com/GTNewHorizons/lwjgl3ify/pull/374 (3.0.37)
>* Fix Windows taskbar showing the Java icon instead of the window icon by @Eldrinn-Elantey in https://github.com/GTNewHorizons/lwjgl3ify/pull/375 (3.0.36)

# Updated - nei-custom-diagram - 1.8.35 --> 1.8.36
**Full Changelog**: https://github.com/GTNewHorizons/nei-custom-diagram/compare/1.8.35...1.8.36

## What's Changed:
>* Fixed search for GT fluids by @slprime in https://github.com/GTNewHorizons/nei-custom-diagram/pull/82 (1.8.36)
>* expose some variables for access for guidenh by @ABKQPO in https://github.com/GTNewHorizons/nei-custom-diagram/pull/81 (1.8.36)

# Updated - twilightforest - 2.7.42 --> 2.7.44
**Full Changelog**: https://github.com/GTNewHorizons/twilightforest/compare/2.7.42...2.7.44

## What's Changed:
>* Fix some saplings never grow on modded soils by @Ressed in https://github.com/GTNewHorizons/twilightforest/pull/163 (2.7.44)
>* Optimize sorting tree logic by @fehling135 in https://github.com/GTNewHorizons/twilightforest/pull/164 (2.7.43)

# Credits
Special thanks to @5-Esania, @ABKQPO, @Aintripin, @Algent, @Angry3vilbot, @AnsonYeung, @Antaresque, @Auynonymous, @Azusfin, @boubou19, @C0bra5, @Chitak985, @chrombread, @danyadev, @DarkShadow44, @DeathFuel, @DreamYao520, @Eclipse-Sol, @Edgaru089, @Eldrinn-Elantey, @Elios5014, @fehling135, @GhostCoder6969, @GreatBrandon, @HalfCooler, @ham-corp, @Jesse-njx, @KAMKEEL, @kin-fuyuki, @Kogepan229, @koolkrafter5, @Lainiel, @lfpraca, @Lumarin, @mak8427, @MarloGr, @micvog, @mitchej123, @MLGfruitshoot, @mvanhorn, @Nana-Sakura, @Niki4tap, @Nikolay-Sitnikov, @PierceC7, @Pxx500, @Ranzuu, @Ressed, @s-yh-china, @S4mpsa, @serenibyss, @shironakoushi, @sivaDog, @slprime, @SuperficialCake, @UltraProdigy, @vakus, @vermz99, @wlhlm, @Worive, @Xela10001, @YannickMG, @zerosignal0101, for their code contributions listed above, and to everyone else who helped, including all of our beta testers! <3
