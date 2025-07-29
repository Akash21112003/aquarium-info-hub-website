from flask import Flask, jsonify, g, request
from flask_cors import CORS
import sqlite3
import re
import string

# --- Configuration ---
DATABASE = 'fish_info.db' 

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# --- Database Connection Management ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row # This makes query results accessible like dictionaries
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Helper function to fetch data from a generic table ---
def fetch_data_from_table(table_name, search_name_lower):
    conn = get_db()
    cursor = conn.cursor()

    # Attempt 1: Exact match on the detected name (e.g., 'guppies')
    cursor.execute(f"SELECT * FROM {table_name} WHERE LOWER(name) = ?", (search_name_lower,))
    item = cursor.fetchone()
    if item:
        return item

    # Attempt 2: Try singularizing (e.g., 'guppies' -> 'guppy')
    # This is a very basic pluralization/singularization attempt
    if search_name_lower.endswith('ies'): # e.g., guppies -> guppy
        singular_candidate = search_name_lower[:-3] + 'y'
        cursor.execute(f"SELECT * FROM {table_name} WHERE LOWER(name) = ?", (singular_candidate,))
        item = cursor.fetchone()
        if item:
            return item
    elif search_name_lower.endswith('s'): # e.g., Bettas -> Betta, Tetras -> Tetra
        singular_candidate = search_name_lower[:-1]
        cursor.execute(f"SELECT * FROM {table_name} WHERE LOWER(name) = ?", (singular_candidate,))
        item = cursor.fetchone()
        if item:
            return item
            
    # Attempt 3: Try appending " Fish" or " Plant" (capitalize for consistency with DB names)
    # This handles cases where NLP extracted "Betta" but DB has "Betta Fish"
    if table_name == 'fish_species' and ' fish' not in search_name_lower:
        full_name_candidate = search_name_lower + ' fish'
        cursor.execute(f"SELECT * FROM {table_name} WHERE LOWER(name) = ?", (full_name_candidate,))
        item = cursor.fetchone()
        if item:
            return item
    elif table_name == 'plant_species' and ' plant' not in search_name_lower:
        full_name_candidate = search_name_lower + ' plant'
        cursor.execute(f"SELECT * FROM {table_name} WHERE LOWER(name) = ?", (full_name_candidate,))
        item = cursor.fetchone()
        if item:
            return item

    # Attempt 4: Try a LIKE search (less precise but more forgiving)
    # This could lead to multiple matches, but for simple exact names, it can help with minor variations
    cursor.execute(f"SELECT * FROM {table_name} WHERE LOWER(name) LIKE ?", (f"%{search_name_lower}%",))
    item = cursor.fetchone() # Get the first best match
    if item:
        return item

    return None # Item not found after all attempts

# --- Helper function to get all items from a generic table ---
def get_all_items_from_table(table_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT id, name, description, image_url FROM {table_name} ORDER BY name COLLATE NOCASE")
    return [dict(item) for item in cursor.fetchall()]

# --- API Endpoint: Get All Fish Species ---
@app.route('/api/fishes', methods=['GET'])
def get_all_fishes():
    return jsonify(get_all_items_from_table('fish_species'))

# --- API Endpoint: Get Details for a Single Fish Species ---
@app.route('/api/fish/<string:species_name>', methods=['GET'])
def get_fish_detail(species_name):
    fish_info = fetch_data_from_table('fish_species', species_name.lower())
    if fish_info:
        return jsonify(dict(fish_info))
    else:
        return jsonify({"error": "Fish species not found."}), 404

# NEW API Endpoints for Plants ---
@app.route('/api/plants', methods=['GET'])
def get_all_plants():
    return jsonify(get_all_items_from_table('plant_species'))

@app.route('/api/plant/<string:plant_name>', methods=['GET'])
def get_plant_detail(plant_name):
    plant_info = fetch_data_from_table('plant_species', plant_name.lower())
    if plant_info:
        return jsonify(dict(plant_info))
    else:
        return jsonify({"error": "Plant species not found."}), 404

# --- NEW API Endpoint: Unified Search ---
# This endpoint will handle the search bar input and figure out what user is asking for.
@app.route('/api/search', methods=['POST'])
def search_info():
    user_query = request.json.get('query', '').lower()
    print(f"--- Incoming user_query: '{user_query}'")
    
    if not user_query:
        return jsonify({"response": "Please enter a search query."}), 400

    # Clean the query (remove trailing punctuation, standardize spaces)
    user_query = user_query.rstrip(string.punctuation).strip()
    user_query = ' '.join(user_query.split())
    print(f"--- Cleaned user_query: '{user_query}'")

    response_data = {"type": "general_info", "data": None, "message": ""}

    # --- NLP: Identify Category and Item Name ---
    detected_item_name = None
    target_table = None
    requested_detail = None 

    # 1. Check for specific detail requests and remove them from query for name extraction
    detail_keywords = {
        'diet': ['diet', 'eat', 'food'],
        'habitat': ['habitat', 'water', 'temperature', 'ph'],
        'compatibility': ['compatible', 'compatibility', 'other fish'],
        'min_tank_size_gal': ['tank size', 'size of tank'],
        'plant_needs': ['plants', 'plantation'], # For fish needs
        'filter_recommendation': ['filter', 'filtering'],
        'care_level': ['care level', 'care'], # For plants
        'lighting': ['lighting'],
        'co2_needed': ['co2'],
        'placement': ['placement'],
        'growth_rate': ['growth rate', 'growth']
    }

    cleaned_query_for_name = user_query
    for detail, keywords in detail_keywords.items():
        for keyword in keywords:
            if keyword in user_query:
                requested_detail = detail
                # Ensure replacement handles multi-word keywords and doesn't remove too much
                cleaned_query_for_name = cleaned_query_for_name.replace(keyword, '').strip()
                break 
        if requested_detail:
            break
    
    cleaned_query_for_name = ' '.join(cleaned_query_for_name.split()) # Re-clean spaces

    # 2. Determine if it's a fish or plant query and extract item name
    # Check for explicit category mentions
    is_plant_explicit = any(k in user_query for k in ["plant", "fern", "anubias", "anacharis"])
    is_fish_explicit = any(k in user_query for k in ["fish", "betta", "guppy", "tetra"])

    # Try to extract the item name using regex. This regex tries to capture text
    # that is likely the name, before certain keywords or end of string.
    # It attempts to capture multiple words.
    name_regex_patterns = [
        r'(?:about|for|what is|tell me about|show me)\s+([\w\s]+?)(?:\s+(?:fish|plant)|\?|\.|$)', # "tell me about Betta Fish"
        r'([\w\s]+?)(?:\s+(?:fish|plant)|\?|\.|$)', # "Betta Fish" or "Java Fern" followed by category/punctuation
        r'([\w\s]+)' # Fallback: capture any remaining words as a name candidate
    ]
    
    for pattern in name_regex_patterns: # Corrected variable name here
        match = re.search(pattern, cleaned_query_for_name)
        if match:
            detected_item_name = match.group(1).strip()
            # If a very short word is detected, but a longer candidate exists in query, prefer longer
            if len(detected_item_name.split()) == 1 and len(cleaned_query_for_name.split()) > 1:
                # Try to take the longest sequence of capitalized words if they were initially capitalized
                # This is getting complex for rule-based, stick to direct matches
                pass # Simple regex for now
            break # Found a name, stop trying other patterns


    # Refine detected_item_name and set target_table
    if detected_item_name:
        detected_item_name = detected_item_name.rstrip(string.punctuation).strip() # Clean again
        detected_item_name = ' '.join([word.capitalize() for word in detected_item_name.split()]) # Capitalize fully
        
        # Try to guess table if not explicit:
        if is_plant_explicit and not is_fish_explicit: # Explicitly plant, not fish
            target_table = 'plant_species'
        elif is_fish_explicit and not is_plant_explicit: # Explicitly fish, not plant
            target_table = 'fish_species'
        else: # Neither explicitly nor both explicit (e.g., "tell me about Betta Plant") - prioritize fish by default
            target_table = 'fish_species' 
            # Could add logic here to check if name exists in one table before defaulting

    print(f"--- Detected item name: '{detected_item_name}'")
    print(f"--- Target table (guessed): '{target_table}'")
    print(f"--- Requested detail: '{requested_detail}'")

    # --- Fetch Data based on Detection ---
    item_info = None
    if detected_item_name and target_table:
        print(f"--- Attempting to fetch '{detected_item_name.lower()}' from table '{target_table}'")
        item_info = fetch_data_from_table(target_table, detected_item_name.lower())
        if item_info:
            print(f"--- Item found: {item_info['name']}")
        else:
            print(f"--- Item NOT found in DB for query: '{detected_item_name.lower()}' in '{target_table}'")
    else:
        print(f"--- Skipping DB fetch: detected_item_name='{detected_item_name}', target_table='{target_table}'")

    if item_info:
        response_data['data'] = dict(item_info)
        response_data['type'] = target_table

        if requested_detail: # If a specific detail was asked
            # Handle complex/multi-column details first (like habitat)
            if target_table == 'fish_species' and requested_detail == 'habitat': # NEW specific check for habitat for fish
                if item_info['habitat_temp'] and item_info['habitat_ph']:
                    response_data['message'] = f"{item_info['name']} prefer temperatures of {item_info['habitat_temp']} and a pH of {item_info['habitat_ph']}."
                else:
                    response_data['message'] = f"I don't have specific habitat information for {item_info['name']}."
            elif target_table == 'fish_species' and requested_detail == 'compatibility': # NEW specific check for compatibility
                 response_data['message'] = f"{item_info['name']} are {item_info['compatibility']}."
            # ... add more special cases here if needed ...

            else: # Handle details that map directly to single columns in a robust way
                try: 
                    detail_value = item_info[requested_detail] # Use [] for sqlite3.Row
                    if detail_value is not None and str(detail_value).strip() != '':
                        # Specific formatting for common types (tank size, measurements)
                        if target_table == 'fish_species':
                            if requested_detail == 'min_tank_size_gal':
                                response_data['message'] = f"The minimum tank size for {item_info['name']} is {detail_value} gallons."
                            elif requested_detail == 'plant_needs':
                                response_data['message'] = f"For {item_info['name']}, {detail_value} are recommended."
                            elif requested_detail == 'filter_recommendation':
                                response_data['message'] = f"For {item_info['name']}, {detail_value} is usually recommended."
                            elif requested_detail == 'diet': # Direct match (e.g. "Guppy diet")
                                response_data['message'] = f"{item_info['name']} are {item_info['diet']}."
                            else: # Fallback for other direct column details
                                response_data['message'] = f"The {requested_detail.replace('_', ' ')} for {item_info['name']} is {detail_value}."
                        
                        elif target_table == 'plant_species':
                            if requested_detail == 'co2_needed':
                                response_data['message'] = f"For {item_info['name']}, CO2 is {detail_value}."
                            elif requested_detail == 'care_level':
                                response_data['message'] = f"The care level for {item_info['name']} is {detail_value}."
                            elif requested_detail == 'lighting':
                                response_data['message'] = f"Regarding lighting for {item_info['name']}: {detail_value}."
                            elif requested_detail == 'placement':
                                response_data['message'] = f"The recommended placement for {item_info['name']} is {detail_value}."
                            elif requested_detail == 'growth_rate':
                                response_data['message'] = f"The growth rate for {item_info['name']} is {detail_value}."
                            else: # Generic plant detail
                                response_data['message'] = f"The {requested_detail.replace('_', ' ')} for {item_info['name']} is {detail_value}."
                    else: # If column exists but its value is None or empty string
                        response_data['message'] = f"I don't have specific information about the {requested_detail.replace('_', ' ')} for {item_info['name']}."
                except KeyError:
                    response_data['message'] = f"I don't have specific information about '{requested_detail.replace('_', ' ')}' for {item_info['name']}."
                except Exception as e:
                    print(f"ERROR: Unexpected error accessing detail '{requested_detail}' for {item_info['name']}: {e}")
                    response_data['message'] = f"An internal error occurred while fetching details for {item_info['name']}."

        else: # No specific detail requested, provide full description
            response_data['message'] = f"{item_info['name']}: {item_info['description']}"
    else: # Item not found at all
        response_data['message'] = f"I couldn't find information for '{detected_item_name if detected_item_name else user_query}'. Please try another name or phrase."
        response_data['type'] = 'error'

    return jsonify(response_data)

# --- Run the Flask App ---
if __name__ == '__main__':
    app.run(debug=True, port=5000) # Runs on http://127.0.0.1:5000