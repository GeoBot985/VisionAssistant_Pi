import random

def get_distance_response(value):
    """Return a response based on the distance reading."""
    if value >= 1000:
        return "No Obstacle"
    elif value >= 600:
        return "Caution"
    elif value >= 300:
        return "Warning"
    else:
        return "Obstacle Close"

def generate_distance_frame(base=1200, min_val=50, decay=0.92, noise=25):
    """
    Generates an 8x8 distance frame with responses for each value.
    """
    frame = []
    responses = []
    
    for row in range(8):
        row_values = []
        row_responses = []
        for col in range(8):
            val = base * (decay ** ((row + col) / 2))
            val += random.randint(-noise, noise)
            val = max(min_val, min(int(val), base))
            row_values.append(val)
            row_responses.append(get_distance_response(val))
        frame.append(row_values)
        responses.append(row_responses)

    
    output = "------ 8x8 Distance Frame (mm) ------\n"
    for row in frame:
        output += " ".join(f"{v:4d}" for v in row) + "\n"
    output += "-------------------------------------\n\n"
    
    output += "------ 8x8 Response Frame -----------\n"
    for row in responses:
        output += " | ".join(f"{resp:14s}" for resp in row) + "\n"
    output += "-------------------------------------"
    
    return output


# Example usage
print(generate_distance_frame())
