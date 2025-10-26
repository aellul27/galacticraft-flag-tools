#!/usr/bin/env python3
"""
Galacticraft Flag Editor
========================
This script allows you to edit flag images for Space Races in Galacticraft save files.
It reads the NBT data, lists all space races, and allows you to replace a flag with a custom image.

Usage:
    python flag_editor.py <path_to_level.dat> [options]

Requirements:
    - nbtlib (pip install nbtlib)
    - Pillow (pip install Pillow)
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple, cast

try:
    import nbtlib
    from nbtlib import nbt
except ImportError:
    print("Error: nbtlib is required. Install it with: pip install nbtlib")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is required. Install it with: pip install Pillow")
    sys.exit(1)

cairosvg = None
try:
    import cairosvg
    SVG_SUPPORT = True
except ImportError:
    cairosvg = None
    SVG_SUPPORT = False


class FlagData:
    """Represents flag data as stored in Galacticraft NBT format."""
    
    def __init__(self, width: int = 0, height: int = 0):
        self.width = width
        self.height = height
        # Color array: [x][y][rgb] where rgb are signed bytes (-128 to 127)
        self.colors = [[[0, 0, 0] for _ in range(height)] for _ in range(width)]
    
    @classmethod
    def from_nbt(cls, nbt_data: nbtlib.Compound) -> 'FlagData':
        """Read flag data from NBT compound tag."""
        # New compact format (preferred)
        if 'FWidth' in nbt_data:
            width = int(nbt_data['FWidth'])
            height = int(nbt_data['FHeight'])
            flag = cls(width, height)
            
            for i in range(height):
                color_row_key = f'FRow{i}'
                if color_row_key in nbt_data:
                    color_row = nbt_data[color_row_key]
                    for j in range(width):
                        if j < len(color_row):
                            color = int(color_row[j])
                            # Extract RGB from 32-bit color
                            # Java casts to byte: (byte)(color >> 16)
                            # This means: if value >= 128, it becomes negative in signed byte
                            # We need to match Java's (byte) cast behavior
                            r = (color >> 16) & 0xFF
                            g = (color >> 8) & 0xFF
                            b = color & 0xFF
                            # Convert unsigned byte (0-255) to signed byte (-128 to 127)
                            # Values 0-127 stay the same, 128-255 become -128 to -1
                            flag.colors[j][i][0] = r if r < 128 else r - 256
                            flag.colors[j][i][1] = g if g < 128 else g - 256
                            flag.colors[j][i][2] = b if b < 128 else b - 256
            
            return flag
        
        # Legacy format
        elif 'FlagWidth' in nbt_data:
            width = int(nbt_data['FlagWidth'])
            height = int(nbt_data['FlagHeight'])
            flag = cls(width, height)
            
            for i in range(width):
                for j in range(height):
                    r_key = f'ColorR-X{i}-Y{j}'
                    g_key = f'ColorG-X{i}-Y{j}'
                    b_key = f'ColorB-X{i}-Y{j}'
                    
                    if r_key in nbt_data:
                        flag.colors[i][j][0] = int(nbt_data[r_key])
                    if g_key in nbt_data:
                        flag.colors[i][j][1] = int(nbt_data[g_key])
                    if b_key in nbt_data:
                        flag.colors[i][j][2] = int(nbt_data[b_key])
            
            return flag
        
        # Empty flag
        return cls(20, 14)  # Default Galacticraft flag size
    
    def to_nbt(self, nbt_data: nbtlib.Compound):
        """Write flag data to NBT compound tag (new compact format)."""
        nbt_data['FWidth'] = nbtlib.Int(self.width)
        nbt_data['FHeight'] = nbtlib.Int(self.height)
        
        for i in range(self.height):
            color_row = []
            for j in range(self.width):
                # Convert RGB to 32-bit color
                r = (self.colors[j][i][0] + 128) & 0xFF
                g = (self.colors[j][i][1] + 128) & 0xFF
                b = (self.colors[j][i][2] + 128) & 0xFF
                color_32bit = (r << 16) | (g << 8) | b
                color_row.append(color_32bit)
            
            nbt_data[f'FRow{i}'] = nbtlib.IntArray(color_row)
    
    def to_image(self) -> Image.Image:
        """Convert flag data to PIL Image."""
        img = Image.new('RGB', (self.width, self.height))
        
        for x in range(self.width):
            for y in range(self.height):
                r = (self.colors[x][y][0] + 128) & 0xFF
                g = (self.colors[x][y][1] + 128) & 0xFF
                b = (self.colors[x][y][2] + 128) & 0xFF
                img.putpixel((x, y), (r, g, b))
        
        return img
    
    @classmethod
    def from_image(cls, img: Image.Image, target_width: int = 48, target_height: int = 32,
                   preserve_aspect: bool = False) -> 'FlagData':
        """Create flag data from PIL Image.

        If preserve_aspect is False (default), the image is resized/stretched to exactly
        target dimensions (current behavior). If True, the image is scaled to fit while
        preserving aspect ratio and pasted centered onto a black background of the
        target size.
        """
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')

        if preserve_aspect:
            # Scale preserving aspect ratio and paste onto black background
            # Make a copy so we don't mutate the original
            working = img.copy()
            working.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)

            background = Image.new('RGB', (target_width, target_height), (0, 0, 0))
            offset_x = (target_width - working.width) // 2
            offset_y = (target_height - working.height) // 2
            background.paste(working, (offset_x, offset_y))
            img_to_sample = background
        else:
            # Stretch to fill target dimensions (existing behavior)
            if img.size != (target_width, target_height):
                img_to_sample = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            else:
                img_to_sample = img

        flag = cls(target_width, target_height)

        for x in range(target_width):
            for y in range(target_height):
                # getpixel will be an RGB triplet after conversion
                pixel = cast(Tuple[int, int, int], img_to_sample.getpixel((x, y)))
                r, g, b = pixel
                # Convert unsigned byte (0-255) to signed byte (-128 to 127)
                flag.colors[x][y][0] = r if r < 128 else r - 256
                flag.colors[x][y][1] = g if g < 128 else g - 256
                flag.colors[x][y][2] = b if b < 128 else b - 256

        return flag


class SpaceRace:
    """Represents a Space Race team."""
    
    def __init__(self):
        self.team_name: str = "Unnamed"
        self.space_race_id: int = 0
        self.ticks_spent: int = 0
        self.flag_data: FlagData = FlagData()
        self.team_color: Tuple[float, float, float] = (0.5, 0.5, 0.5)
        self.player_names: List[str] = []
        self.celestial_bodies: Dict[str, int] = {}
    
    @classmethod
    def from_nbt(cls, nbt_data: nbtlib.Compound) -> 'SpaceRace':
        """Load space race from NBT compound tag."""
        race = cls()
        
        if 'TeamName' in nbt_data:
            race.team_name = str(nbt_data['TeamName'])
        
        if 'SpaceRaceID' in nbt_data:
            race.space_race_id = int(nbt_data['SpaceRaceID'])
        
        if 'TicksSpent' in nbt_data:
            race.ticks_spent = int(nbt_data['TicksSpent'])
        
        # Load flag data
        race.flag_data = FlagData.from_nbt(nbt_data)
        
        # Load team color
        if 'teamColorR' in nbt_data:
            race.team_color = (
                float(nbt_data['teamColorR']),
                float(nbt_data['teamColorG']),
                float(nbt_data['teamColorB'])
            )
        
        # Load player names
        if 'PlayerList' in nbt_data:
            for player_tag in nbt_data['PlayerList']:
                if 'PlayerName' in player_tag:
                    race.player_names.append(str(player_tag['PlayerName']))
        
        # Load celestial bodies
        if 'CelestialBodyList' in nbt_data:
            for body_tag in nbt_data['CelestialBodyList']:
                if 'CelestialBodyName' in body_tag:
                    body_name = str(body_tag['CelestialBodyName'])
                    time_taken = int(body_tag.get('TimeTaken', 0))
                    race.celestial_bodies[body_name] = time_taken
        
        return race
    
    def to_nbt(self, nbt_data: nbtlib.Compound):
        """Save space race to NBT compound tag."""
        nbt_data['TeamName'] = nbtlib.String(self.team_name)
        nbt_data['SpaceRaceID'] = nbtlib.Int(self.space_race_id)
        nbt_data['TicksSpent'] = nbtlib.Long(self.ticks_spent)
        
        # Save flag data
        self.flag_data.to_nbt(nbt_data)
        
        # Save team color
        nbt_data['teamColorR'] = nbtlib.Double(self.team_color[0])
        nbt_data['teamColorG'] = nbtlib.Double(self.team_color[1])
        nbt_data['teamColorB'] = nbtlib.Double(self.team_color[2])
        
        # Save player names
        player_list = nbtlib.List[nbtlib.Compound]()
        for player_name in self.player_names:
            player_tag = nbtlib.Compound()
            player_tag['PlayerName'] = nbtlib.String(player_name)
            player_list.append(player_tag)
        nbt_data['PlayerList'] = player_list
        
        # Save celestial bodies
        body_list = nbtlib.List[nbtlib.Compound]()
        for body_name, time_taken in self.celestial_bodies.items():
            body_tag = nbtlib.Compound()
            body_tag['CelestialBodyName'] = nbtlib.String(body_name)
            body_tag['TimeTaken'] = nbtlib.Int(time_taken)
            body_list.append(body_tag)
        nbt_data['CelestialBodyList'] = body_list
    
    def __str__(self):
        players_str = ", ".join(self.player_names) if self.player_names else "None"
        bodies_str = ", ".join(self.celestial_bodies.keys()) if self.celestial_bodies else "None"
        return (f"Space Race #{self.space_race_id}: {self.team_name}\n"
                f"  Players: {players_str}\n"
                f"  Flag Size: {self.flag_data.width}x{self.flag_data.height}\n"
                f"  Team Color: RGB({self.team_color[0]:.2f}, {self.team_color[1]:.2f}, {self.team_color[2]:.2f})\n"
                f"  Celestial Bodies Visited: {bodies_str}\n"
                f"  Ticks Spent: {self.ticks_spent}")


class SpaceRaceEditor:
    """Main class for editing space race data in Minecraft saves."""
    
    def __init__(self, world_path: str):
        self.world_path = Path(world_path)
        self.level_dat_path = self.world_path / "level.dat"
        self.data_path = self.world_path / "data"
        self.space_races: List[SpaceRace] = []
        self.nbt_file = None
        self.space_race_nbt_file = None  # Store the original NBT file structure
        
        if not self.level_dat_path.exists():
            raise FileNotFoundError(f"level.dat not found at {self.level_dat_path}")
    
    def load(self):
        """Load space race data from the world save."""
        # Load level.dat
        self.nbt_file = nbtlib.load(str(self.level_dat_path))
        
        # Look for space race data in the Data compound
        # Space races are stored in WorldSavedData with ID "GCSpaceRaceData"
        
        # Check in data folder for GCSpaceRaceData.dat
        space_race_file = self.data_path / "GCSpaceRaceData.dat"
        
        if space_race_file.exists():
            print(f"Loading space race data from {space_race_file}")
            self.space_race_nbt_file = nbtlib.load(str(space_race_file))
            self._parse_space_races(self.space_race_nbt_file['data'])
        else:
            print("No space race data found. The world may not have any space races yet.")
    
    def _parse_space_races(self, data_compound: nbtlib.Compound):
        """Parse space race data from NBT compound."""
        if 'SpaceRaceList' in data_compound:
            race_list = data_compound['SpaceRaceList']
            for race_nbt in race_list:
                race = SpaceRace.from_nbt(race_nbt)
                self.space_races.append(race)
            print(f"Loaded {len(self.space_races)} space race(s)")
        else:
            print("No SpaceRaceList found in data")
    
    def save(self):
        """Save modified space race data back to the world."""
        space_race_file = self.data_path / "GCSpaceRaceData.dat"
        
        # Create data directory if it doesn't exist
        self.data_path.mkdir(exist_ok=True)
        
        # Create backup of original file
        if space_race_file.exists():
            import shutil
            backup_file = self.data_path / "GCSpaceRaceData.dat.backup"
            shutil.copy2(space_race_file, backup_file)
            print(f"Backup created: {backup_file}")
        
        # Use the original NBT file structure if it exists, otherwise create new
        if self.space_race_nbt_file is not None:
            root = self.space_race_nbt_file
        else:
            root = nbtlib.File()
            root['data'] = nbtlib.Compound()
        
        # Update the SpaceRaceList in the data compound
        race_list = nbtlib.List[nbtlib.Compound]()
        for race in self.space_races:
            race_nbt = nbtlib.Compound()
            race.to_nbt(race_nbt)
            race_list.append(race_nbt)
        
        root['data']['SpaceRaceList'] = race_list
        
        # Save to file
        root.save(str(space_race_file))
        print(f"Space race data saved to {space_race_file}")
    
    def list_races(self):
        """Print all space races."""
        if not self.space_races:
            print("No space races found in this world.")
            return
        
        print("\n" + "="*60)
        print("SPACE RACES")
        print("="*60)
        for i, race in enumerate(self.space_races):
            print(f"\n[{i}] {race}")
        print("\n" + "="*60 + "\n")
    
    def export_flag(self, race_index: int, output_path: str):
        """Export a space race flag to an image file."""
        if race_index < 0 or race_index >= len(self.space_races):
            raise ValueError(f"Invalid race index: {race_index}")
        
        race = self.space_races[race_index]
        img = race.flag_data.to_image()
        img.save(output_path)
        print(f"Flag exported to {output_path}")
    
    def import_flag(self, race_index: int, image_path: str, width: int = 48, height: int = 32,
                    preserve_aspect: bool = False):
        """Import an image as a space race flag."""
        if race_index < 0 or race_index >= len(self.space_races):
            raise ValueError(f"Invalid race index: {race_index}")
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Handle SVG files
        if image_path.lower().endswith('.svg'):
            if not SVG_SUPPORT:
                print("Error: SVG support requires cairosvg. Install it with: pip install cairosvg")
                print("Alternatively, convert your SVG to PNG first.")
                sys.exit(1)
            
            # Convert SVG to PNG in memory (always 48x32)
            import io
            # Ensure cairosvg is available (static analyzer) and that svg2png returns bytes
            assert cairosvg is not None, "cairosvg must be available for SVG conversion"
            png_data = cast(bytes, cairosvg.svg2png(url=image_path))
            if png_data is None:
                raise RuntimeError("Failed to render SVG to PNG")
            img = Image.open(io.BytesIO(png_data))
        else:
            img = Image.open(image_path)
        
        race = self.space_races[race_index]
        race.flag_data = FlagData.from_image(img, 48, 32, preserve_aspect=preserve_aspect)
        mode_str = 'pad (preserve aspect ratio, black background)' if preserve_aspect else 'stretch (fill target size)'
        print(f"Flag imported from {image_path} using mode: {mode_str}")
        print(f"Applied to Space Race #{race.space_race_id}: {race.team_name}")


def main():
    parser = argparse.ArgumentParser(
        description="Edit Galacticraft Space Race flags in Minecraft world saves (48x32 pixels)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  List all space races:
    python flag_editor.py /path/to/world

  Export a flag:
    python flag_editor.py /path/to/world --export 0 --output flag.png

  Import a flag (automatically resized to 48x32):
    python flag_editor.py /path/to/world --import 0 --image my_flag.png
        """
    )
    
    parser.add_argument('world_path', help='Path to the Minecraft world folder')
    parser.add_argument('--list', action='store_true', help='List all space races (default action)')
    parser.add_argument('--export', type=int, metavar='INDEX', help='Export flag from space race at INDEX')
    parser.add_argument('--import', dest='import_flag', type=int, metavar='INDEX', 
                       help='Import flag to space race at INDEX')
    parser.add_argument('--output', '-o', help='Output file path for export')
    parser.add_argument('--image', '-i', help='Input image file path for import')
    parser.add_argument('--mode', choices=['stretch', 'pad'], default='stretch',
                        help="Scaling mode when importing: 'stretch' (default) stretches to fill 48x32; 'pad' scales preserving aspect ratio and pads with black")
    
    args = parser.parse_args()
    
    try:
        editor = SpaceRaceEditor(args.world_path)
        editor.load()
        
        # Default action: list races
        if args.export is None and args.import_flag is None:
            editor.list_races()
        
        # Export flag
        if args.export is not None:
            output_path = args.output or f"flag_race_{args.export}.png"
            editor.export_flag(args.export, output_path)
        
        # Import flag
        if args.import_flag is not None:
            if not args.image:
                print("Error: --image is required when importing a flag")
                sys.exit(1)

            preserve_aspect = (args.mode == 'pad')
            editor.import_flag(args.import_flag, args.image, preserve_aspect=preserve_aspect)
            editor.save()
            print("\nDone! Remember to backup your world before using the modified save.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
