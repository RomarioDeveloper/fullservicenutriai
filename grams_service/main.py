from fastapi import FastAPI, UploadFile, File, HTTPException
import aiohttp
import uvicorn
import os
import json
from typing import List, Optional

app = FastAPI(title="Grams Service")

# URLs of dependent services
# Assuming 3dmodels is running on 3002
# Assuming segmentation is running on 3001 (or mocked)
SEGMENTATION_SERVICE_URL = os.getenv("SEGMENTATION_SERVICE_URL", "http://localhost:3001")
AUTO_MODELING_SERVICE_URL = os.getenv("AUTO_MODELING_SERVICE_URL", "http://localhost:3002")

@app.post("/calculate")
async def calculate_grams(images: List[UploadFile] = File(...)):
    """
    Accepts 1-3 images, sends them for segmentation, then for modeling, 
    and finally calculates the average grammage.
    """
    if not images:
        raise HTTPException(status_code=400, detail="No images provided")

    results = []

    async with aiohttp.ClientSession() as session:
        for image in images:
            try:
                # 1. Send to Segmentation Service
                image_content = await image.read()
                form_data = aiohttp.FormData()
                form_data.add_field('image', image_content, filename=image.filename, content_type=image.content_type)
                
                async with session.post(f"{SEGMENTATION_SERVICE_URL}/analyze", data=form_data) as seg_resp:
                    if seg_resp.status != 200:
                        print(f"Segmentation failed for {image.filename}: {seg_resp.status}")
                        continue
                    segmentation_data = await seg_resp.json()
                
                # 2. Send to Auto Modeling Service
                async with session.post(f"{AUTO_MODELING_SERVICE_URL}/model", json=segmentation_data) as model_resp:
                    if model_resp.status != 200:
                        print(f"Modeling failed for {image.filename}: {model_resp.status}")
                        continue
                    modeling_data = await model_resp.json()
                    results.append(modeling_data)
                    
            except Exception as e:
                print(f"Error processing {image.filename}: {e}")
                continue
    
    if not results:
        raise HTTPException(status_code=500, detail="Failed to process any images")

    # 3. Average results
    final_result = average_results(results)
    
    return final_result

def average_results(results_list: list) -> dict:
    """Averages modeling results from multiple images."""
    grouped_food = {}
    
    for data in results_list:
        if not data or 'results' not in data:
            continue
            
        for item in data['results']:
            food_name = item.get('food', 'неизвестно')
            if food_name not in grouped_food:
                grouped_food[food_name] = {
                    'weights': [],
                    'calories': [],
                    'volumes': []
                }
            
            grouped_food[food_name]['weights'].append(item.get('weight', 0))
            grouped_food[food_name]['calories'].append(item.get('calories', 0))
            grouped_food[food_name]['volumes'].append(item.get('volume_cm3', 0))
    
    averaged = []
    for food_name, data in grouped_food.items():
        weights = data['weights']
        calories = data['calories']
        volumes = data['volumes']
        
        if not weights:
            continue
            
        avg_weight = sum(weights) / len(weights)
        avg_calories = sum(calories) / len(calories)
        avg_volume = sum(volumes) / len(volumes)
        
        averaged.append({
            'food': food_name,
            'weight': round(avg_weight, 2),
            'calories': int(avg_calories),
            'volume_cm3': round(avg_volume, 2)
        })
        
    return {'results': averaged}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3003))
    uvicorn.run(app, host="0.0.0.0", port=port)

