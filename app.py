from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
import os
import cv2
import asyncio

from misumi_xy_wrapper import MisumiXYWrapper, AxisName, DriveMode
from well_plate_config import WellPlateCalculator, WellPosition, WellPlateConfig

app = FastAPI(title="Misumi XY Stage Controller")

# Add CORS middleware to allow web app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global stage instance (will be initialized on startup)
stage: Optional[MisumiXYWrapper] = None
# Use 24-well plate as default
calculator: WellPlateCalculator = WellPlateCalculator(WellPlateCalculator.STANDARD_24_WELL)
# Global camera instance
camera: Optional[cv2.VideoCapture] = None

# Pydantic models for request/response
class MoveXYRequest(BaseModel):
    x: float
    y: float

class MoveWellRequest(BaseModel):
    well: str  # e.g., "A1", "B12"
    position: str = "center"  # center, top, bottom, left, right, etc.

class ConfigUpdateRequest(BaseModel):
    origin_x: float
    origin_y: float

class WellPlateConfigRequest(BaseModel):
    rows: int
    cols: int
    well_spacing_x: float
    well_spacing_y: float
    well_diameter: float
    plate_origin_x: float = 0.0
    plate_origin_y: float = 0.0

class StageConfig(BaseModel):
    port: str
    baudrate: int = 38400

class PositionResponse(BaseModel):
    x: float
    y: float
    well: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize the stage on startup if COM port is configured"""
    global stage
    # You'll need to configure your COM port here
    # For now, we'll delay initialization until the configure endpoint is called
    pass

@app.on_event("shutdown")
async def shutdown_event():
    """Disconnect from stage and camera on shutdown"""
    global stage, camera
    if stage:
        stage.disconnect()
    if camera:
        camera.release()

@app.post("/configure")
async def configure_stage(config: StageConfig):
    """Configure and connect to the stage"""
    global stage
    try:
        # Only disconnect and reconnect if port or baudrate changed
        if stage:
            if stage.port == config.port and stage.baudrate == config.baudrate and stage.connected:
                return {"status": "connected", "port": config.port, "message": "Already connected"}
            stage.disconnect()
        stage = MisumiXYWrapper(port=config.port, baudrate=config.baudrate, auto_initialize=False)
        return {"status": "connected", "port": config.port}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect: {str(e)}")

@app.post("/move/xy")
async def move_xy(request: MoveXYRequest):
    """Move stage to absolute XY coordinates"""
    if not stage:
        raise HTTPException(status_code=400, detail="Stage not connected. Call /configure first.")
    
    print(request.y)
    try:
        # Start the movement for each axis (don't wait for completion)
        if request.x is not None:
            stage.drive_absolute(AxisName.X, request.x)
        if request.y is not None:
            stage.drive_absolute(AxisName.Y, request.y)

        return {"status": "moving", "x": request.x, "y": request.y}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Movement failed: {str(e)}")

@app.post("/move/well")
async def move_well(request: MoveWellRequest):
    """Move stage to a specific well and position within that well"""
    if not stage:
        raise HTTPException(status_code=400, detail="Stage not connected. Call /configure first.")

    try:
        # Parse position
        try:
            position = WellPosition(request.position.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid position. Must be one of: {', '.join([p.value for p in WellPosition])}"
            )

        # Calculate target coordinates
        x, y = calculator.get_well_position(request.well, position)
        print(f"Moving to well {request.well} at position {request.position}: X={x}, Y={y}")

        # Start the movement for each axis (don't wait for completion)
        stage.drive_absolute(AxisName.X, x)
        stage.drive_absolute(AxisName.Y, y)

        return {
            "status": "moving",
            "well": request.well,
            "position": request.position,
            "x": x,
            "y": y
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Movement failed: {str(e)}")

@app.get("/position")
async def get_position():
    """Get current stage position"""
    if not stage:
        raise HTTPException(status_code=400, detail="Stage not connected. Call /configure first.")

    try:
        x = stage.get_position(AxisName.X)
        y = stage.get_position(AxisName.Y)

        return PositionResponse(x=x, y=y)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get position: {str(e)}")

@app.post("/initialize")
async def initialize_stage():
    """Initialize the stage (set memory switches, speeds, and home axes)"""
    if not stage:
        raise HTTPException(status_code=400, detail="Stage not connected. Call /configure first.")

    try:
        stage.initialize()
        return {"status": "success", "message": "Stage initialized and homed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")

@app.post("/home")
async def home_stage():
    """Home all axes"""
    if not stage:
        raise HTTPException(status_code=400, detail="Stage not connected. Call /configure first.")

    try:
        success = stage.home_all_axes()
        if success:
            return {"status": "success", "message": "All axes homed"}
        else:
            raise HTTPException(status_code=500, detail="Homing timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Homing failed: {str(e)}")

@app.post("/stop")
async def stop_stage():
    """Emergency stop all axes"""
    if not stage:
        raise HTTPException(status_code=400, detail="Stage not connected. Call /configure first.")

    try:
        stage.stop()
        return {"status": "success", "message": "All axes stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stop failed: {str(e)}")

@app.get("/wells")
async def get_wells():
    """Get list of all available wells"""
    return {
        "wells": calculator.get_all_wells(),
        "config": {
            "rows": calculator.config.rows,
            "cols": calculator.config.cols,
            "name": calculator.config.name
        }
    }

@app.post("/calibrate/origin")
async def calibrate_origin(request: ConfigUpdateRequest):
    """Set the current position as the origin (well A1 center)"""
    calculator.update_origin(request.origin_x, request.origin_y)
    return {
        "status": "success",
        "message": f"Origin set to ({request.origin_x}, {request.origin_y})"
    }

@app.post("/config/wellplate")
async def configure_wellplate(config: WellPlateConfigRequest):
    """Configure custom well plate dimensions"""
    global calculator
    try:
        custom_config = WellPlateConfig(
            rows=config.rows,
            cols=config.cols,
            well_spacing_x=config.well_spacing_x,
            well_spacing_y=config.well_spacing_y,
            well_diameter=config.well_diameter,
            plate_origin_x=config.plate_origin_x,
            plate_origin_y=config.plate_origin_y
        )
        calculator = WellPlateCalculator(custom_config)
        return {
            "status": "success",
            "message": f"Well plate configured: {custom_config.name}",
            "config": {
                "rows": config.rows,
                "cols": config.cols,
                "wells": calculator.get_all_wells()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(e)}")

@app.get("/config/wellplate")
async def get_wellplate_config():
    """Get current well plate configuration"""
    return {
        "rows": calculator.config.rows,
        "cols": calculator.config.cols,
        "well_spacing_x": calculator.config.well_spacing_x,
        "well_spacing_y": calculator.config.well_spacing_y,
        "well_diameter": calculator.config.well_diameter,
        "plate_origin_x": calculator.config.plate_origin_x,
        "plate_origin_y": calculator.config.plate_origin_y,
        "name": calculator.config.name
    }

@app.post("/camera/start")
async def start_camera():
    """Initialize and start the camera"""
    global camera
    try:
        if camera is not None and camera.isOpened():
            return {"status": "success", "message": "Camera already running"}

        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            raise HTTPException(status_code=500, detail="Failed to open camera")

        return {"status": "success", "message": "Camera started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start camera: {str(e)}")

@app.post("/camera/stop")
async def stop_camera():
    """Stop the camera"""
    global camera
    try:
        if camera:
            camera.release()
            camera = None
        return {"status": "success", "message": "Camera stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop camera: {str(e)}")

def generate_frames():
    """Generator function to yield camera frames"""
    global camera
    while True:
        if camera is None or not camera.isOpened():
            break

        success, frame = camera.read()
        if not success:
            break

        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        # Yield frame in multipart format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.get("/camera/stream")
async def video_stream():
    """Stream video from the camera"""
    if camera is None or not camera.isOpened():
        raise HTTPException(status_code=400, detail="Camera not started. Call /camera/start first.")

    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/")
async def read_root():
    """Serve the web interface"""
    return FileResponse("static/index.html")

# Mount static files directory
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")