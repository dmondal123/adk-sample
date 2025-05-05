from common.a2a_client import call_agent

AREA_URL = "http://localhost:8004/run"
PERIMETER_URL = "http://localhost:8005/run"

async def run(payload):
    # 👀 Print what the geometry host agent is sending
    print("🚀 Incoming geometry payload:", payload)

    # Extract the request and parameters
    request = payload.get("request", "").lower()
    parameters = payload.get("parameters", {})
    
    # Extract length and width from parameters
    length = parameters.get("length", 0)
    width = parameters.get("width", 0)
    
    # Create payloads for sub-agents with parameters at the top level
    area_payload = {
        "length": length,
        "width": width,
        # Also include the original request and parameters for context
        "request": f"Calculate the area of a rectangle with length {length} and width {width}",
        "parameters": parameters
    }
    
    perimeter_payload = {
        "length": length,
        "width": width,
        # Also include the original request and parameters for context
        "request": f"Calculate the perimeter of a rectangle with length {length} and width {width}",
        "parameters": parameters
    }
    
    results = {}
    
    # Call only the appropriate agent based on the request
    if "area" in request:
        area = await call_agent(AREA_URL, area_payload)
        print("📦 area:", area)
        # 🛡 Ensure it's a dict before access
        area = area if isinstance(area, dict) else {}
        results["area"] = area.get("result", "No area calculation returned.")
        
    if "perimeter" in request:
        perimeter = await call_agent(PERIMETER_URL, perimeter_payload)
        print("📦 perimeter:", perimeter)
        # 🛡 Ensure it's a dict before access
        perimeter = perimeter if isinstance(perimeter, dict) else {}
        results["perimeter"] = perimeter.get("result", "No perimeter calculation returned.")
    
    # If neither area nor perimeter was explicitly requested, calculate both (fallback behavior)
    if "area" not in request and "perimeter" not in request:
        area = await call_agent(AREA_URL, area_payload)
        perimeter = await call_agent(PERIMETER_URL, perimeter_payload)
        
        print("📦 area:", area)
        print("📦 perimeter:", perimeter)
        
        # 🛡 Ensure all are dicts before access
        area = area if isinstance(area, dict) else {}
        perimeter = perimeter if isinstance(perimeter, dict) else {}
        
        results["area"] = area.get("result", "No area calculation returned.")
        results["perimeter"] = perimeter.get("result", "No perimeter calculation returned.")

    return results 