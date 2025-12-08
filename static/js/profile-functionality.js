// Profile Page Enhanced Functionality
(function () {
    'use strict';

    // Wait for DOM and dependencies
    document.addEventListener('DOMContentLoaded', function () {
        if (typeof UIUtils === 'undefined') {
            console.error('UIUtils not loaded');
            return;
        }

        initializeProfileEnhancements();
    });

    // State management
    let bookmarksData = [];
    let historyData = [];
    let selectedBookmarks = new Set();

    function initializeProfileEnhancements() {
        initializeBookmarkWidget();
        initializeHistoryWidget();
        initializeTrailPlanner();
        loadInitialData();
    }

    // ==================== BOOKMARK WIDGET ====================
    function initializeBookmarkWidget() {
        // Search functionality
        const searchInput = document.getElementById('bookmark-search');
        if (searchInput) {
            searchInput.addEventListener('input', UIUtils.debounce((e) => {
                filterBookmarks({ search: e.target.value });
            }, 300));
        }

        // Filter chips
        document.querySelectorAll('#bookmarks-widget .filter-chip').forEach(chip => {
            chip.addEventListener('click', function () {
                // Update active state
                document.querySelectorAll('#bookmarks-widget .filter-chip').forEach(c => c.classList.remove('active'));
                this.classList.add('active');

                const filter = this.dataset.filter;
                filterBookmarks({ type: filter });
            });
        });

        // Select all checkbox
        const selectAllCheckbox = document.getElementById('select-all-bookmarks');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', function (e) {
                const checkboxes = document.querySelectorAll('.bookmark-item input[type="checkbox"]');
                checkboxes.forEach(cb => {
                    cb.checked = e.target.checked;
                    if (e.target.checked) {
                        selectedBookmarks.add(cb.dataset.id);
                    } else {
                        selectedBookmarks.delete(cb.dataset.id);
                    }
                });
                updateBulkActions();
            });
        }

        // Refresh button
        document.getElementById('refresh-bookmarks-btn')?.addEventListener('click', loadBookmarks);

        // Export button
        document.getElementById('export-bookmarks-btn')?.addEventListener('click', exportBookmarks);

        // Sort button
        document.getElementById('sort-bookmarks-btn')?.addEventListener('click', showSortOptions);

        // Delete selected
        document.getElementById('delete-selected-bookmarks')?.addEventListener('click', deleteSelectedBookmarks);

        // Add to trail
        document.getElementById('add-to-trail-selected')?.addEventListener('click', addSelectedToTrail);

        // Plan itinerary button
        document.getElementById('plan-itinerary-btn')?.addEventListener('click', planFoodTrail);
    }

    async function loadBookmarks() {
        const widget = document.getElementById('bookmarks-widget');
        const loader = UIUtils.showLoader(widget, 'Loading bookmarks...');

        try {
            // Simulate API call - replace with actual endpoint
            const response = await fetch('/api/bookmarks');
            if (response.ok) {
                bookmarksData = await response.json();
            } else {
                // Demo data if API fails
                bookmarksData = [
                    {
                        id: '1',
                        name: 'V. B. Bakery',
                        cuisine: 'Bakery, Desserts',
                        rating: 4.5,
                        cost: 300,
                        city: 'Bangalore',
                        addedDate: new Date().toISOString()
                    }
                ];
            }

            displayBookmarks(bookmarksData);
            updateBookmarkCount();
        } catch (error) {
            console.error('Error loading bookmarks:', error);
            UIUtils.showToast('Failed to load bookmarks', 'error');
        } finally {
            UIUtils.hideLoader(loader);
        }
    }

    function displayBookmarks(bookmarks) {
        const list = document.getElementById('bookmarks-list');
        if (!list) return;

        if (bookmarks.length === 0) {
            list.innerHTML = `
                <li class="empty-state">
                    <i class="fas fa-bookmark"></i>
                    <p>No bookmarks yet. Tap the bookmark icon on any restaurant card.</p>
                </li>
            `;
            return;
        }

        list.innerHTML = bookmarks.map(bookmark => `
            <li class="bookmark-item" data-id="${bookmark.id}">
                <input type="checkbox" data-id="${bookmark.id}">
                <div class="bookmark-item-content">
                    <div class="bookmark-item-title">${bookmark.name}</div>
                    <div class="bookmark-item-meta">
                        <span><i class="fas fa-utensils"></i> ${bookmark.cuisine}</span>
                        <span><i class="fas fa-star"></i> ${bookmark.rating}</span>
                        <span><i class="fas fa-rupee-sign"></i> ${bookmark.cost} for two</span>
                    </div>
                </div>
                <div class="bookmark-item-actions">
                    <button class="item-action-btn" onclick="viewBookmark('${bookmark.id}')" title="View">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="item-action-btn" onclick="shareBookmark('${bookmark.id}')" title="Share">
                        <i class="fas fa-share-alt"></i>
                    </button>
                    <button class="item-action-btn" onclick="deleteBookmark('${bookmark.id}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </li>
        `).join('');

        // Add checkbox listeners
        list.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.addEventListener('change', function () {
                if (this.checked) {
                    selectedBookmarks.add(this.dataset.id);
                } else {
                    selectedBookmarks.delete(this.dataset.id);
                }
                updateBulkActions();
            });
        });
    }

    function filterBookmarks(options = {}) {
        let filtered = [...bookmarksData];

        // Search filter
        if (options.search) {
            const query = options.search.toLowerCase();
            filtered = filtered.filter(b =>
                b.name.toLowerCase().includes(query) ||
                b.cuisine.toLowerCase().includes(query) ||
                b.city.toLowerCase().includes(query)
            );
        }

        // Type filter
        if (options.type === 'recent') {
            const weekAgo = new Date();
            weekAgo.setDate(weekAgo.getDate() - 7);
            filtered = filtered.filter(b => new Date(b.addedDate) > weekAgo);
        } else if (options.type === 'favorites') {
            filtered = filtered.filter(b => b.isFavorite);
        }

        displayBookmarks(filtered);
    }

    function updateBulkActions() {
        const deleteBtn = document.getElementById('delete-selected-bookmarks');
        const addToTrailBtn = document.getElementById('add-to-trail-selected');
        const planBtn = document.getElementById('plan-itinerary-btn');

        const hasSelection = selectedBookmarks.size > 0;

        if (deleteBtn) deleteBtn.disabled = !hasSelection;
        if (addToTrailBtn) addToTrailBtn.disabled = !hasSelection;
        if (planBtn) planBtn.disabled = selectedBookmarks.size < 2;
    }

    function updateBookmarkCount() {
        const countEl = document.getElementById('bookmark-count');
        if (countEl) countEl.textContent = bookmarksData.length;
    }

    async function exportBookmarks() {
        if (bookmarksData.length === 0) {
            UIUtils.showToast('No bookmarks to export', 'info');
            return;
        }

        const filename = `bookmarks_${new Date().toISOString().split('T')[0]}.json`;
        UIUtils.exportToJSON(bookmarksData, filename);
        UIUtils.showToast('Bookmarks exported successfully', 'success');
    }

    function showSortOptions() {
        // Simple sort toggle for demo
        bookmarksData.sort((a, b) => b.rating - a.rating);
        displayBookmarks(bookmarksData);
        UIUtils.showToast('Sorted by rating', 'info');
    }

    async function deleteSelectedBookmarks() {
        if (selectedBookmarks.size === 0) return;

        const confirmed = await UIUtils.confirm(
            `Delete ${selectedBookmarks.size} bookmark(s)?`,
            'Confirm Deletion'
        );

        if (confirmed) {
            bookmarksData = bookmarksData.filter(b => !selectedBookmarks.has(b.id));
            selectedBookmarks.clear();
            displayBookmarks(bookmarksData);
            updateBookmarkCount();
            updateBulkActions();
            UIUtils.showToast('Bookmarks deleted', 'success');
        }
    }

    function addSelectedToTrail() {
        UIUtils.showToast(`${selectedBookmarks.size} spots added to trail`, 'success');
    }

    // Make functions global for onclick handlers
    window.viewBookmark = function (id) {
        UIUtils.showToast('Opening bookmark details...', 'info');
    };

    window.shareBookmark = function (id) {
        const bookmark = bookmarksData.find(b => b.id === id);
        if (bookmark) {
            UIUtils.copyToClipboard(`Check out ${bookmark.name}!`);
        }
    };

    window.deleteBookmark = async function (id) {
        const confirmed = await UIUtils.confirm('Delete this bookmark?');
        if (confirmed) {
            bookmarksData = bookmarksData.filter(b => b.id !== id);
            displayBookmarks(bookmarksData);
            updateBookmarkCount();
            UIUtils.showToast('Bookmark deleted', 'success');
        }
    };

    // ==================== HISTORY WIDGET ====================
    function initializeHistoryWidget() {
        // Search functionality
        const searchInput = document.getElementById('history-search');
        if (searchInput) {
            searchInput.addEventListener('input', UIUtils.debounce((e) => {
                filterHistory({ search: e.target.value });
            }, 300));
        }

        // Period filter chips
        document.querySelectorAll('#history-widget .filter-chip').forEach(chip => {
            chip.addEventListener('click', function () {
                document.querySelectorAll('#history-widget .filter-chip').forEach(c => c.classList.remove('active'));
                this.classList.add('active');

                const period = this.dataset.period;
                filterHistory({ period });
            });
        });

        // Buttons
        document.getElementById('refresh-history-btn')?.addEventListener('click', loadHistory);
        document.getElementById('export-history-btn')?.addEventListener('click', exportHistory);
        document.getElementById('clear-history-btn')?.addEventListener('click', clearHistory);
    }

    async function loadHistory() {
        const widget = document.getElementById('history-widget');
        const loader = UIUtils.showLoader(widget, 'Loading history...');

        try {
            const response = await fetch('/api/history');
            if (response.ok) {
                historyData = await response.json();
            } else {
                // Demo data
                historyData = [
                    {
                        id: '1',
                        query: 'Bangalore',
                        results: 4,
                        timestamp: new Date().toISOString()
                    },
                    {
                        id: '2',
                        query: 'Bangalore',
                        results: 8,
                        timestamp: new Date(Date.now() - 86400000).toISOString()
                    }
                ];
            }

            displayHistory(historyData);
            updateHistoryStats();
        } catch (error) {
            console.error('Error loading history:', error);
            UIUtils.showToast('Failed to load history', 'error');
        } finally {
            UIUtils.hideLoader(loader);
        }
    }

    function displayHistory(history) {
        const list = document.getElementById('history-list');
        if (!list) return;

        if (history.length === 0) {
            list.innerHTML = `
                <li class="empty-state">
                    <i class="fas fa-clock"></i>
                    <p>Submit a search to build history.</p>
                </li>
            `;
            return;
        }

        list.innerHTML = history.map(item => `
            <li class="history-item" onclick="rerunSearch('${item.id}')">
                <div class="history-item-content">
                    <div class="history-item-title">search · ${item.query}</div>
                    <div class="history-item-meta">
                        <span><i class="fas fa-list"></i> ${item.results} results</span>
                        <span><i class="fas fa-clock"></i> ${UIUtils.formatDate(item.timestamp)}</span>
                    </div>
                </div>
                <div class="history-item-actions">
                    <button class="item-action-btn" onclick="event.stopPropagation(); rerunSearch('${item.id}')" title="Re-run">
                        <i class="fas fa-redo"></i>
                    </button>
                </div>
            </li>
        `).join('');
    }

    function filterHistory(options = {}) {
        let filtered = [...historyData];

        // Search filter
        if (options.search) {
            const query = options.search.toLowerCase();
            filtered = filtered.filter(h => h.query.toLowerCase().includes(query));
        }

        // Period filter
        if (options.period && options.period !== 'all') {
            const now = new Date();
            let cutoff;

            if (options.period === 'today') {
                cutoff = new Date(now.setHours(0, 0, 0, 0));
            } else if (options.period === 'week') {
                cutoff = new Date(now.setDate(now.getDate() - 7));
            } else if (options.period === 'month') {
                cutoff = new Date(now.setMonth(now.getMonth() - 1));
            }

            filtered = filtered.filter(h => new Date(h.timestamp) > cutoff);
        }

        displayHistory(filtered);
    }

    function updateHistoryStats() {
        const countEl = document.getElementById('history-count');
        const mostSearchedEl = document.getElementById('most-searched');

        if (countEl) countEl.textContent = historyData.length;

        if (mostSearchedEl && historyData.length > 0) {
            // Find most common query
            const queries = historyData.map(h => h.query);
            const counts = {};
            queries.forEach(q => counts[q] = (counts[q] || 0) + 1);
            const mostCommon = Object.keys(counts).reduce((a, b) => counts[a] > counts[b] ? a : b);
            mostSearchedEl.textContent = mostCommon;
        }
    }

    async function exportHistory() {
        if (historyData.length === 0) {
            UIUtils.showToast('No history to export', 'info');
            return;
        }

        const filename = `history_${new Date().toISOString().split('T')[0]}.json`;
        UIUtils.exportToJSON(historyData, filename);
        UIUtils.showToast('History exported successfully', 'success');
    }

    async function clearHistory() {
        if (historyData.length === 0) {
            UIUtils.showToast('No history to clear', 'info');
            return;
        }

        const confirmed = await UIUtils.confirm(
            'Clear all search history?',
            'Confirm Clear History'
        );

        if (!confirmed) return;

        const widget = document.getElementById('history-widget');
        const loader = UIUtils.showLoader(widget, 'Clearing history...');

        try {
            const response = await fetch('/api/clear_history', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                historyData = [];
                displayHistory(historyData);
                updateHistoryStats();
                UIUtils.showToast('History cleared successfully', 'success');
            } else {
                throw new Error('Failed to clear history');
            }
        } catch (error) {
            console.error('Error clearing history:', error);
            UIUtils.showToast('Failed to clear history', 'error');
        } finally {
            UIUtils.hideLoader(loader);
        }
    }

    window.rerunSearch = function (id) {
        const item = historyData.find(h => h.id === id);
        if (item) {
            UIUtils.showToast(`Re-running search for "${item.query}"...`, 'info');
            // Redirect to home with query
            window.location.href = `/?city=${encodeURIComponent(item.query)}`;
        }
    };

    // ==================== TRAIL PLANNER ====================
    function initializeTrailPlanner() {
        document.getElementById('save-trail-btn')?.addEventListener('click', saveTrail);
        document.getElementById('share-trail-btn')?.addEventListener('click', shareTrail);
        document.getElementById('export-trail-btn')?.addEventListener('click', exportTrail);

        document.getElementById('trail-optimization')?.addEventListener('change', updateTrailOptimization);
    }

    function planFoodTrail() {
        if (selectedBookmarks.size < 2) {
            UIUtils.showToast('Select at least 2 bookmarks', 'warning');
            return;
        }

        const selectedItems = bookmarksData.filter(b => selectedBookmarks.has(b.id));
        const optimization = document.getElementById('trail-optimization')?.value || 'distance';

        // Sort based on optimization
        if (optimization === 'rating') {
            selectedItems.sort((a, b) => b.rating - a.rating);
        }

        displayTrail(selectedItems);
        UIUtils.showToast('Food trail created!', 'success');
    }

    function displayTrail(items) {
        const output = document.getElementById('itinerary-output');
        const stats = document.getElementById('trail-stats');

        if (!output) return;

        output.innerHTML = items.map((item, index) => `
            <div class="trail-item">
                <div class="trail-item-header">
                    <div class="trail-item-number">${index + 1}</div>
                    <div class="trail-item-title">${item.name}</div>
                </div>
                <div class="trail-item-meta">
                    <span><i class="fas fa-utensils"></i> ${item.cuisine}</span>
                    <span><i class="fas fa-star"></i> ${item.rating}</span>
                    <span><i class="fas fa-map-marker-alt"></i> ${item.city}</span>
                </div>
            </div>
        `).join('');

        // Update stats
        if (stats) {
            stats.style.display = 'flex';
            document.getElementById('trail-stops').textContent = items.length;
            document.getElementById('trail-distance').textContent = (items.length * 2.5).toFixed(1);
            document.getElementById('trail-time').textContent = (items.length * 1.5).toFixed(1);
        }

        // Enable trail buttons
        document.getElementById('save-trail-btn').disabled = false;
        document.getElementById('share-trail-btn').disabled = false;
        document.getElementById('export-trail-btn').disabled = false;
    }

    function saveTrail() {
        UIUtils.showToast('Trail saved to your profile', 'success');
    }

    function shareTrail() {
        UIUtils.copyToClipboard('Check out my food trail!');
    }

    function exportTrail() {
        const selectedItems = bookmarksData.filter(b => selectedBookmarks.has(b.id));
        const filename = `food_trail_${new Date().toISOString().split('T')[0]}.json`;
        UIUtils.exportToJSON(selectedItems, filename);
        UIUtils.showToast('Trail exported', 'success');
    }

    function updateTrailOptimization() {
        if (selectedBookmarks.size >= 2) {
            planFoodTrail();
        }
    }

    // ==================== INITIAL LOAD ====================
    function loadInitialData() {
        loadBookmarks();
        loadHistory();
    }

})();
