document.addEventListener('DOMContentLoaded', () => {
    // --- Global Elements and Functions (used across multiple pages) ---
    const API_BASE_URL = 'http://127.0.0.1:5000'; // Your Flask backend URL

    // Elements for the search overlay, present on all pages
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const searchResultsOverlay = document.getElementById('search-results-overlay');
    const closeSearchResultsButton = document.getElementById('close-search-results');
    const resultsDisplay = document.getElementById('results-display'); // Inside the overlay

    // Function to show/hide the search overlay
    function toggleSearchOverlay(show) {
        if (show) {
            searchResultsOverlay.classList.add('active');
            resultsDisplay.innerHTML = `<p class="placeholder-text-search">Your search results will appear here.</p>`; // Reset content
        } else {
            searchResultsOverlay.classList.remove('active');
        }
    }

    // Function to display results within the search overlay
    function displaySearchResults(data) {
        resultsDisplay.innerHTML = ''; // Clear previous results
        resultsDisplay.classList.remove('loading');

        if (data.type === 'error') {
            resultsDisplay.innerHTML = `<p class="error-message">${data.message}</p>`;
        } else if (data.data) { // Item found
            const item = data.data;
            let htmlContent = `<div class="search-result-card">`;
            htmlContent += `<h3>${item.name}</h3>`;

            if (data.type === 'fish_species') {
                htmlContent += `<p><strong>Description:</strong> ${item.description.substring(0, 150)}...</p>`; // Short description
                htmlContent += `<p><strong>Diet:</strong> ${item.diet}</p>`;
                htmlContent += `<p><a href="fish_detail.html?name=${encodeURIComponent(item.name)}" class="view-details-link">View Full Details &rarr;</a></p>`;
            } else if (data.type === 'plant_species') {
                htmlContent += `<p><strong>Description:</strong> ${item.description.substring(0, 150)}...</p>`;
                htmlContent += `<p><strong>Care Level:</strong> ${item.care_level}</p>`;
                htmlContent += `<p><a href="plant_detail.html?name=${encodeURIComponent(item.name)}" class="view-details-link">View Full Details &rarr;</a></p>`;
            }
            htmlContent += `</div>`;
            resultsDisplay.innerHTML = htmlContent;
        } else { // Generic message if no specific data but not an error type
            resultsDisplay.innerHTML = `<p class="placeholder-text-search">${data.message}</p>`;
        }
    }

    // Function to handle search (used by all pages)
    async function performSearch() {
        const query = searchInput.value.trim();
        if (query === '') {
            resultsDisplay.innerHTML = `<p class="placeholder-text-search">Please enter a search query.</p>`;
            return;
        }

        toggleSearchOverlay(true); // Show overlay before searching
        resultsDisplay.innerHTML = `<p class="placeholder-text-search loading-message">Searching...</p>`;

        try {
            const response = await fetch(`${API_BASE_URL}/api/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`API Error: ${response.status} - ${errorData.response || JSON.stringify(errorData)}`);
            }

            const data = await response.json();
            displaySearchResults(data);

        } catch (error) {
            console.error('Error fetching search results:', error);
            resultsDisplay.innerHTML = `<p class="error-message">An error occurred while searching. (${error.message})</p>`;
            resultsDisplay.classList.remove('loading');
        }
    }

    // --- Event Listeners for Search Bar (common to all pages) ---
    if (searchButton && searchInput && searchResultsOverlay && closeSearchResultsButton) {
        searchButton.addEventListener('click', performSearch);
        searchInput.addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                performSearch();
            }
        });
        closeSearchResultsButton.addEventListener('click', () => toggleSearchOverlay(false));
        // Close overlay if clicked outside content (optional)
        searchResultsOverlay.addEventListener('click', (event) => {
            if (event.target === searchResultsOverlay) {
                toggleSearchOverlay(false);
            }
        });
    }


    // --- Page-Specific JavaScript Logic ---

    // Logic for fishes.html (Fish Listing Page)
    async function loadFishList() {
        const fishListContainer = document.getElementById('fish-list');
        if (!fishListContainer) return; // Not on fishes.html

        fishListContainer.innerHTML = `<p class="loading-message">Loading fish species...</p>`;

        try {
            const response = await fetch(`${API_BASE_URL}/api/fishes`);
            if (!response.ok) {
                throw new Error(`API Error: ${response.status} - Could not load fish list.`);
            }
            const fishes = await response.json();

            fishListContainer.innerHTML = ''; // Clear loading message

            if (fishes.length === 0) {
                fishListContainer.innerHTML = `<p class="placeholder-text-search">No fish species found in the database.</p>`;
                return;
            }

            fishes.forEach(fish => {
                const card = document.createElement('a'); // Make card clickable
                card.href = `fish_detail.html?name=${encodeURIComponent(fish.name)}`; // Link to detail page
                card.classList.add('list-card');
                card.innerHTML = `
                    <div class="list-card-image">${fish.image_url ? `<img src="${fish.image_url}" alt="${fish.name}">` : '🐠'}</div>
                    <h3>${fish.name}</h3>
                    <p>${fish.description.substring(0, 100)}...</p>
                `;
                fishListContainer.appendChild(card);
            });

        } catch (error) {
            console.error('Error loading fish list:', error);
            fishListContainer.innerHTML = `<p class="error-message">Failed to load fish species. (${error.message})</p>`;
        }
    }

    // Logic for fish_detail.html (Single Fish Detail Page)
    async function loadFishDetail() {
        const fishDetailCard = document.getElementById('fish-detail-card');
        const fishDetailSubtitle = document.getElementById('fish-detail-subtitle');
        if (!fishDetailCard) return; // Not on fish_detail.html

        const urlParams = new URLSearchParams(window.location.search);
        const speciesName = urlParams.get('name');

        if (!speciesName) {
            fishDetailCard.innerHTML = `<p class="error-message">Fish species name not provided in URL.</p>`;
            if (fishDetailSubtitle) fishDetailSubtitle.textContent = "Error";
            return;
        }

        fishDetailCard.innerHTML = `<p class="loading-message">Loading details for ${speciesName}...</p>`;
        if (fishDetailSubtitle) fishDetailSubtitle.textContent = speciesName; // Set subtitle early

        try {
            const response = await fetch(`${API_BASE_URL}/api/fish/${encodeURIComponent(speciesName)}`);
            if (response.status === 404) {
                fishDetailCard.innerHTML = `<p class="error-message">Fish species "${speciesName}" not found.</p>`;
                return;
            }
            if (!response.ok) {
                throw new Error(`API Error: ${response.status} - Could not load fish details.`);
            }
            const fish = await response.json();

            fishDetailCard.innerHTML = `
                <div class="detail-image-container">
                    ${fish.image_url ? `<img src="${fish.image_url}" alt="${fish.name}">` : '🐠'}
                </div>
                <div class="detail-info">
                    <h2>${fish.name}</h2>
                    <p><strong>Description:</strong> ${fish.description}</p>
                    <p><strong>Habitat Temp:</strong> ${fish.habitat_temp}</p>
                    <p><strong>Habitat pH:</strong> ${fish.habitat_ph}</p>
                    <p><strong>Diet:</strong> ${fish.diet}</p>
                    <p><strong>Compatibility:</strong> ${fish.compatibility}</p>
                    <p><strong>Min Tank Size:</strong> ${fish.min_tank_size_gal} gallons</p>
                    <p><strong>Plant Needs:</strong> ${fish.plant_needs}</p>
                    <p><strong>Filter Recommendation:</strong> ${fish.filter_recommendation}</p>
                </div>
            `;
        } catch (error) {
            console.error('Error loading fish details:', error);
            fishDetailCard.innerHTML = `<p class="error-message">Failed to load details for ${speciesName}. (${error.message})</p>`;
        }
    }

    // Logic for plants.html (Plant Listing Page) - Similar to fish list
    async function loadPlantList() {
        const plantListContainer = document.getElementById('plant-list');
        if (!plantListContainer) return; // Not on plants.html

        plantListContainer.innerHTML = `<p class="loading-message">Loading plant species...</p>`;

        try {
            const response = await fetch(`${API_BASE_URL}/api/plants`);
            if (!response.ok) {
                throw new Error(`API Error: ${response.status} - Could not load plant list.`);
            }
            const plants = await response.json();

            plantListContainer.innerHTML = ''; // Clear loading message

            if (plants.length === 0) {
                plantListContainer.innerHTML = `<p class="placeholder-text-search">No plant species found in the database.</p>`;
                return;
            }

            plants.forEach(plant => {
                const card = document.createElement('a'); // Make card clickable
                card.href = `plant_detail.html?name=${encodeURIComponent(plant.name)}`; // Link to detail page
                card.classList.add('list-card');
                card.innerHTML = `
                    <div class="list-card-image">${plant.image_url ? `<img src="${plant.image_url}" alt="${plant.name}">` : '🌿'}</div>
                    <h3>${plant.name}</h3>
                    <p>${plant.description.substring(0, 100)}...</p>
                `;
                plantListContainer.appendChild(card);
            });

        } catch (error) {
            console.error('Error loading plant list:', error);
            plantListContainer.innerHTML = `<p class="error-message">Failed to load plant species. (${error.message})</p>`;
        }
    }

    // Logic for plant_detail.html (Single Plant Detail Page) - Similar to fish detail
    async function loadPlantDetail() {
        const plantDetailCard = document.getElementById('plant-detail-card');
        const plantDetailSubtitle = document.getElementById('plant-detail-subtitle');
        if (!plantDetailCard) return; // Not on plant_detail.html

        const urlParams = new URLSearchParams(window.location.search);
        const speciesName = urlParams.get('name');

        if (!speciesName) {
            plantDetailCard.innerHTML = `<p class="error-message">Plant species name not provided in URL.</p>`;
            if (plantDetailSubtitle) plantDetailSubtitle.textContent = "Error";
            return;
        }

        plantDetailCard.innerHTML = `<p class="loading-message">Loading details for ${speciesName}...</p>`;
        if (plantDetailSubtitle) plantDetailSubtitle.textContent = speciesName; // Set subtitle early

        try {
            const response = await fetch(`${API_BASE_URL}/api/plant/${encodeURIComponent(speciesName)}`);
            if (response.status === 404) {
                plantDetailCard.innerHTML = `<p class="error-message">Plant species "${speciesName}" not found.</p>`;
                return;
            }
            if (!response.ok) {
                throw new Error(`API Error: ${response.status} - Could not load plant details.`);
            }
            const plant = await response.json();

            plantDetailCard.innerHTML = `
                <div class="detail-image-container">
                    ${plant.image_url ? `<img src="${plant.image_url}" alt="${plant.name}">` : '🌿'}
                </div>
                <div class="detail-info">
                    <h2>${plant.name}</h2>
                    <p><strong>Description:</strong> ${plant.description}</p>
                    <p><strong>Care Level:</strong> ${plant.care_level}</p>
                    <p><strong>Lighting:</strong> ${plant.lighting}</p>
                    <p><strong>CO2 Needed:</strong> ${plant.co2_needed}</p>
                    <p><strong>Placement:</strong> ${plant.placement}</p>
                    <p><strong>Growth Rate:</strong> ${plant.growth_rate}</p>
                </div>
            `;
        } catch (error) {
            console.error('Error loading plant details:', error);
            plantDetailCard.innerHTML = `<p class="error-message">Failed to load details for ${speciesName}. (${error.message})</p>`;
        }
    }


    // --- Initialize page-specific logic on load ---
    if (document.getElementById('fish-list')) {
        loadFishList();
    } else if (document.getElementById('fish-detail-card')) {
        loadFishDetail();
    } else if (document.getElementById('plant-list')) {
        loadPlantList();
    } else if (document.getElementById('plant-detail-card')) {
        loadPlantDetail();
    }
});