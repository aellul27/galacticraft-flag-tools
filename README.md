# Galacticraft Flag Tools

A Python script to edit Space Race flag images in Galacticraft Minecraft save files.

## Features

- **List all Space Races** in a world save with their details
- **Export flags** to PNG images
- **Import custom images** as flags (automatically resized and color-converted)
- Works with both legacy and modern NBT flag formats
- Preserves all other space race data (team name, players, celestial bodies, etc.)

## Installation

1. Make sure you have Python 3.7+ installed
2. Install the required dependencies:

```bash
pip install -r flag_editor_requirements.txt
```

Or manually:

```bash
pip install nbtlib Pillow
```

## Usage

### List Space Races

To see all space races in a world:

```bash
python flag_editor.py /path/to/minecraft/saves/YourWorld
```

Example output:
```
============================================================
SPACE RACES
============================================================

[0] Space Race #1: Team Alpha
  Players: Steve, Alex
  Flag Size: 48x32
  Team Color: RGB(1.00, 0.50, 0.25)
  Celestial Bodies Visited: planet.moon, planet.mars
  Ticks Spent: 123456

[1] Space Race #2: Team Beta
  Players: Notch
  Flag Size: 48x32
  Team Color: RGB(0.25, 0.75, 1.00)
  Celestial Bodies Visited: planet.moon
  Ticks Spent: 78910
============================================================
```

### Export a Flag

Export a flag to an image file:

```bash
python flag_editor.py /path/to/saves/YourWorld --export 0 --output my_flag.png
```

This will save the flag from Space Race #0 to `my_flag.png`.

### Import a Custom Flag

Replace a flag with a custom image:

```bash
python flag_editor.py /path/to/saves/YourWorld --import 0 --image custom_flag.png
```

The script will:
- Automatically resize your image to 48x32 pixels (Galacticraft's flag dimensions)
- Convert colors to the correct format
- Save the modified data back to the world

### Import modes

When importing an image you can choose how the image is fitted to the 48x32 flag canvas using the `--mode` option (default: `stretch`):

- `stretch` (default): the image is resized to exactly 48x32 and may be distorted if the aspect ratio differs. This is the original behavior of the tool.
- `pad`: the image is scaled to fit inside 48x32 while preserving its aspect ratio, then centered on a black background (letterbox/pillarbox) to fill the remaining area.

Examples:

Stretch (default):
```bash
python flag_editor.py /path/to/saves/YourWorld --import 0 --image custom_flag.png
```

Pad (preserve aspect ratio, black background):
```bash
python flag_editor.py /path/to/saves/YourWorld --import 0 --image custom_flag.png --mode pad
```

## How It Works

### NBT Structure

The script reads and writes to the `GCSpaceRaceData.dat` file in your world's `data` folder. The structure is:

```
GCSpaceRaceData.dat
└── data (Compound)
    └── SpaceRaceList (List of Compounds)
        ├── TeamName (String)
        ├── SpaceRaceID (Int)
        ├── TicksSpent (Long)
        ├── FWidth (Int) - Flag width
        ├── FHeight (Int) - Flag height
        ├── FRow0, FRow1, ... (IntArray) - Flag pixel data
        ├── teamColorR/G/B (Double) - Team color
        ├── PlayerList (List) - Team members
        └── CelestialBodyList (List) - Bodies visited
```

### Flag Format

Flags are stored as a compact array of 32-bit integers:
- Each row of pixels is stored as an IntArray (`FRow0`, `FRow1`, etc.)
- Each integer contains RGB values: `(R << 16) | (G << 8) | B`
- Colors are stored as signed bytes offset by 128 (range: -128 to 127)

### Image Conversion

When importing an image:
1. The image is converted to RGB mode if needed
2. Resized to target dimensions using high-quality Lanczos resampling
3. Each pixel's RGB values are converted to Galacticraft's signed byte format
4. Data is packed into the NBT structure

## Important Notes

⚠️ **Always backup your world before modifying save files!**

- The script modifies the `data/GCSpaceRaceData.dat` file in your world
- Make sure Minecraft is closed before running the script
- The default Galacticraft flag size is 20×14 pixels
- Images are automatically resized to fit the flag dimensions

## Troubleshooting

### "No space race data found"

This means either:
- The world doesn't have any Space Races yet (players need to create them in-game first)
- The `data/GCSpaceRaceData.dat` file doesn't exist

### "nbtlib is required"

Install the dependency:
```bash
pip install nbtlib
```

### "Pillow is required"

Install the dependency:
```bash
pip install Pillow
```

### Modified flags don't appear in-game

- Make sure Minecraft was closed when you ran the script
- Check that you're editing the correct world save
- The flag cache might need to be cleared (in `assets/flagCache/`)

## Technical Details

### Color Encoding

Galacticraft stores colors as signed bytes (-128 to 127) but interprets them as unsigned (0 to 255):
- File byte value: `-128` to `127`
- Displayed color: `0` to `255`
- Conversion: `display_value = file_value + 128`

### Legacy Format Support

The script supports both formats:
- **Legacy**: Individual NBT bytes for each pixel (`ColorR-X0-Y0`, etc.)
- **Modern**: Compact IntArray rows (`FRow0`, `FRow1`, etc.)

The script always saves in the modern format for efficiency.

## Examples

### Create a flag from a screenshot

```bash
# 1. List races to find the index
python flag_editor.py ~/Library/Application\ Support/minecraft/saves/MyWorld

# 2. Take a screenshot or create an image
# 3. Import it
python flag_editor.py ~/Library/Application\ Support/minecraft/saves/MyWorld \
    --import 0 --image ~/Pictures/my_custom_flag.png
```

### Batch export all flags

```bash
world="/path/to/world"
python flag_editor.py "$world" | grep "^\[" | while read -r line; do
    index=$(echo "$line" | grep -o '^\[[0-9]\+\]' | tr -d '[]')
    python flag_editor.py "$world" --export "$index" --output "flag_$index.png"
done
```

## Source Code Reference

Based on the Galacticraft source code:
- `FlagData.java` - Flag data storage and serialization
- `SpaceRace.java` - Space Race team data
- `SpaceRaceManager.java` - Managing multiple space races
- `WorldDataSpaceRaces.java` - World save data integration

## License

This tool is provided as-is for use with Galacticraft. Please respect the Galacticraft project's license when using this tool.
