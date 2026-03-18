import requests
from fastapi import FastAPI
from fastapi import HTTPException

app = FastAPI(title = "Travel API Server")

hotel_db = requests.get(
    "https://raw.githubusercontent.com/budzianowski/multiwoz/master/db/hotel_db.json"
).json()

restaurant_db = requests.get(
    "https://raw.githubusercontent.com/budzianowski/multiwoz/master/db/restaurant_db.json"
).json()



@app.get("/look/{domain}", tags=["Tools"], operation_id="look")
async def look(domain: str, area: str = None):
    
    if domain == "hotel":
        results = hotel_db
        if area:
            results = [h for h in results if h.get("area") == area]
        return [{"name": h["name"], "type": h["type"], "area": h["area"], "address": h["address"]}
                for h in results]

    elif domain == "restaurant":
        results = restaurant_db
        if area:
            results = [r for r in results if r.get("area") == area]
        return [{"name": r["name"], "food": r.get("food"), "area": r["area"], "address": r["address"]}
                for r in results]

    else:
        raise HTTPException(status_code=400, detail=f"Domain '{domain}' not supported. Use 'hotel' or 'restaurant'")


@app.get("/search/{domain}")
async def search(domain: str, area: str = None, pricerange: str = None,
                 stars: str = None, internet: str = None, parking: str = None,
                 food: str = None, name: str = None):
   
    if domain == "hotel":
        results = hotel_db
        if area:       results = [h for h in results if h.get("area") == area]
        if name:       results = [h for h in results if h.get("name") == name]
        if pricerange: results = [h for h in results if h.get("pricerange") == pricerange]
        if stars:      results = [h for h in results if h.get("stars") == stars]
        if internet:   results = [h for h in results if h.get("internet") == internet]
        if parking:    results = [h for h in results if h.get("parking") == parking]

    elif domain == "restaurant":
        results = restaurant_db
        if area:       results = [r for r in results if r.get("area") == area]
        if pricerange: results = [r for r in results if r.get("pricerange") == pricerange]
        if name:       results = [r for r in results if r.get("name", "").lower() == name.lower()]
        if food:
            if isinstance(food, list):
                results = [r for r in results if r.get('food') in food]
            else:
                results = [r for r in results if r.get("food") == food]

    else:
        raise HTTPException(status_code=400, detail=f"Domain '{domain}' not supported")

    if not results:
        raise HTTPException(status_code=404, detail="No results found matching the criteria")

    return results

