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

        switch (e.key) {
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
    const profileSummaryText = document.getElementById('profile-summary-text');
    const editProfileBtn = document.getElementById('edit-profile-btn');
    const applyProfileBtn = document.getElementById('apply-profile-btn');
    const profileModal = document.getElementById('profile-modal');
    const closeProfileModalBtn = document.getElementById('close-profile-modal');
    const profileForm = document.getElementById('profile-form');
    const profileFavoriteInput = document.getElementById('profile-favorite-cuisines');
    const profileDietaryGroup = document.getElementById('profile-dietary-group');
    const profileBudgetSelect = document.getElementById('profile-budget');
    const profileVisitTypeSelect = document.getElementById('profile-visit-type');
    const profileTableBookingSelect = document.getElementById('profile-table-booking');
    const profileMoodsInput = document.getElementById('profile-moods');
    const profileOccasionsInput = document.getElementById('profile-occasions');
    const profileCuisineSearch = document.getElementById('profile-cuisine-search');
    const profileCuisineOptions = document.getElementById('profile-cuisine-options');
    const bookmarksList = document.getElementById('bookmarks-list');
    const historyList = document.getElementById('history-list');
    const refreshBookmarksBtn = document.getElementById('refresh-bookmarks-btn');
    const refreshHistoryBtn = document.getElementById('refresh-history-btn');
    const planItineraryBtn = document.getElementById('plan-itinerary-btn');
    const itineraryOutput = document.getElementById('itinerary-output');
    let userProfile = null;
    let bookmarksState = [];
    let historyEvents = [];
    const selectedBookmarkIds = new Set();
    let profileCuisineSelections = new Set();
    let availableProfileCuisines = [];
    const profileCuisineCountDisplay = document.getElementById('profile-cuisine-count');
    const profileDietaryCountDisplay = document.getElementById('profile-dietary-count');
    const profileBookmarkCountDisplay = document.getElementById('profile-bookmark-count');
    const profileHistoryCountDisplay = document.getElementById('profile-history-count');
    const quickChips = document.querySelectorAll('.quick-chip');
    const moodFilter = document.getElementById('moodFilter');
    const occasionFilter = document.getElementById('occasionFilter');

    async function loadProfileCuisines() {
        if (!profileCuisineOptions) return;
        try {
            const response = await fetch('/api/cuisines');
            if (!response.ok) throw new Error('Failed to load cuisines');
            availableProfileCuisines = (await response.json()).sort((a, b) =>
                a.localeCompare(b, undefined, { sensitivity: 'base' })
            );
            renderProfileCuisineOptions(profileCuisineSearch?.value || '');
        } catch (error) {
            console.error('Failed to fetch cuisine list', error);
            profileCuisineOptions.innerHTML = '<p class="empty-state">Unable to load cuisines right now.</p>';
        }
    }

    function renderProfileCuisineOptions(searchTerm = '') {
        if (!profileCuisineOptions) return;
        if (!availableProfileCuisines.length) {
            profileCuisineOptions.innerHTML = '<p class="empty-state">Loading cuisines...</p>';
            return;
        }
        const normalized = searchTerm.trim().toLowerCase();
        const filtered = availableProfileCuisines.filter(cuisine =>
            cuisine.toLowerCase().includes(normalized)
        );
        if (!filtered.length) {
            profileCuisineOptions.innerHTML = '<p class="empty-state">No cuisines match your search.</p>';
            return;
        }
        profileCuisineOptions.innerHTML = '';
        filtered.forEach(cuisine => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = `cuisine-chip ${profileCuisineSelections.has(cuisine) ? 'selected' : ''}`;
            btn.textContent = cuisine;
            btn.addEventListener('click', () => toggleProfileCuisine(cuisine));
            profileCuisineOptions.appendChild(btn);
        });
    }

    function toggleProfileCuisine(cuisine) {
        if (profileCuisineSelections.has(cuisine)) {
            profileCuisineSelections.delete(cuisine);
        } else {
            profileCuisineSelections.add(cuisine);
        }
        syncCuisineInputFromSet();
        renderProfileCuisineOptions(profileCuisineSearch?.value || '');
    }

    function syncCuisineInputFromSet() {
        if (profileFavoriteInput) {
            profileFavoriteInput.value = Array.from(profileCuisineSelections).join(', ');
        }
    }

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

        setSelectedCuisines(cuisineList = []) {
            this.selectedValues.clear();
            cuisineList.forEach(cuisine => this.selectedValues.add(cuisine));
            if (this.selectedItems) {
                this.selectedItems.innerHTML = '';
                this.selectedValues.forEach(cuisine => this.addTag(cuisine));
            }
            this.updateHiddenInput();
            this.renderItems();
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
    window.cuisineDropdown = cuisineDropdown;

    function updateProfileSummary() {
        if (!profileSummaryText || !userProfile) return;
        const cuisines = (userProfile.favorite_cuisines || []).slice(0, 3).join(', ') || 'Not set';
        const minBand = userProfile.budget_band_min ?? userProfile.budget;
        const maxBand = userProfile.budget_band_max ?? userProfile.budget;
        let budget = 'Budget not set';
        if (minBand && maxBand) {
            budget = minBand === maxBand
                ? `Budget level ${minBand}`
                : `Budget levels ${minBand}-${maxBand}`;
        }
        profileSummaryText.textContent = `${cuisines} · ${budget}`;
    }

    function updateProfileStatsFromProfile() {
        if (!userProfile) return;
        setProfileStat(profileCuisineCountDisplay, userProfile.favorite_cuisines?.length || 0);
        const dietaryCount = Array.isArray(userProfile.dietary_needs) ? userProfile.dietary_needs.length : 0;
        setProfileStat(profileDietaryCountDisplay, dietaryCount);
    }

    function setProfileStat(element, value) {
        if (element) {
            element.textContent = value;
        }
    }

    function populateProfileForm() {
        if (!userProfile || !profileForm) return;
        profileCuisineSelections = new Set(userProfile.favorite_cuisines || []);
        if (profileFavoriteInput) {
            profileFavoriteInput.value = Array.from(profileCuisineSelections).join(', ');
        }
        if (profileBudgetSelect) {
            profileBudgetSelect.value = userProfile.budget_band_min || userProfile.budget || '2';
        }
        if (profileVisitTypeSelect) {
            profileVisitTypeSelect.value = userProfile.preferred_visit_type || 'visit';
        }
        if (profileTableBookingSelect) {
            profileTableBookingSelect.value = userProfile.preferred_table_booking || 'No';
        }
        if (profileMoodsInput) {
            profileMoodsInput.value = (userProfile.mood_tags || []).join(', ');
        }
        if (profileOccasionsInput) {
            profileOccasionsInput.value = (userProfile.occasion_tags || []).join(', ');
        }
        const dietary = new Set(userProfile.dietary_needs || []);
        profileDietaryGroup.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        profileDietaryGroup.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.checked = dietary.has(cb.value);
        });
        renderProfileCuisineOptions(profileCuisineSearch?.value || '');
    }

    function openProfileModal() {
        if (!profileModal) return;
        profileModal.classList.remove('hidden');
        populateProfileForm();
    }

    function closeProfileModal() {
        profileModal?.classList.add('hidden');
    }

    function collectProfileFormData() {
        const dietarySelections = Array.from(profileDietaryGroup.querySelectorAll('input[type="checkbox"]:checked')).map(cb => cb.value);
        const favoriteCuisines = (profileFavoriteInput?.value || '').split(',').map(v => v.trim()).filter(Boolean);
        if (profileCuisineSelections.size === 0 && favoriteCuisines.length) {
            profileCuisineSelections = new Set(favoriteCuisines);
        }
        const cuisines = profileCuisineSelections.size ? Array.from(profileCuisineSelections) : favoriteCuisines;
        const budgetValue = Number(profileBudgetSelect?.value || 2);
        return {
            favorite_cuisines: cuisines,
            dietary_needs: dietarySelections,
            budget_band_min: budgetValue,
            budget_band_max: budgetValue,
            flexible_prefs: {
                favorite_cuisines: cuisines,
                dietary_tags: dietarySelections
            },
            preferred_visit_type: profileVisitTypeSelect?.value,
            preferred_table_booking: profileTableBookingSelect?.value,
            mood_tags: (profileMoodsInput?.value || '').split(',').map(v => v.trim()).filter(Boolean),
            occasion_tags: (profileOccasionsInput?.value || '').split(',').map(v => v.trim()).filter(Boolean)
        };
    }

    async function loadProfile(applyToForm = false) {
        try {
            const response = await fetch('/api/v1/preferences');
            if (!response.ok) throw new Error('Unable to load profile');
            userProfile = await response.json();
            updateProfileSummary();
            updateProfileStatsFromProfile();
            if (applyToForm) {
                applyProfileToForm();
            }
        } catch (error) {
            console.error('Profile load failed', error);
            if (profileSummaryText) {
                profileSummaryText.textContent = 'No profile yet — personalize to improve recommendations.';
            }
        }
    }

    function applyProfileToForm() {
        if (!userProfile) return;
        const budgetValue = userProfile.budget_band_min || userProfile.budget;
        if (budgetValue && priceRangeSelect) {
            priceRangeSelect.value = budgetValue;
        }
        if (userProfile.preferred_visit_type) {
            document.querySelector(`input[name="visitType"][value="${userProfile.preferred_visit_type}"]`)?.click();
        }
        if (userProfile.preferred_table_booking && tableBookingSelect) {
            tableBookingSelect.value = userProfile.preferred_table_booking;
        }
        if (userProfile.saved_filters && userProfile.saved_filters.city && cityInput) {
            cityInput.value = userProfile.saved_filters.city;
            cityHiddenInput.value = userProfile.saved_filters.city;
        }
    }

    async function loadBookmarks() {
        try {
            const response = await fetch('/api/bookmarks');
            if (!response.ok) throw new Error('Unable to load bookmarks');
            bookmarksState = await response.json();
            setProfileStat(profileBookmarkCountDisplay, bookmarksState.length);
            renderBookmarks();
        } catch (error) {
            console.error('Bookmarks load failed', error);
        }
    }

    function renderBookmarks() {
        if (!bookmarksList) return;
        bookmarksList.innerHTML = '';
        selectedBookmarkIds.clear();
        if (!bookmarksState.length) {
            bookmarksList.innerHTML = '<li class="empty-state">No bookmarks yet. Tap the bookmark icon on any card.</li>';
            planItineraryBtn.disabled = true;
            return;
        }
        bookmarksState.forEach(bookmark => {
            const li = document.createElement('li');
            li.className = 'bookmark-item';
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.dataset.bookmarkId = bookmark.bookmark_id;
            checkbox.addEventListener('change', () => {
                if (checkbox.checked) {
                    selectedBookmarkIds.add(bookmark.bookmark_id);
                } else {
                    selectedBookmarkIds.delete(bookmark.bookmark_id);
                }
                planItineraryBtn.disabled = selectedBookmarkIds.size < 2;
            });
            const label = document.createElement('label');
            label.innerHTML = `<strong>${bookmark.name}</strong><span>${bookmark.city || ''}</span>`;
            li.appendChild(checkbox);
            li.appendChild(label);
            bookmarksList.appendChild(li);
        });
        planItineraryBtn.disabled = selectedBookmarkIds.size < 2;
    }

    async function loadHistory() {
        try {
            const response = await fetch('/api/history');
            if (!response.ok) throw new Error('Unable to load history');
            historyEvents = await response.json();
            const itineraryCount = historyEvents.filter(event => event.type === 'itinerary').length;
            setProfileStat(profileHistoryCountDisplay, itineraryCount);
            renderHistory();
        } catch (error) {
            console.error('History load failed', error);
        }
    }

    function renderHistory() {
        if (!historyList) return;
        historyList.innerHTML = '';
        if (!historyEvents.length) {
            historyList.innerHTML = '<li class="empty-state">Submit a search to build history.</li>';
            return;
        }
        historyEvents.slice().reverse().forEach(event => {
            const li = document.createElement('li');
            li.className = 'history-item';
            li.innerHTML = `<span>${event.type || 'search'} · ${event.city || ''}</span><span>${event.results || 0} results</span>`;
            historyList.appendChild(li);
        });
    }

    function closeItineraryOutput(message) {
        if (itineraryOutput) {
            itineraryOutput.innerHTML = `<p class="empty-state">${message}</p>`;
        }
    }

    async function planItinerary() {
        if (selectedBookmarkIds.size < 2) {
            closeItineraryOutput('Pick at least two bookmarks.');
            return;
        }
        const selectedStops = bookmarksState.filter(b => selectedBookmarkIds.has(b.bookmark_id));
        try {
            const response = await fetch('/api/itinerary', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ stops: selectedStops })
            });
            if (!response.ok) {
                throw new Error('Failed to build itinerary');
            }
            const itinerary = await response.json();
            renderItinerary(itinerary);
        } catch (error) {
            console.error('Itinerary failed', error);
            closeItineraryOutput('Could not build itinerary. Try again.');
        }
    }

    function renderItinerary(itinerary) {
        if (!itineraryOutput) return;
        itineraryOutput.innerHTML = `
            <p><strong>Total distance:</strong> ${itinerary.total_distance_km} km</p>
            <p><strong>Travel time:</strong> ${itinerary.total_travel_time_minutes} mins</p>
            <ol>${itinerary.route.map(stop => `<li>${stop.name || 'Stop'} · ${stop.city || ''}</li>`).join('')}</ol>
            <a href="${itinerary.share_link}" target="_blank" rel="noopener">Open in Google Maps</a>
        `;
    }

    function buildBookmarkPayload(restaurant) {
        return {
            restaurant_id: restaurant['Restaurant ID'] || restaurant['restaurant_id'] || restaurant['id'] || restaurant['name'],
            name: restaurant['Restaurant Name'] || restaurant['name'],
            city: restaurant['City'] || restaurant['city'],
            cuisines: restaurant['Cuisines'] || (restaurant['cuisines'] ? restaurant['cuisines'].join?.(', ') || restaurant['cuisines'] : ''),
            rating: restaurant['Aggregate rating'] || restaurant['rating'],
            average_cost_for_two: restaurant['Average Cost for two'] || restaurant['cost_for_two'],
            latitude: restaurant['Latitude'] || restaurant['latitude'],
            longitude: restaurant['Longitude'] || restaurant['longitude']
        };
    }

    async function saveBookmark(restaurant) {
        try {
            const payload = buildBookmarkPayload(restaurant);
            const response = await fetch('/api/v1/interactions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    entity_id: payload.restaurant_id,
                    entity_type: 'restaurant',
                    interaction_type: 'bookmark',
                    metadata: payload
                })
            });
            if (!response.ok) throw new Error('Bookmark failed');
            await loadBookmarks();
        } catch (error) {
            console.error('Error saving bookmark', error);
        }
    }

    async function rateRestaurant(restaurant) {
        const ratingInput = prompt('Rate this place (1-5 stars):', '4.5');
        if (!ratingInput) return;
        const ratingValue = parseFloat(ratingInput);
        if (Number.isNaN(ratingValue) || ratingValue < 1 || ratingValue > 5) {
            alert('Please enter a rating between 1 and 5.');
            return;
        }
        try {
            const payload = buildBookmarkPayload(restaurant);
            const response = await fetch('/api/v1/interactions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    entity_id: payload.restaurant_id,
                    entity_type: 'restaurant',
                    interaction_type: 'rating',
                    value: ratingValue,
                    metadata: payload
                })
            });
            if (!response.ok) throw new Error('Rating failed');
            alert('Thanks for rating!');
        } catch (error) {
            console.error('Rating error', error);
            alert('Could not save rating.');
        }
    }

    editProfileBtn?.addEventListener('click', openProfileModal);
    closeProfileModalBtn?.addEventListener('click', closeProfileModal);
    profileModal?.addEventListener('click', (e) => {
        if (e.target === profileModal) {
            closeProfileModal();
        }
    });
    applyProfileBtn?.addEventListener('click', applyProfileToForm);
    planItineraryBtn?.addEventListener('click', planItinerary);
    refreshBookmarksBtn?.addEventListener('click', loadBookmarks);
    refreshHistoryBtn?.addEventListener('click', loadHistory);

    profileForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const body = collectProfileFormData();
            const response = await fetch('/api/v1/preferences', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!response.ok) throw new Error('Failed to save profile');
            userProfile = await response.json();
            updateProfileSummary();
            closeProfileModal();
        } catch (error) {
            console.error('Profile save failed', error);
        }
    });

    profileCuisineSearch?.addEventListener('input', (event) => {
        renderProfileCuisineOptions(event.target.value);
    });

    profileFavoriteInput?.addEventListener('blur', () => {
        const typed = (profileFavoriteInput.value || '')
            .split(',')
            .map(v => v.trim())
            .filter(Boolean);
        profileCuisineSelections = new Set(typed);
        renderProfileCuisineOptions(profileCuisineSearch?.value || '');
    });

    quickChips.forEach(chip => {
        chip.addEventListener('click', async () => {
            quickChips.forEach(btn => btn.classList.remove('active'));
            chip.classList.add('active');
            const city = chip.dataset.city;
            if (city && cityInput) {
                cityInput.value = city;
                if (cityHiddenInput) {
                    cityHiddenInput.value = city;
                }
                if (typeof cuisineDropdown?.loadCuisines === 'function') {
                    await cuisineDropdown.loadCuisines(city);
                }
            }
            const cuisines = chip.dataset.cuisines
                ? chip.dataset.cuisines.split(',').map(v => v.trim()).filter(Boolean)
                : [];
            if (window.cuisineDropdown?.setSelectedCuisines && cuisines.length) {
                window.cuisineDropdown.setSelectedCuisines(cuisines);
            }
            if (cuisinesHiddenInput && cuisines.length) {
                cuisinesHiddenInput.value = cuisines.join(',');
            }
            if (priceRangeSelect && chip.dataset.priceRange) {
                priceRangeSelect.value = chip.dataset.priceRange;
            }
            if (moodFilter && chip.dataset.mood) {
                moodFilter.value = chip.dataset.mood;
            }
            if (occasionFilter && chip.dataset.occasion) {
                occasionFilter.value = chip.dataset.occasion;
            }
            if (chip.dataset.visitType) {
                document.querySelector(`input[name="visitType"][value="${chip.dataset.visitType}"]`)?.click();
            }
            if (chip.dataset.autoSubmit === 'true' && recoForm) {
                recoForm.requestSubmit();
            }
        });
    });

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
    const searchModeSelect = document.getElementById('searchMode');
    const searchModeHint = document.getElementById('search-mode-hint');
    const geminiOption = document.getElementById('gemini-option');
    const cityHiddenInput = document.getElementById('city-hidden');
    const cuisinesHiddenInput = document.getElementById('cuisines');
    const priceRangeSelect = document.getElementById('priceRange');
    const tableBookingSelect = document.getElementById('tableBooking');
    let currentRestaurants = [];
    let geminiAvailable = false;

    // Check Gemini API status on page load
    async function checkGeminiStatus() {
        try {
            const response = await fetch('/api/gemini/status');
            const status = await response.json();
            geminiAvailable = status.available;

            if (geminiAvailable) {
                if (geminiOption) {
                    geminiOption.disabled = false;
                    geminiOption.textContent = 'AI Search (Gemini) ✓';
                }
            } else {
                if (geminiOption) {
                    geminiOption.disabled = true;
                    geminiOption.textContent = 'AI Search (Gemini) - Not Available';
                }
            }
        } catch (error) {
            console.error('Error checking Gemini status:', error);
        }
    }

    // Update search mode hint
    if (searchModeSelect) {
        const updateSearchModeHint = () => {
            const mode = searchModeSelect.value;
            if (!searchModeHint) return;
            switch (mode) {
                case 'dataset':
                    searchModeHint.textContent = 'Using dataset for quick results';
                    break;
                case 'hybrid':
                    searchModeHint.textContent = 'Will try dataset first, then AI if needed';
                    break;
                case 'gemini':
                    searchModeHint.textContent = 'Using AI for expanded search capabilities';
                    break;
                default:
                    searchModeHint.textContent = '';
                    break;
            }
        };

        searchModeSelect.addEventListener('change', updateSearchModeHint);
        updateSearchModeHint();
    }

    // Check Gemini status on load
    checkGeminiStatus();

    // Dark Mode Toggle
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    if (darkModeToggle) {
        // Check for saved theme preference or default to light mode
        const currentTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', currentTheme);
        updateDarkModeIcon(currentTheme);

        darkModeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateDarkModeIcon(newTheme);
        });

        function updateDarkModeIcon(theme) {
            const icon = darkModeToggle.querySelector('i');
            if (icon) {
                icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
            }
        }
    }

    // Advanced Filters Toggle
    const filterToggle = document.getElementById('filter-toggle');
    const filterContent = document.getElementById('filter-content');
    const filterChevron = document.getElementById('filter-chevron');

    if (filterToggle && filterContent) {
        filterToggle.addEventListener('click', () => {
            filterContent.classList.toggle('active');
            if (filterChevron) {
                filterChevron.style.transform = filterContent.classList.contains('active')
                    ? 'rotate(180deg)'
                    : 'rotate(0deg)';
            }
        });
    }

    // Function to show/hide table booking based on visit/delivery
    function toggleTableBooking() {
        if (!tableBookingGroup) return;
        const selectedTypeInput = document.querySelector('input[name="visitType"]:checked');
        if (!selectedTypeInput) {
            tableBookingGroup.classList.add('hidden');
            return;
        }
        tableBookingGroup.classList.toggle('hidden', selectedTypeInput.value !== 'visit');
    }

    if (visitTypeRadios && visitTypeRadios.length) {
        visitTypeRadios.forEach(radio => {
            radio.addEventListener('change', toggleTableBooking);
        });
        toggleTableBooking();
    }

    // Sort results when sort option changes
    if (sortBySelect) {
        sortBySelect.addEventListener('change', () => {
            if (currentRestaurants.length > 0) {
                displayResults(currentRestaurants);
            }
        });
    }

    // Handle form submission
    if (recoForm) {
        recoForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!resultsList) return;

            // Ensure the city hidden input has a value even if the user typed manually
            const typedCity = cityInput?.value.trim() || '';
            if (cityHiddenInput && !cityHiddenInput.value.trim() && typedCity) {
                cityHiddenInput.value = typedCity;
            }

            // Validate required inputs before making the request
            if (!cityHiddenInput || !cityHiddenInput.value.trim()) {
                resultsList.innerHTML = `
                <p class="error-message">
                    <i class="fas fa-exclamation-circle"></i>
                    Please select a city from the suggestions or type a valid city name.
                </p>`;
                return;
            }

            if (cuisinesHiddenInput && !cuisinesHiddenInput.value.trim()) {
                resultsList.innerHTML = `
                <p class="error-message">
                    <i class="fas fa-exclamation-circle"></i>
                    Pick at least one cuisine to continue.
                </p>`;
                return;
            }

            // Show loading message
            resultsList.innerHTML = '<p class="loading"><i class="fas fa-spinner fa-spin"></i> Finding the best restaurants for you...</p>';
            viewAllMapBtn.classList.add('hidden');

            // Get form values
            const formData = new FormData(recoForm);
            const searchMode = formData.get('searchMode') || 'dataset';
            const dietarySelections = Array.from(document.querySelectorAll('input[name="dietary"]:checked')).map(cb => cb.value);
            const featureSelections = Array.from(document.querySelectorAll('input[name="features"]:checked')).map(cb => cb.value);
            const moodSelection = formData.get('mood') || (userProfile?.mood_tags?.[0] || '');
            const occasionSelection = formData.get('occasion') || (userProfile?.occasion_tags?.[0] || '');
            const userPreferences = {
                city: formData.get('city'),
                cuisines: formData.get('cuisines'),
                priceRange: formData.get('priceRange'),
                visitType: formData.get('visitType'),
                tableBooking: formData.get('tableBooking'),
                dietary: dietarySelections,
                features: featureSelections,
                ambiance: formData.get('ambiance'),
                minRating: formData.get('minRating'),
                mood: moodSelection,
                occasion: occasionSelection
            };

            try {
                // Add loading state to submit button
                const submitBtn = recoForm.querySelector('.submit-btn');
                const originalBtnText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner"></i> Searching...';
                submitBtn.classList.add('loading');

                // Determine which endpoint to use based on search mode
                let endpoint = '/api/recommend'; // Default to dataset
                if (searchMode === 'gemini') {
                    endpoint = '/api/gemini/search';
                } else if (searchMode === 'hybrid') {
                    endpoint = '/api/recommend/hybrid';
                }

                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(userPreferences)
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                }

                currentRestaurants = await response.json();
                // Save results to sessionStorage for persistence
                sessionStorage.setItem('lastSearchResults', JSON.stringify(currentRestaurants));
                sessionStorage.setItem('lastSearchParams', JSON.stringify(userPreferences));


                // Restore button state
                submitBtn.innerHTML = originalBtnText;
                submitBtn.classList.remove('loading');

                // Animate results appearance
                resultsList.style.opacity = '0';
                displayResults(currentRestaurants);
                viewAllMapBtn.classList.remove('hidden');
                loadHistory();

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
    }

    // Function to sort restaurants based on selected criteria
    function sortRestaurants(restaurants) {
        if (!sortBySelect) return [...restaurants];
        const sortBy = sortBySelect.value;
        return [...restaurants].sort((a, b) => {
            switch (sortBy) {
                case 'rating':
                    const ratingA = parseFloat(a['Aggregate rating'] || a['rating'] || 0);
                    const ratingB = parseFloat(b['Aggregate rating'] || b['rating'] || 0);
                    return ratingB - ratingA;
                case 'cost':
                    const costA = parseFloat(a['Average Cost for two'] || a['cost_for_two'] || 0);
                    const costB = parseFloat(b['Average Cost for two'] || b['cost_for_two'] || 0);
                    return costA - costB;
                case 'similarity':
                    const simA = parseFloat(a['Similarity Score'] || 0);
                    const simB = parseFloat(b['Similarity Score'] || 0);
                    return simB - simA;
                default:
                    return 0;
            }
        });
    }

    // Function to render restaurant cards
    function displayResults(restaurants) {
        if (!resultsList) return;
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

            // Handle both dataset and Gemini result formats
            const restaurantName = r['Restaurant Name'] || r['name'] || 'Unknown Restaurant';
            const rating = parseFloat(r['Aggregate rating'] || r['rating'] || 0).toFixed(1);
            const similarity = r['Similarity Score'] ? (parseFloat(r['Similarity Score']) * 100).toFixed(1) : null;
            const cuisines = r['Cuisines'] || (r['cuisines'] ? r['cuisines'].join(', ') : 'Not specified');
            const cost = r['Average Cost for two'] || r['cost_for_two'] || 'N/A';
            const delivery = r['Has Online delivery'] === 1 || (r['features'] && r['features'].includes('Online Delivery'));
            const booking = r['Has Table booking'] === 1 || (r['features'] && r['features'].includes('Table Booking'));
            const latitude = r['Latitude'] || r['latitude'];
            const longitude = r['Longitude'] || r['longitude'];
            const restaurantId = r['Restaurant ID'] || r['id'] || r['place_id'] || restaurantName.replace(/[^a-zA-Z0-9]/g, '_');
            const hasCoordinates = latitude !== undefined && latitude !== null && latitude !== '' &&
                longitude !== undefined && longitude !== null && longitude !== '';
            const directionsUrl = hasCoordinates
                ? `https://www.google.com/maps/dir/?api=1&destination=${latitude},${longitude}`
                : null;
            const description = r['description'] || '';

            card.innerHTML = `
                <div class="card-header">
                    <h3>${restaurantName}</h3>
                    <div class="rating">
                        <span class="rating-value">${rating}</span>
                        <i class="fas fa-star"></i>
                    </div>
                </div>
                <div class="card-body">
                    <p class="cuisines">
                        <i class="fas fa-utensils"></i> ${cuisines}
                    </p>
                    <p class="cost">
                        <i class="fas fa-rupee-sign"></i> ${cost} for two
                    </p>
                    ${description ? `<p class="description">${description}</p>` : ''}
                    <p class="features">
                        ${delivery ? '<span class="feature"><i class="fas fa-motorcycle"></i> Delivery</span>' : ''}
                        ${booking ? '<span class="feature"><i class="fas fa-chair"></i> Table Booking</span>' : ''}
                    </p>
                    ${similarity ? `
                    <div class="similarity">
                        <div class="similarity-bar" style="width: ${similarity}%"></div>
                        <span>${similarity}% match</span>
                    </div>` : ''}
                </div>
                <div class="card-actions">
                    ${restaurantId ? `
                    <button class="view-details-btn" onclick="window.location.href='/restaurant/${restaurantId}'">
                        <i class="fas fa-info-circle"></i> View Details
                    </button>
                    <button class="view-map-btn" onclick="window.location.href='/map?highlight=${restaurantId}'">
                        <i class="fas fa-map-marker-alt"></i> Map
                    </button>` : hasCoordinates ? `
                    <button class="view-map-btn" onclick="window.location.href='/map'">
                        <i class="fas fa-map-marker-alt"></i> View on Map
                    </button>` : ''}
                    ${directionsUrl ? `
                        <button class="directions-btn" onclick="window.open('${directionsUrl}', '_blank')">
                            <i class="fas fa-route"></i> Directions
                        </button>` : ''}
                </div>
            `;
            resultsList.appendChild(card);

            const personalizationActions = document.createElement('div');
            personalizationActions.className = 'personalization-actions';
            const bookmarkBtn = document.createElement('button');
            bookmarkBtn.className = 'bookmark-btn';
            bookmarkBtn.innerHTML = '<i class="fas fa-bookmark"></i> Save';
            bookmarkBtn.addEventListener('click', (event) => {
                event.stopPropagation();
                saveBookmark(r);
            });
            const rateBtn = document.createElement('button');
            rateBtn.className = 'rate-btn';
            rateBtn.innerHTML = '<i class="fas fa-star-half-alt"></i> Rate';
            rateBtn.addEventListener('click', (event) => {
                event.stopPropagation();
                rateRestaurant(r);
            });
            personalizationActions.appendChild(bookmarkBtn);
            personalizationActions.appendChild(rateBtn);
            card.appendChild(personalizationActions);

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
    if (viewAllMapBtn) {
        viewAllMapBtn.addEventListener('click', () => {
            window.location.href = '/map';
        });
    }
    // Initialize City Autocomplete
    const cityListContainer = document.getElementById('city-list');
    if (cityInput && cityListContainer) {
        const cityAutocomplete = new Autocomplete(cityInput, {
            listContainer: cityListContainer,
            hiddenInput: cityHiddenInput,
            dataUrl: '/api/cities',
            autoFetch: true,
            onSelect: (selectedCity) => {
                // When city is selected, load cuisines for that city
                cuisineDropdown.loadCuisines(selectedCity);
            }
        });
    }

    const scrollRevealElements = document.querySelectorAll('.reveal-on-scroll');
    if ('IntersectionObserver' in window && scrollRevealElements.length) {
        const revealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    revealObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.15 });
        scrollRevealElements.forEach(el => revealObserver.observe(el));
    } else {
        scrollRevealElements.forEach(el => el.classList.add('visible'));
    }

    loadProfileCuisines();
    loadProfile(true);
    loadBookmarks();
    loadHistory();
    
    // Restore last search results if available (at the end after everything is initialized)
    setTimeout(() => {
        const savedResults = sessionStorage.getItem('lastSearchResults');
        if (savedResults && resultsList) {
            try {
                const restoredRestaurants = JSON.parse(savedResults);
                if (restoredRestaurants.length > 0) {
                    currentRestaurants = restoredRestaurants;
                    displayResults(currentRestaurants);
                    if (viewAllMapBtn) viewAllMapBtn.classList.remove('hidden');
                    console.log('✅ Restored', currentRestaurants.length, 'search results');
                }
            } catch (e) {
                console.error('Error restoring results:', e);
            }
        }
    }, 100); // Small delay to ensure everything is ready
});

// Make restaurant cards clickable - navigate to details page
document.addEventListener('DOMContentLoaded', function() {
    const resultsList = document.getElementById('results-list');
    
    if (resultsList) {
        // Use event delegation for dynamically added cards
        resultsList.addEventListener('click', function(e) {
            const card = e.target.closest('.restaurant-card');
            
            // Only trigger if clicking the card itself, not buttons
            if (card && !e.target.closest('button')) {
                const viewDetailsBtn = card.querySelector('.view-details-btn');
                if (viewDetailsBtn) {
                    viewDetailsBtn.click();
                }
            }
        });
    }
});


// Helper function to view restaurant details (for Gemini results without IDs)
function viewRestaurantDetails(name, city, restaurantData) {
    // Store restaurant data in sessionStorage
    sessionStorage.setItem('tempRestaurantData', JSON.stringify(restaurantData));
    
    // Navigate to a special details page
    window.location.href = `/restaurant-details?name=${encodeURIComponent(name)}&city=${encodeURIComponent(city)}`;
}


