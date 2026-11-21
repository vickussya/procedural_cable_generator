# README media: shot list

Every image the main [README](../../README.md) expects, with how to record it. Until a file exists here,
GitHub shows a broken-image icon in its place, so **record at least `hero.gif` before announcing the release.**

| File | Used in README section | Type | Length |
|---|---|---|---|
| `hero.gif` | Top of page | GIF | 8–10 s |
| `presets.png` | Creating cables › Cable presets | PNG | still |
| `mode-two-objects.gif` | 1) From 2 Objects | GIF | 5–8 s |
| `mode-chain.gif` | 2) From Selected Objects (Chain) | GIF | 6–8 s |
| `mode-free-cable.gif` | 3) Free Cable (Cursor) | GIF | 6–8 s |
| `mode-coil.gif` | 4) Coil / Roll (Cursor) | GIF | 8–10 s |
| `mode-tied-bundle.gif` | 5) Tied Bundle (2 Objects) | GIF | 6–8 s |
| `dynamics.gif` | Dynamics (Experimental) | GIF | 8–10 s |

## Settings for every shot

- **Resolution:** 1280×720. Record a 1280×720 region of the screen, not the full monitor.
- **GIF:** 15 fps, under ~5 MB each (GitHub may not display very large GIFs). Trim dead time at the start and end.
- **Blender:** default theme, *Solid* shading, grid on. Hide anything unrelated in the scene.
- **Sidebar visible** (`N`, **Cable** tab) whenever a button is clicked, so viewers see where it is.
- Name files exactly as in the table; the README links to these names.
- Dynamics only works in **Blender 5.2+**. The other shots can use any supported version, but using 5.2 for
  all of them keeps the UI consistent.

---

## `hero.gif`: the whole idea in one shot

**What to record:** two objects → one click → a sagging cable → drag a control and the cable follows.

1. New General scene. Delete the default cube. Add two objects about 4 m apart at the same height, e.g. two
   cubes scaled to 0.3 at `(-2, 0, 1)` and `(2, 0, 1)` (a prop and a wall socket look even better).
2. Frame them so both fill the width of the view. Open the sidebar (`N`) → **Cable** tab.
3. **Start recording.**
4. Click the right object, then Shift-click the left one (the last one clicked is the start).
5. In **Cable Preset**, click **Sagging Drop**.
6. Click **Create Cable From 2 Selected Objects**.
7. Click the middle `CTRL_Cable_MID_03` empty, press `G`, and move it sideways and down. The cable follows.
8. **Stop recording** once you release the empty.

## `presets.png`: the five cable presets side by side

**What to record:** a single still with five cables, one per preset, labeled.

1. Add five pairs of objects in rows, each pair 4 m apart (e.g. small cubes at `x = -2` and `x = 2`, rows at
   `y = 0, 1.5, 3, 4.5, 6`).
2. For each row: select its pair, click a preset (**Power Line**, **Street Wires**, **Sagging Drop**,
   **Cable Loom**, **Taut Run**), then click **Create Tied Bundle From 2 Objects**. The bundle button shows the
   bundle settings each preset sets, which is where they differ most.
3. Add a Text object next to each row with the preset's name (`Add > Text`, `Tab` to edit).
4. Frame all five rows from a three-quarter angle above. Take a screenshot (or `View > Viewport Render Image`
   and save it) at 1280×720.

## `mode-two-objects.gif`: ends follow their objects

**What to record:** with **Parent End Controls** on, moving an end object drags the cable with it.

1. Two objects 4 m apart, as in the hero shot.
2. In **From 2 Objects**, set **Middle Controls** to `3` and make sure **Parent End Controls** is on.
   Set **Span Sag** to `-0.1`.
3. **Start recording.** Select both objects (start last), click **Create Cable From 2 Selected Objects**.
4. Select one of the two **objects** (not its empty), press `G` and move it up and around. The cable follows.
5. **Stop recording.**

## `mode-chain.gif`: one cable through several props

**What to record:** a cable routed through 4–5 objects in one click.

1. Add 5 small objects in a loose zigzag along the X axis, e.g. hooks or cubes scaled to 0.15, at varying heights.
2. In **From Selected Objects (Chain)**, set **Chain Order** to **Nearest** and turn **Parent Chain Controls** on.
3. **Start recording.** Box-select all five, then Shift-click the leftmost one so it becomes active (the start).
   If that deselects it instead, it was already active: Shift-click it once more.
4. Click **Create Cable From Selected Objects (Chain)**.
5. Select one of the middle objects, press `G` and move it. The cable follows through it.
6. **Stop recording.**

## `mode-free-cable.gif`: a cable from nothing

**What to record:** a cable created at the 3D cursor, then routed by hand.

1. Empty scene with a floor plane and something to route along, e.g. a box as a desk.
2. `Shift + Right-click` to place the 3D cursor on the desk edge.
3. In **Free Cable**, set **Free Controls** to `6` and **Free Length** to `3 m`.
4. **Start recording.** Click **Create Free Cable (Cursor)**.
5. Select two or three `CTRL_*` empties in turn and move them (`G`) so the cable runs along the desk and drops
   to the floor.
6. **Stop recording.**

## `mode-coil.gif`: each coil preset

**What to record:** four coils appearing, one per preset.

1. Empty scene with a floor plane. View from a three-quarter angle above.
2. **Start recording.**
3. Place the cursor (`Shift + Right-click`), click **Ground Coil** under **Coil / Roll**, then
   **Create Coiled Cable (Cursor)**.
4. Move the cursor and repeat with **Hank**, **Cable Drum** and **Loose Heap**.
5. **Stop recording** once all four exist.

## `mode-tied-bundle.gif`: several cables, tied at the ends

**What to record:** a bundle created in one click, then reshuffled with Seed.

1. Two objects 5 m apart at the same height (e.g. two poles).
2. **Start recording.** Select both (start last), click the **Street Wires** preset, then
   **Create Tied Bundle From 2 Objects**.
3. Press `Ctrl+Z`, raise **Seed** (in *Tied Bundle*) by 1, and click **Create Tied Bundle From 2 Objects** again.
   A different arrangement appears.
4. **Stop recording.**

## `dynamics.gif`: a cable that falls and drapes over a box (Blender 5.2+)

**What to record:** a cable posed as an arch drops under gravity and settles over a box, held at its ends.

This exact setup was replayed headless in Blender 5.2: the cable lands on the box top and stays there (no
sinking in), settling within about 20 frames.

1. Two objects 4 m apart at `z = 2`, e.g. cubes scaled to 0.3 at `(-2, 0, 2)` and `(2, 0, 2)`.
2. Set **Middle Controls** to `3` and **Span Sag** to `+0.25` (positive arches the cable *upward*). Select both
   objects (start last) and click **Create Cable From 2 Selected Objects**.
3. Add a 1 m cube at `(0, 0, 1)` so its top sits at `z = 1.5`, under the middle of the arch.
4. Select the cable and click **Make Dynamic**. Set **Pin Controls** to **Ends Only**.
5. Select the box, Shift-select the cable, and click **Add Selected As Colliders** (in *Collision Setup*).
6. Go to **frame 1**.
7. **Start recording**, press **Play** (`Space`). Don't scrub: the simulation needs to play forward from frame 1.
8. **Stop recording** about a second after the cable has settled on the box.

An animated collider works too (e.g. a sphere keyframed to rise into the cable). Whichever you record, make sure
the collider is where its animation puts it at frame 1 before pressing Play. Starting the simulation with a
collider left right next to the cable and then jumping away kicks the cable hard.
