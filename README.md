# Misumi XY Stage Web Controller

A web application for controlling a Misumi XY stage with well plate support. This app allows you to move the stage to specific wells on a plate and target different positions within each well.

## Features

- **Well-based navigation**: Specify wells by name (e.g., A1, B12) and position within the well
- **Manual XY control**: Direct coordinate-based movement
- **Web interface**: Clean, responsive UI accessible from any browser
- **Multiple well plate formats**: Supports 24-well, 96-well, and 384-well plates (configurable)
- **Real-time position tracking**: Monitor current stage position
- **Emergency stop**: Quick stop button for safety

## Installation

1. Make sure you have Python 3.8+ installed

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the FastAPI server:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

2. Open your web browser and navigate to:
```
http://localhost:8000
```

## Usage

### Initial Setup

1. **Connect to Stage**:
   - Enter your COM port (e.g., COM3)
   - Click "Connect"
   - Wait for the stage to initialize (this will home the axes)

2. **Calibrate Well Plate Origin** (Optional):
   - Manually move the stage to well A1 center position
   - Use the `/calibrate/origin` endpoint to set this as the reference point

### Moving the Stage

#### Well-Based Movement

1. Enter a well name (e.g., "A1") or click on a well in the grid
2. Select a position within the well:
   - **Center**: Middle of the well
   - **Top/Bottom/Left/Right**: Edge positions
   - **Corners**: Top-left, top-right, bottom-left, bottom-right
3. Click "Move to Well"

#### Manual XY Movement

1. Enter X and Y coordinates in millimeters
2. Click "Move to XY"

### Other Controls

- **Home All Axes**: Return to home position
- **Emergency Stop**: Immediately stop all movement
- **Refresh Position**: Update current position display

## API Endpoints

### Stage Control

- `POST /configure` - Connect to the stage
  ```json
  {
    "port": "COM3",
    "baudrate": 38400
  }
  ```

- `POST /move/well` - Move to a well position
  ```json
  {
    "well": "A1",
    "position": "center"
  }
  ```

- `POST /move/xy` - Move to XY coordinates
  ```json
  {
    "x": 10.5,
    "y": 20.3
  }
  ```

- `GET /position` - Get current position
- `POST /home` - Home all axes
- `POST /stop` - Emergency stop

### Well Plate Configuration

- `GET /wells` - Get list of all wells
- `GET /config/wellplate` - Get current well plate configuration
- `POST /config/wellplate` - Configure custom well plate
  ```json
  {
    "rows": 8,
    "cols": 12,
    "well_spacing_x": 9.0,
    "well_spacing_y": 9.0,
    "well_diameter": 6.4,
    "plate_origin_x": 0.0,
    "plate_origin_y": 0.0
  }
  ```

- `POST /calibrate/origin` - Set well plate origin
  ```json
  {
    "origin_x": 0.0,
    "origin_y": 0.0
  }
  ```

## Well Plate Configuration

The app comes pre-configured with standard well plate formats:

### 96-Well Plate (Default)
- Rows: 8 (A-H)
- Columns: 12 (1-12)
- Well spacing: 9.0 mm
- Well diameter: 6.4 mm

### 384-Well Plate
- Rows: 16 (A-P)
- Columns: 24 (1-24)
- Well spacing: 4.5 mm
- Well diameter: 3.3 mm

### 24-Well Plate
- Rows: 4 (A-D)
- Columns: 6 (1-6)
- Well spacing: 19.3 mm
- Well diameter: 15.6 mm

You can configure custom well plates using the `/config/wellplate` endpoint or by modifying [well_plate_config.py](well_plate_config.py).

## Position Calculation

Positions within wells are calculated as follows:
- **Center**: Exact center of the well
- **Edge positions**: 70% of well radius from center (to avoid hitting walls)

## File Structure

```
amscope-misumi-app/
├── app.py                    # FastAPI application
├── misumi_xy_wrapper.py      # Misumi stage controller wrapper
├── well_plate_config.py      # Well plate configuration and calculations
├── requirements.txt          # Python dependencies
├── static/
│   └── index.html           # Web interface
└── README.md                # This file
```

## Safety Notes

- Always test movements in a safe environment first
- Use the emergency stop button if needed
- Ensure the stage has enough clearance for movements
- Double-check well plate configuration matches your physical setup

## Troubleshooting

### Stage won't connect
- Check COM port is correct (use Device Manager on Windows)
- Ensure no other application is using the COM port
- Verify baudrate matches your stage configuration (default: 38400)

### Wrong well positions
- Calibrate the origin by moving to well A1 center and using `/calibrate/origin`
- Verify well plate configuration matches your physical plate
- Check well spacing and diameter settings

### Stage moves to wrong position
- Re-home the stage using "Home All Axes"
- Verify the stage was properly initialized
- Check that coordinates are in the expected units (mm)

## Development

To modify the well plate positions or add new features:

1. **Well plate logic**: Edit [well_plate_config.py](well_plate_config.py)
2. **API endpoints**: Edit [app.py](app.py)
3. **Web interface**: Edit [static/index.html](static/index.html)
4. **Stage control**: Edit [misumi_xy_wrapper.py](misumi_xy_wrapper.py)

## License

This project is provided as-is for controlling Misumi XY stages.
