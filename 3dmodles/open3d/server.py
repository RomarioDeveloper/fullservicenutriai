from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
import os
import sys

# Add current directory to path so we can import food_weight
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the estimator logic from the existing script
# We will need to adapt food_weight.py slightly or use it as library
try:
    from food_weight import FoodWeightEstimator, FOOD_DENSITY
    import numpy as np
    import cv2
    import open3d as o3d
except ImportError:
    # If imports fail (e.g. missing dependencies in this environment), we can mock or fail
    print("Warning: Could not import food_weight dependencies")

app = FastAPI(title="Auto Modeling Service (3D Models)")

class SegmentationItem(BaseModel):
    class_name: str
    polygon: List[List[float]]
    confidence: float = 1.0

class SegmentationRequest(BaseModel):
    width: int
    height: int
    segments: List[SegmentationItem]

class ModelingLogic:
    def __init__(self):
        self.estimator = FoodWeightEstimator(plate_diameter_cm=24.0)

    def process(self, data: SegmentationRequest):
        w = data.width
        h = data.height
        
        # Try to find plate to calibrate
        pixels_per_cm = None
        for seg in data.segments:
            if seg.class_name == 'plate':
                poly = np.array(seg.polygon, dtype=np.int32)
                pixels_per_cm = self.estimator.calibrate_from_plate(poly, w, h, 24.0)
                break
        
        if pixels_per_cm is None:
             pixels_per_cm = (w * 0.7) / 24.0 # Default fallback
             
        results = []
        for seg in data.segments:
            if seg.class_name == 'plate': 
                continue
                
            poly = np.array(seg.polygon, dtype=np.int32)
            if len(poly) < 3: continue
            
            # Simple heuristic for height/type since we don't have the original image for color analysis here
            # In a real scenario, we might want to pass image data too, or trust the segmentation class
            food_type = seg.class_name
            density = FOOD_DENSITY.get(food_type, FOOD_DENSITY['default'])
            
            # Height estimation (simplified)
            height_cm = 3.0
            
            try:
                mesh = self.estimator.create_mesh_from_polygon(poly, (w, h), height_cm, pixels_per_cm)
                volume = self.estimator.calculate_volume(mesh)
                weight = volume * density
                
                results.append({
                    "food": food_type,
                    "weight": weight,
                    "volume_cm3": volume,
                    "calories": int(weight * 1.5) # Mock calories
                })
            except Exception as e:
                print(f"Error modeling object: {e}")
                
        return {"results": results}

logic = ModelingLogic()

@app.post("/model")
async def create_model(data: SegmentationRequest):
    return logic.process(data)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3002))
    uvicorn.run(app, host="0.0.0.0", port=port)

