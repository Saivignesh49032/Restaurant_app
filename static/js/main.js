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

        this.init();
    }

    async init() {
        try {
            await this.fetchItems();
            
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
            this.input.disabled = false;
            this.input.placeholder = this.urlParams.city 
                ? `Search cuisines in ${this.urlParams.city}...`
                : 'Type to search cuisines...';
        }

        return this.items;
    }

    updateUrlParams(params) {
        this.urlParams = { ...this.urlParams, ...params };
        // Clear existing selections when parameters change
        this.selectedValues.clear();
        if (this.selectedItems) {
            this.selectedItems.innerHTML = '';
        }
        if (this.hiddenInput) {
            this.hiddenInput.value = '';
        }
        this.fetchItems();
    }

    onInput() {
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
}

document.addEventListener('DOMContentLoaded', () => {
    let cuisineAutocomplete;

    // Initialize autocomplete for city input
    const cityInput = document.getElementById('city');
    if (cityInput) {
        new Autocomplete(cityInput, {
            dataUrl: '/api/cities',
            hiddenInput: document.getElementById('city-hidden'),
            listContainer: document.getElementById('city-list'),
            onSelect: (city) => {
                // Update cuisine options when city changes
                if (cuisineAutocomplete) {
                    cuisineAutocomplete.updateUrlParams({ city });
                }
            }
        });
    }

    // Initialize autocomplete for cuisines
    const cuisinesInput = document.getElementById('cuisines-input');
    if (cuisinesInput) {
        cuisineAutocomplete = new Autocomplete(cuisinesInput, {
            dataUrl: '/api/cuisines',
            isMulti: true,
            selectedItems: document.getElementById('selected-cuisines'),
            hiddenInput: document.getElementById('cuisines'),
            listContainer: document.getElementById('cuisines-list')
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
            // Here you could initialize a small Leaflet map showing just this restaurant
            // For now, we'll just show the coordinates
            const mapContainer = previewMap.querySelector('.map-container');
            mapContainer.innerHTML = `
                <div class="preview-content">
                    <h4>${restaurant['Restaurant Name']}</h4>
                    <p><i class="fas fa-map-pin"></i> Location Preview</p>
                </div>
            `;
        }
    }

    // View all recommendations on map
    viewAllMapBtn.addEventListener('click', () => {
        window.location.href = '/map';
    });
});