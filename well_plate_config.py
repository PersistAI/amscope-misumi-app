"""
Well Plate Configuration
-------------------------
This module defines the configuration for well plates and provides
utilities to calculate XY positions based on well coordinates and
sub-well positions.
"""

from enum import Enum
from typing import Dict, Tuple
from dataclasses import dataclass


class WellPosition(Enum):
    """Enum for positions within a well"""
    CENTER = "center"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


@dataclass
class WellPlateConfig:
    """Configuration for a well plate"""
    rows: int  # Number of rows (e.g., 4 for A-D)
    cols: int  # Number of columns (e.g., 6 for 1-6)
    well_spacing_x: float  # Distance between well centers in X direction (stage units)
    well_spacing_y: float  # Distance between well centers in Y direction (stage units)
    well_diameter: float  # Diameter of each well (mm)
    plate_origin_x: float  # X coordinate of well A1 center (stage units)
    plate_origin_y: float  # Y coordinate of well A1 center (stage units)

    @property
    def name(self) -> str:
        return f"{self.rows * self.cols}-well plate"


class WellPlateCalculator:
    """Calculator for well plate positions"""

    # Standard well plate configurations
    STANDARD_96_WELL = WellPlateConfig(
        rows=8,
        cols=12,
        well_spacing_x=9.0,  # Standard 96-well plate spacing
        well_spacing_y=9.0,
        well_diameter=6.4,
        plate_origin_x=0.0,  # These should be calibrated to your setup
        plate_origin_y=0.0
    )

    STANDARD_384_WELL = WellPlateConfig(
        rows=16,
        cols=24,
        well_spacing_x=4.5,
        well_spacing_y=4.5,
        well_diameter=3.3,
        plate_origin_x=0.0,
        plate_origin_y=0.0
    )

    STANDARD_24_WELL = WellPlateConfig(
        rows=4,
        cols=6,
        well_spacing_x=9500,  # Step distance between wells
        well_spacing_y=9500,  # Step distance between wells
        well_diameter=15.6,
        plate_origin_x=58000,  # A1 X position
        plate_origin_y=32000   # A1 Y position
    )

    def __init__(self, config: WellPlateConfig = None):
        """
        Initialize the calculator with a well plate configuration.

        Args:
            config: WellPlateConfig object. Defaults to standard 96-well plate.
        """
        self.config = config or self.STANDARD_96_WELL

    def parse_well_name(self, well_name: str) -> Tuple[int, int]:
        """
        Parse a well name like 'A1', 'B12', etc. into row and column indices.

        Args:
            well_name: Well name (e.g., 'A1', 'H12')

        Returns:
            Tuple of (row_index, col_index) where both are 0-based

        Raises:
            ValueError: If the well name is invalid
        """
        well_name = well_name.strip().upper()

        if len(well_name) < 2:
            raise ValueError(f"Invalid well name: {well_name}")

        # Extract row letter(s)
        row_part = ""
        col_part = ""
        for char in well_name:
            if char.isalpha():
                row_part += char
            elif char.isdigit():
                col_part += char

        if not row_part or not col_part:
            raise ValueError(f"Invalid well name: {well_name}")

        # Convert row letter to index (A=0, B=1, ...)
        row_index = 0
        for char in row_part:
            row_index = row_index * 26 + (ord(char) - ord('A'))

        # Convert column number to index (1-based to 0-based)
        col_index = int(col_part) - 1

        # Validate indices
        if row_index < 0 or row_index >= self.config.rows:
            raise ValueError(f"Row '{row_part}' is out of range for {self.config.name}")
        if col_index < 0 or col_index >= self.config.cols:
            raise ValueError(f"Column {col_part} is out of range for {self.config.name}")

        return row_index, col_index

    def get_well_center(self, well_name: str) -> Tuple[float, float]:
        """
        Get the XY coordinates of the center of a well.

        Args:
            well_name: Well name (e.g., 'A1', 'H12')

        Returns:
            Tuple of (x, y) coordinates
        """
        row_idx, col_idx = self.parse_well_name(well_name)

        # Stage moves to lower X values from col 1 to 6, and lower Y values from row A to D
        x = self.config.plate_origin_x - (col_idx * self.config.well_spacing_x)
        y = self.config.plate_origin_y - (row_idx * self.config.well_spacing_y)

        return x, y

    def get_well_position(self, well_name: str, position: WellPosition) -> Tuple[float, float]:
        """
        Get the XY coordinates of a specific position within a well.

        Args:
            well_name: Well name (e.g., 'A1', 'H12')
            position: Position within the well (center, top, bottom, etc.)

        Returns:
            Tuple of (x, y) coordinates in mm
        """
        center_x, center_y = self.get_well_center(well_name)

        # Calculate offset from center based on position
        # Using 1800 steps offset for edge positions
        offset_distance = 1800

        offset_x = 0.0
        offset_y = 0.0

        if position == WellPosition.CENTER:
            pass  # No offset
        elif position == WellPosition.TOP:
            offset_y = -offset_distance  # Y increases downward typically
        elif position == WellPosition.BOTTOM:
            offset_y = offset_distance
        elif position == WellPosition.LEFT:
            offset_x = -offset_distance
        elif position == WellPosition.RIGHT:
            offset_x = offset_distance
        elif position == WellPosition.TOP_LEFT:
            offset_x = -offset_distance
            offset_y = -offset_distance
        elif position == WellPosition.TOP_RIGHT:
            offset_x = offset_distance
            offset_y = -offset_distance
        elif position == WellPosition.BOTTOM_LEFT:
            offset_x = -offset_distance
            offset_y = offset_distance
        elif position == WellPosition.BOTTOM_RIGHT:
            offset_x = offset_distance
            offset_y = offset_distance

        return center_x + offset_x, center_y + offset_y

    def get_all_wells(self) -> list[str]:
        """
        Get a list of all well names in the plate.

        Returns:
            List of well names (e.g., ['A1', 'A2', ..., 'H12'])
        """
        wells = []
        for row in range(self.config.rows):
            row_letter = chr(ord('A') + row)
            for col in range(self.config.cols):
                col_number = col + 1
                wells.append(f"{row_letter}{col_number}")
        return wells

    def update_origin(self, x: float, y: float):
        """
        Update the plate origin coordinates.

        Args:
            x: X coordinate of well A1 center
            y: Y coordinate of well A1 center
        """
        self.config.plate_origin_x = x
        self.config.plate_origin_y = y
