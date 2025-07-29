import sqlite3

DATABASE_NAME = 'fish_info.db' # We'll keep the name for now, but it contains more than fish

def create_database():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Create the 'fish_species' table (existing)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fish_species (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            habitat_temp TEXT,
            habitat_ph TEXT,
            diet TEXT,
            compatibility TEXT,
            min_tank_size_gal INTEGER,
            plant_needs TEXT,
            filter_recommendation TEXT,
            image_url TEXT
        )
    ''')

    # NEW: Create the 'plant_species' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plant_species (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            care_level TEXT,
            lighting TEXT,
            co2_needed TEXT,
            placement TEXT,
            growth_rate TEXT,
            image_url TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print(f"Database '{DATABASE_NAME}' created (if it didn't exist) and tables ensured.")

def add_sample_fish_data(): # Renamed function for clarity
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    sample_fish = [
        (
            'Betta Fish',
            'Known for their vibrant colors and flowing fins, Betta fish (Siamese fighting fish) are popular but require specific care. They are often kept alone.',
            '75-80°F (24-27°C)', '6.5-7.5', 'Carnivore (pellets, bloodworms, brine shrimp)',
            'Aggressive towards other Bettas and fish with long fins; generally best kept alone in their own tank.',
            5, 'Live plants like Anubias, Java Fern; floating plants for cover',
            'Sponge filter or small hang-on-back filter with gentle flow',
            'https://example.com/betta.jpg'
        ),
        (
            'Guppy',
            'Small, colorful, and active livebearers, Guppies are excellent for beginners. They breed easily.',
            '72-78°F (22-26°C)', '6.8-7.8', 'Omnivore (flakes, brine shrimp, daphnia)',
            'Peaceful; compatible with most community fish of similar size and temperament.',
            10, 'Heavily planted tanks (e.g., Anacharis, Guppy Grass) provide cover for fry.',
            'Hang-on-back filter or internal filter suitable for tank size',
            'https://example.com/guppy.jpg'
        ),
        (
            'Neon Tetra',
            'Brightly colored, schooling fish that are peaceful and add a pop of color to community tanks.',
            '72-76°F (22-24°C)', '6.0-7.0', 'Omnivore (micro-pellets, flakes, frozen foods)',
            'Peaceful; must be kept in schools of 6 or more; compatible with other peaceful community fish.',
            20, 'Densely planted tanks with open swimming areas (e.g., Cryptocoryne, Java Moss).',
            'Can tolerate various filters, but prefer gentle flow from sponge or internal filter.',
            'https://example.com/neon_tetra.jpg'
        )
    ]
    cursor.executemany('''
        INSERT OR IGNORE INTO fish_species (name, description, habitat_temp, habitat_ph, diet, compatibility, min_tank_size_gal, plant_needs, filter_recommendation, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_fish)
    conn.commit()
    conn.close()
    print(f"Sample fish data added to '{DATABASE_NAME}'.")

def add_sample_plant_data(): # NEW: Function to add plant data
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    sample_plants = [
        (
            'Java Fern',
            'A hardy and easy-to-care-for plant, ideal for beginners. It attaches to wood or rocks.',
            'Easy', 'Low to Medium', 'No', 'Midground/Attached to decor', 'Slow',
            'https://example.com/java_fern.jpg'
        ),
        (
            'Anubias Nana',
            'Another very hardy and low-maintenance plant, known for its thick leaves. Attaches to surfaces.',
            'Easy', 'Low to Medium', 'No', 'Foreground/Midground/Attached to decor', 'Slow',
            'https://example.com/anubias_nana.jpg'
        ),
        (
            'Anacharis',
            'A fast-growing, excellent oxygenator that can be floated or planted. Great for new tanks.',
            'Easy', 'Medium to High', 'No (benefits from it)', 'Background/Floating', 'Fast',
            'https://example.com/anacharis.jpg'
        )
    ]
    cursor.executemany('''
        INSERT OR IGNORE INTO plant_species (name, description, care_level, lighting, co2_needed, placement, growth_rate, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_plants)

    conn.commit()
    conn.close()
    print(f"Sample plant data added to '{DATABASE_NAME}'.")

if __name__ == '__main__':
    create_database()
    add_sample_fish_data()
    add_sample_plant_data() # NEW: Call to add plant data

    # Optional: Verify data (modified to show both fish and plants)
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    print("\nVerifying sample fish data:")
    cursor.execute("SELECT name, diet FROM fish_species")
    for row in cursor.fetchall():
        print(f"Fish: {row}")

    print("\nVerifying sample plant data:")
    cursor.execute("SELECT name, care_level FROM plant_species")
    for row in cursor.fetchall():
        print(f"Plant: {row}")
    conn.close()