// Autocomplete functionality for city and cuisine inputs
class Autocomplete {
    constructor(input, options = {}) {
        this.input = input;
        this.wrapper = input.closest('.autocomplete-wrapper');
        this.listContainer = options.listContainer || this.wrapper.querySelector('.autocomplete-list');
        this.selectedItems = options.selectedItems || null;
        this.isMulti = options.isMulti || false;
        this.hiddenInput = options.hiddenInput || null;
        this.dataUrl = options.dataUrl || '';
        this.urlParams = options.urlParams || {};
        this.onSelect = options.onSelect || null;
        this.items = [];
        this.filteredItems = [];
        this.selectedIndex = -1;
        this.selectedValues = new Set();
        this.autoFetch = options.autoFetch !== false;
        this.isDisabled = options.disabled || false;

        this.init();
    }

    async init() {
        try {
            if (this.isDisabled) {
                this.toggleDisabledState(true);
            }

            if (this.autoFetch) {
                await this.fetchItems();
            }
            
            this.input.addEventListener('input', () => this.onInput());
            this.input.addEventListener('keydown', (e) => this.onKeydown(e));
            document.addEventListener('click', (e) => this.onClick(e));
            
            if (this.listContainer) {
                this.listContainer.addEventListener('click', (e) => this.onListClick(e));
            }
        } catch (error) {
            console.error('Error fetching autocomplete data:', error);
        }
    }

    async fetchItems() {
        const url = new URL(this.dataUrl, window.location.origin);
        // Add any URL parameters
        Object.entries(this.urlParams).forEach(([key, value]) => {
            if (value) url.searchParams.append(key, value);
        });

        const shouldRemainDisabled = this.isDisabled;

        // Add loading state if this is the cuisine input
        if (this.input.id === 'cuisines-input') {
            this.wrapper.classList.add('loading');
            // Clear the input and disable it temporarily
            this.input.value = '';
            this.input.placeholder = 'Loading cuisines...';
            this.input.disabled = true;
        }

        const response = await fetch(url);
        this.items = await response.json();

        // Remove loading state if this is the cuisine input
        if (this.input.id === 'cuisines-input') {
            this.wrapper.classList.remove('loading');
            this.input.disabled = shouldRemainDisabled;
            if (!shouldRemainDisabled) {
                this.input.placeholder = this.urlParams.city 
                    ? `Search cuisines in ${this.urlParams.city}...`
                    : 'Type to search cuisines...';
            } else {
                this.input.placeholder = 'Select a city first...';
            }
        }

        return this.items;
    }

    updateUrlParams(params) {
        this.urlParams = { ...this.urlParams, ...params };
        // Clear existing selections when parameters change
        this.resetSelections();
        return this.fetchItems();
    }

    onInput() {
        if (this.isDisabled) return;
        const value = this.input.value.toLowerCase().trim();
        this.filteredItems = this.items.filter(item => {
            return !this.selectedValues.has(item) && 
                   item.toLowerCase().includes(value);
        });
        this.renderList();
    }

    renderList() {
        if (!this.listContainer) return;

        if (!this.input.value.trim()) {
            this.listContainer.classList.remove('active');
            return;
        }

        this.listContainer.innerHTML = '';
        this.selectedIndex = -1;
        const searchValue = this.input.value.toLowerCase().trim();

        this.filteredItems.forEach(item => {
            const div = document.createElement('div');
            div.className = 'autocomplete-item';
            
            // Highlight matching text
            const itemText = item.toString();
            const matchIndex = itemText.toLowerCase().indexOf(searchValue);
            if (matchIndex >= 0) {
                const before = itemText.substring(0, matchIndex);
                const match = itemText.substring(matchIndex, matchIndex + searchValue.length);
                const after = itemText.substring(matchIndex + searchValue.length);
                div.innerHTML = `${before}<span class="highlight">${match}</span>${after}`;
            } else {
                div.textContent = itemText;
            }
            
            div.dataset.value = item;
            this.listContainer.appendChild(div);
        });

        this.listContainer.classList.toggle('active', this.filteredItems.length > 0);
    }

    onKeydown(e) {
        const items = this.listContainer?.querySelectorAll('.autocomplete-item') || [];
        
        switch(e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, items.length - 1);
                this.highlightItem();
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.highlightItem();
                break;
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0 && items[this.selectedIndex]) {
                    this.selectItem(items[this.selectedIndex].dataset.value);
                }
                break;
            case 'Escape':
                this.listContainer?.classList.remove('active');
                this.selectedIndex = -1;
                break;
        }
    }

    highlightItem() {
        const items = this.listContainer?.querySelectorAll('.autocomplete-item') || [];
        items.forEach((item, index) => {
            item.classList.toggle('highlighted', index === this.selectedIndex);
        });
    }

    selectItem(value) {
        if (this.isMulti) {
            if (!this.selectedValues.has(value)) {
                this.selectedValues.add(value);
                this.addTag(value);
                this.updateHiddenInput();
            }
            this.input.value = '';
        } else {
            this.input.value = value;
            if (this.hiddenInput) {
                this.hiddenInput.value = value;
            }
            if (this.onSelect) {
                this.onSelect(value);
            }
        }

        this.listContainer?.classList.remove('active');
    }

    addTag(value) {
        if (!this.selectedItems) return;

        const tag = document.createElement('div');
        tag.className = 'selected-tag';
        tag.innerHTML = `
            ${value}
            <span class="remove" data-value="${value}">&times;</span>
        `;

        tag.querySelector('.remove').addEventListener('click', () => {
            this.removeTag(value);
        });

        this.selectedItems.appendChild(tag);
    }

    removeTag(value) {
        this.selectedValues.delete(value);
        const tag = this.selectedItems.querySelector(`[data-value="${value}"]`).parentElement;
        if (tag) {
            tag.remove();
        }
        this.updateHiddenInput();
    }

    updateHiddenInput() {
        if (this.hiddenInput) {
            this.hiddenInput.value = Array.from(this.selectedValues).join(',');
        }
    }

    onClick(e) {
        if (!this.wrapper.contains(e.target)) {
            this.listContainer?.classList.remove('active');
        }
    }

    onListClick(e) {
        const item = e.target.closest('.autocomplete-item');
        if (item) {
            this.selectItem(item.dataset.value);
        }
    }

    toggleDisabledState(disabled) {
        this.isDisabled = disabled;
        if (this.wrapper) {
            this.wrapper.classList.toggle('input-disabled', disabled);
        }
        if (this.input) {
            this.input.disabled = disabled;
            if (disabled) {
                this.input.value = '';
                if (this.listContainer) {
                    this.listContainer.classList.remove('active');
                }
                if (this.input.id === 'cuisines-input') {
                    this.input.placeholder = 'Select a city first...';
                }
            } else if (this.input.id === 'cuisines-input') {
                this.input.placeholder = this.urlParams.city
                    ? `Search cuisines in ${this.urlParams.city}...`
                    : 'Type to search cuisines...';
            }
        }
    }

    setDisabled(disabled) {
        this.toggleDisabledState(disabled);
        if (disabled) {
            this.clearData();
            this.resetSelections();
        }
    }

    resetSelections() {
        this.selectedValues.clear();
        if (this.selectedItems) {
            this.selectedItems.innerHTML = '';
        }
        if (this.hiddenInput) {
            this.hiddenInput.value = '';
        }
    }

    clearData() {
        this.items = [];
        this.filteredItems = [];
        this.selectedIndex = -1;
        if (this.listContainer) {
            this.listContainer.innerHTML = '';
            this.listContainer.classList.remove('active');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Cuisine Dropdown Handler
    const cuisineDropdown = {
        toggle: document.getElementById('cuisines-dropdown-toggle'),
        menu: document.getElementById('cuisines-dropdown'),
        items: document.getElementById('cuisines-items'),
        search: document.getElementById('cuisines-search'),
        selectedItems: document.getElementById('selected-cuisines'),
        hiddenInput: document.getElementById('cuisines'),
        placeholder: document.querySelector('#cuisines-dropdown-toggle .dropdown-placeholder'),
        allCuisines: [],
        filteredCuisines: [],
        selectedValues: new Set(),
        currentCity: null,

        init() {
            if (!this.toggle || !this.menu) return;

            // Toggle dropdown
            this.toggle.addEventListener('click', (e) => {
                e.stopPropagation();
                if (!this.toggle.disabled) {
                    this.toggle.classList.toggle('active');
                    this.menu.classList.toggle('active');
                    if (this.menu.classList.contains('active') && this.search) {
                        this.search.focus();
                    }
                }
            });

            // Close dropdown when clicking outside
            document.addEventListener('click', (e) => {
                if (!this.menu.contains(e.target) && !this.toggle.contains(e.target)) {
                    this.close();
                }
            });

            // Search filter
            if (this.search) {
                this.search.addEventListener('input', () => {
                    this.filterCuisines();
                });
            }

            // Prevent dropdown from closing when clicking inside
            this.menu.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        },

        async loadCuisines(city) {
            if (!city) return;

            this.currentCity = city;
            this.toggle.disabled = false;
            if (this.placeholder) {
                this.placeholder.textContent = `Select cuisines in ${city}...`;
            }

            // Clear search
            if (this.search) {
                this.search.value = '';
            }

            try {
                const response = await fetch(`/api/cuisines?city=${encodeURIComponent(city)}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                this.allCuisines = await response.json();
                this.filteredCuisines = [...this.allCuisines];
                this.renderItems();
            } catch (error) {
                console.error('Error loading cuisines:', error);
                if (this.items) {
                    this.items.innerHTML = '<p class="dropdown-empty">Error loading cuisines</p>';
                }
            }
        },

        filterCuisines() {
            const searchValue = this.search.value.toLowerCase().trim();
            this.filteredCuisines = this.allCuisines.filter(cuisine => {
                const matchesSearch = !searchValue || cuisine.toLowerCase().includes(searchValue);
                return matchesSearch;
            });
            this.renderItems();
        },

        renderItems() {
            if (!this.items) return;

            if (this.filteredCuisines.length === 0) {
                this.items.innerHTML = '<p class="dropdown-empty">No cuisines found</p>';
                return;
            }

            this.items.innerHTML = '';
            this.filteredCuisines.forEach(cuisine => {
                const item = document.createElement('div');
                item.className = 'dropdown-item';
                const isSelected = this.selectedValues.has(cuisine);
                const safeId = cuisine.replace(/[^a-zA-Z0-9]/g, '-');
                item.innerHTML = `
                    <input type="checkbox" id="cuisine-${safeId}" ${isSelected ? 'checked' : ''}>
                    <label for="cuisine-${safeId}">${cuisine}</label>
                `;
                
                const checkbox = item.querySelector('input[type="checkbox"]');
                if (checkbox) {
                    checkbox.addEventListener('change', () => {
                        this.toggleCuisine(cuisine);
                    });
                }

                this.items.appendChild(item);
            });
        },

        toggleCuisine(cuisine) {
            if (this.selectedValues.has(cuisine)) {
                this.selectedValues.delete(cuisine);
                this.removeTag(cuisine);
            } else {
                this.selectedValues.add(cuisine);
                this.addTag(cuisine);
            }
            this.updateHiddenInput();
            this.renderItems(); // Re-render to update checkboxes
        },

        addTag(cuisine) {
            if (!this.selectedItems) return;

            const tag = document.createElement('div');
            tag.className = 'selected-tag';
            tag.innerHTML = `
                ${cuisine}
                <span class="remove" data-value="${cuisine}">&times;</span>
            `;

            tag.querySelector('.remove').addEventListener('click', () => {
                this.removeTag(cuisine);
            });

            this.selectedItems.appendChild(tag);
        },

        removeTag(cuisine) {
            this.selectedValues.delete(cuisine);
            const tag = this.selectedItems.querySelector(`[data-value="${cuisine}"]`);
            if (tag) {
                tag.parentElement.remove();
            }
            this.updateHiddenInput();
            this.renderItems(); // Re-render to update checkboxes
        },

        updateHiddenInput() {
            if (this.hiddenInput) {
                this.hiddenInput.value = Array.from(this.selectedValues).join(',');
            }
        },

        reset() {
            this.selectedValues.clear();
            if (this.selectedItems) {
                this.selectedItems.innerHTML = '';
            }
            if (this.hiddenInput) {
                this.hiddenInput.value = '';
            }
            if (this.search) {
                this.search.value = '';
            }
            this.allCuisines = [];
            this.filteredCuisines = [];
            this.currentCity = null;
            if (this.toggle) {
                this.toggle.disabled = true;
            }
            if (this.placeholder) {
                this.placeholder.textContent = 'Select a city first...';
            }
            if (this.items) {
                this.items.innerHTML = '<p class="dropdown-empty">Select a city to see available cuisines</p>';
            }
            this.close();
        },

        close() {
            if (this.toggle) {
                this.toggle.classList.remove('active');
            }
            if (this.menu) {
                this.menu.classList.remove('active');
            }
        }
    };

    cuisineDropdown.init();

    // Initialize autocomplete for city input
    const cityInput = document.getElementById('city');
    if (cityInput) {
        const cityHiddenInput = document.getElementById('city-hidden');
        new Autocomplete(cityInput, {
            dataUrl: '/api/cities',
            hiddenInput: cityHiddenInput,
            listContainer: document.getElementById('city-list'),
            onSelect: (city) => {
                // Load cuisines for selected city
                cuisineDropdown.loadCuisines(city);
            }
        });

        cityInput.addEventListener('input', () => {
            const typedValue = cityInput.value.trim();
            if (!typedValue) {
                if (cityHiddenInput) {
                    cityHiddenInput.value = '';
                }
                cuisineDropdown.reset();
            } else if (cityHiddenInput && cityHiddenInput.value !== typedValue) {
                cityHiddenInput.value = '';
                cuisineDropdown.reset();
            }
        });
    }

    const recoForm = document.getElementById('reco-form');
    const resultsList = document.getElementById('results-list');
    const visitTypeRadios = document.getElementsByName('visitType');
    const tableBookingGroup = document.getElementById('table-booking-group');
    const viewAllMapBtn = document.getElementById('view-all-map');
    const sortBySelect = document.getElementById('sort-by');
    let currentRestaurants = [];

    // Function to show/hide table booking based on visit/delivery
    function toggleTableBooking() {
        const selectedType = document.querySelector('input[name="visitType"]:checked').value;
        tableBookingGroup.classList.toggle('hidden', selectedType !== 'visit');
    }

    // Add event listeners to radio buttons
    visitTypeRadios.forEach(radio => {
        radio.addEventListener('change', toggleTableBooking);
    });
    
    // Initial check
    toggleTableBooking();

    // Sort results when sort option changes
    sortBySelect.addEventListener('change', () => {
        if (currentRestaurants.length > 0) {
            displayResults(currentRestaurants);
        }
    });

    // Handle form submission
    recoForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Show loading message
        resultsList.innerHTML = '<p class="loading"><i class="fas fa-spinner fa-spin"></i> Finding the best restaurants for you...</p>';
        viewAllMapBtn.classList.add('hidden');

        // Get form values
        const formData = new FormData(recoForm);
        const userPreferences = {
            city: formData.get('city'),
            cuisines: formData.get('cuisines'),
            priceRange: formData.get('priceRange'),
            visitType: formData.get('visitType'),
            tableBooking: formData.get('tableBooking')
        };

        try {
            // Add loading state to submit button
            const submitBtn = recoForm.querySelector('.submit-btn');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner"></i> Searching...';
            submitBtn.classList.add('loading');

            const response = await fetch('/api/recommend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userPreferences)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            currentRestaurants = await response.json();
            
            // Restore button state
            submitBtn.innerHTML = originalBtnText;
            submitBtn.classList.remove('loading');

            // Animate results appearance
            resultsList.style.opacity = '0';
            displayResults(currentRestaurants);
            viewAllMapBtn.classList.remove('hidden');
            
            // Smooth scroll to results on mobile
            if (window.innerWidth <= 1024) {
                resultsList.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
            
            // Fade in results
            setTimeout(() => {
                resultsList.style.opacity = '1';
                resultsList.style.transition = 'opacity var(--transition-normal)';
            }, 100);

        } catch (error) {
            console.error('Error fetching recommendations:', error);
            resultsList.innerHTML = `
                <p class="error-message">
                    <i class="fas fa-exclamation-circle"></i>
                    Error: ${error.message}
                </p>`;
        }
    });

    // Function to sort restaurants based on selected criteria
    function sortRestaurants(restaurants) {
        const sortBy = sortBySelect.value;
        return [...restaurants].sort((a, b) => {
            switch (sortBy) {
                case 'rating':
                    return b['Aggregate rating'] - a['Aggregate rating'];
                case 'cost':
                    return a['Average Cost for two'] - b['Average Cost for two'];
                case 'similarity':
                    return b['Similarity Score'] - a['Similarity Score'];
                default:
                    return 0;
            }
        });
    }

    // Function to render restaurant cards
    function displayResults(restaurants) {
        resultsList.innerHTML = '';

        if (!restaurants || restaurants.length === 0) {
            resultsList.innerHTML = `
                <p class="no-results">
                    <i class="fas fa-search"></i>
                    Sorry, no restaurants match your criteria. Please try different options!
                </p>`;
            return;
        }

        const sortedRestaurants = sortRestaurants(restaurants);

        sortedRestaurants.forEach(r => {
            const card = document.createElement('div');
            card.className = 'restaurant-card';
            
            const rating = parseFloat(r['Aggregate rating']).toFixed(1);
            const similarity = (parseFloat(r['Similarity Score']) * 100).toFixed(1);
            const delivery = r['Has Online delivery'] === 1;
            const booking = r['Has Table booking'] === 1;
            const latitude = r['Latitude'];
            const longitude = r['Longitude'];
            const hasCoordinates = latitude !== undefined && latitude !== null && latitude !== '' &&
                longitude !== undefined && longitude !== null && longitude !== '';
            const directionsUrl = hasCoordinates
                ? `https://www.google.com/maps/dir/?api=1&destination=${latitude},${longitude}`
                : null;

            card.innerHTML = `
                <div class="card-header">
                    <h3>${r['Restaurant Name']}</h3>
                    <div class="rating">
                        <span class="rating-value">${rating}</span>
                        <i class="fas fa-star"></i>
                    </div>
                </div>
                <div class="card-body">
                    <p class="cuisines">
                        <i class="fas fa-utensils"></i> ${r['Cuisines']}
                    </p>
                    <p class="cost">
                        <i class="fas fa-rupee-sign"></i> ${r['Average Cost for two']} for two
                    </p>
                    <p class="features">
                        ${delivery ? '<span class="feature"><i class="fas fa-motorcycle"></i> Delivery</span>' : ''}
                        ${booking ? '<span class="feature"><i class="fas fa-chair"></i> Table Booking</span>' : ''}
                    </p>
                    <div class="similarity">
                        <div class="similarity-bar" style="width: ${similarity}%"></div>
                        <span>${similarity}% match</span>
                    </div>
                </div>
                <div class="card-actions">
                    <button class="view-map-btn" onclick="window.location.href='/map?highlight=${r['Restaurant ID']}'">
                        <i class="fas fa-map-marker-alt"></i> View on Map
                    </button>
                    ${directionsUrl ? `
                        <button class="directions-btn" onclick="window.open('${directionsUrl}', '_blank')">
                            <i class="fas fa-route"></i> Directions
                        </button>` : ''}
                </div>
            `;
            resultsList.appendChild(card);

            // Add hover effect to show preview map
            card.addEventListener('mouseenter', () => {
                showPreviewMap(r);
            });
        });
    }

    // Function to show preview map
    function showPreviewMap(restaurant) {
        const previewMap = document.getElementById('preview-map');
        if (previewMap) {
            previewMap.classList.remove('hidden');
            
            // Update action buttons
            const viewInMapBtn = document.getElementById('view-in-map');
            const getDirectionsBtn = document.getElementById('get-directions');
            
            viewInMapBtn.onclick = () => {
                window.location.href = `/map?highlight=${restaurant['Restaurant ID']}`;
            };
            
            getDirectionsBtn.onclick = () => {
                const url = `https://www.google.com/maps/dir/?api=1&destination=${restaurant['Latitude']},${restaurant['Longitude']}`;
                window.open(url, '_blank');
            };
            const mapContainer = previewMap.querySelector('.map-container');

            // Clear previous map if exists
            mapContainer.innerHTML = '';

            // Initialize Leaflet map
            const map = L.map(mapContainer, {
                zoomControl: false,  // Disable zoom controls for preview
                dragging: false,     // Disable dragging for preview
                touchZoom: false,
                scrollWheelZoom: false
            }).setView([restaurant['Latitude'], restaurant['Longitude']], 15);

            // Add tile layer
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);

            // Add marker with custom popup
            const marker = L.marker([restaurant['Latitude'], restaurant['Longitude']])
                .addTo(map)
                .bindPopup(`
                    <div class="preview-popup">
                        <h4>${restaurant['Restaurant Name']}</h4>
                        <p class="rating">
                            <i class="fas fa-star"></i> ${restaurant['Aggregate rating']}
                        </p>
                        <p class="cuisines">
                            <i class="fas fa-utensils"></i> ${restaurant['Cuisines']}
                        </p>
                        <p class="cost">
                            <i class="fas fa-rupee-sign"></i> ${restaurant['Average Cost for two']} for two
                        </p>
                    </div>
                `, {
                    closeButton: false,
                    className: 'preview-popup'
                });
            
            // Auto-open the popup
            marker.openPopup();
        }
    }

    // View all recommendations on map
    viewAllMapBtn.addEventListener('click', () => {
        window.location.href = '/map';
    });
});