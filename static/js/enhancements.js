// Enhanced Bookmark and History Management
// This file extends the existing main.js functionality with UI enhancements

(function () {
    'use strict';

    // Wait for DOM and UIUtils to be ready
    document.addEventListener('DOMContentLoaded', function () {
        if (typeof UIUtils === 'undefined') {
            console.error('UIUtils not loaded');
            return;
        }

        initializeEnhancements();
    });

    function initializeEnhancements() {
        enhanceBookmarkManagement();
        enhanceHistoryManagement();
        enhanceFormValidation();
        enhanceRestaurantCards();
        addExportFunctionality();
        addClearAllFilters();
    }

    // Enhanced Bookmark Management
    function enhanceBookmarkManagement() {
        const bookmarksList = document.getElementById('bookmarks-list');
        const bookmarksWidget = document.getElementById('bookmarks-widget');

        if (!bookmarksWidget) return;

        // Add search bar for bookmarks
        const searchBar = createSearchBar('Search bookmarks...', (query) => {
            filterBookmarks(query);
        });

        const widgetHeader = bookmarksWidget.querySelector('.widget-header');
        if (widgetHeader) {
            widgetHeader.insertAdjacentElement('afterend', searchBar);
        }

        // Add export button
        const exportBtn = document.createElement('button');
        exportBtn.className = 'btn-icon';
        exportBtn.innerHTML = '<i class="fas fa-download"></i>';
        exportBtn.title = 'Export Bookmarks';
        exportBtn.onclick = exportBookmarks;
        widgetHeader.appendChild(exportBtn);

        // Add select all checkbox
        const selectAllContainer = document.createElement('div');
        selectAllContainer.className = 'bulk-actions';
        selectAllContainer.innerHTML = `
            <label class="checkbox-label">
                <input type="checkbox" id="select-all-bookmarks">
                <span>Select All</span>
            </label>
            <button class="btn-icon" id="delete-selected" title="Delete Selected" disabled>
                <i class="fas fa-trash"></i>
            </button>
        `;
        searchBar.insertAdjacentElement('afterend', selectAllContainer);

        // Handle select all
        document.getElementById('select-all-bookmarks')?.addEventListener('change', function (e) {
            const checkboxes = document.querySelectorAll('.bookmark-item input[type="checkbox"]');
            checkboxes.forEach(cb => cb.checked = e.target.checked);
            updateBulkActions();
        });

        // Handle delete selected
        document.getElementById('delete-selected')?.addEventListener('click', async function () {
            const selected = Array.from(document.querySelectorAll('.bookmark-item input[type="checkbox"]:checked'));
            if (selected.length === 0) return;

            const confirmed = await UIUtils.confirm(
                `Delete ${selected.length} bookmark${selected.length > 1 ? 's' : ''}?`,
                'Confirm Deletion'
            );

            if (confirmed) {
                const loader = UIUtils.showLoader(bookmarksWidget, 'Deleting...');
                try {
                    await deleteSelectedBookmarks(selected);
                    UIUtils.showToast(`${selected.length} bookmark(s) deleted`, 'success');
                } catch (error) {
                    UIUtils.showToast('Failed to delete bookmarks', 'error');
                } finally {
                    UIUtils.hideLoader(loader);
                }
            }
        });
    }

    // Enhanced History Management
    function enhanceHistoryManagement() {
        const historyWidget = document.getElementById('history-widget');
        if (!historyWidget) return;

        const widgetHeader = historyWidget.querySelector('.widget-header');

        // Add search bar
        const searchBar = createSearchBar('Search history...', (query) => {
            filterHistory(query);
        });
        widgetHeader.insertAdjacentElement('afterend', searchBar);

        // Add clear history button
        const clearBtn = document.createElement('button');
        clearBtn.className = 'btn-icon';
        clearBtn.innerHTML = '<i class="fas fa-trash-alt"></i>';
        clearBtn.title = 'Clear History';
        clearBtn.onclick = clearHistory;
        widgetHeader.appendChild(clearBtn);

        // Add export button
        const exportBtn = document.createElement('button');
        exportBtn.className = 'btn-icon';
        exportBtn.innerHTML = '<i class="fas fa-download"></i>';
        exportBtn.title = 'Export History';
        exportBtn.onclick = exportHistory;
        widgetHeader.appendChild(exportBtn);
    }

    // Enhanced Form Validation
    function enhanceFormValidation() {
        const form = document.getElementById('reco-form');
        if (!form) return;

        const cityInput = document.getElementById('city');
        const cuisinesInput = document.getElementById('cuisines');

        if (cityInput) {
            cityInput.addEventListener('blur', () => {
                UIUtils.validateField(cityInput, {
                    required: true,
                    minLength: 2
                });
            });
        }

        if (cuisinesInput) {
            form.addEventListener('submit', (e) => {
                if (!cuisinesInput.value.trim()) {
                    e.preventDefault();
                    UIUtils.showToast('Please select at least one cuisine', 'warning');
                    return false;
                }
            });
        }
    }

    // Enhanced Restaurant Cards
    function enhanceRestaurantCards() {
        // This will be called after results are displayed
        window.enhanceCards = function () {
            const cards = document.querySelectorAll('.restaurant-card');
            cards.forEach(card => {
                if (card.classList.contains('enhanced')) return;
                card.classList.add('card-enhanced', 'enhanced');

                // Add quick actions
                const quickActions = document.createElement('div');
                quickActions.className = 'quick-actions';
                quickActions.innerHTML = `
                    <button class="quick-action-btn bookmark-quick" title="Bookmark">
                        <i class="fas fa-bookmark"></i>
                    </button>
                    <button class="quick-action-btn share-quick" title="Share">
                        <i class="fas fa-share-alt"></i>
                    </button>
                    <button class="quick-action-btn directions-quick" title="Directions">
                        <i class="fas fa-directions"></i>
                    </button>
                `;

                card.querySelector('.card-header')?.appendChild(quickActions);

                // Handle quick actions
                quickActions.querySelector('.bookmark-quick')?.addEventListener('click', (e) => {
                    e.stopPropagation();
                    toggleBookmark(card);
                });

                quickActions.querySelector('.share-quick')?.addEventListener('click', (e) => {
                    e.stopPropagation();
                    shareRestaurant(card);
                });

                quickActions.querySelector('.directions-quick')?.addEventListener('click', (e) => {
                    e.stopPropagation();
                    getDirections(card);
                });
            });
        };
    }

    // Helper Functions
    function createSearchBar(placeholder, onSearch) {
        const container = document.createElement('div');
        container.className = 'search-bar';
        container.innerHTML = `
            <input type="text" placeholder="${placeholder}" class="search-input">
            <i class="fas fa-search"></i>
        `;

        const input = container.querySelector('input');
        input.addEventListener('input', UIUtils.debounce((e) => {
            onSearch(e.target.value);
        }, 300));

        return container;
    }

    function filterBookmarks(query) {
        const items = document.querySelectorAll('.bookmark-item');
        const lowerQuery = query.toLowerCase();

        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            item.style.display = text.includes(lowerQuery) ? '' : 'none';
        });
    }

    function filterHistory(query) {
        const items = document.querySelectorAll('.history-list li');
        const lowerQuery = query.toLowerCase();

        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            item.style.display = text.includes(lowerQuery) ? '' : 'none';
        });
    }

    async function exportBookmarks() {
        try {
            const response = await fetch('/api/bookmarks');
            const bookmarks = await response.json();

            if (bookmarks.length === 0) {
                UIUtils.showToast('No bookmarks to export', 'info');
                return;
            }

            const filename = `bookmarks_${new Date().toISOString().split('T')[0]}.json`;
            UIUtils.exportToJSON(bookmarks, filename);
            UIUtils.showToast('Bookmarks exported successfully', 'success');
        } catch (error) {
            UIUtils.showToast('Failed to export bookmarks', 'error');
        }
    }

    async function exportHistory() {
        try {
            const response = await fetch('/api/history');
            const history = await response.json();

            if (history.length === 0) {
                UIUtils.showToast('No history to export', 'info');
                return;
            }

            const filename = `history_${new Date().toISOString().split('T')[0]}.json`;
            UIUtils.exportToJSON(history, filename);
            UIUtils.showToast('History exported successfully', 'success');
        } catch (error) {
            UIUtils.showToast('Failed to export history', 'error');
        }
    }

    async function clearHistory() {
        const confirmed = await UIUtils.confirm(
            'This will delete all your search history. This action cannot be undone.',
            'Clear History'
        );

        if (confirmed) {
            try {
                const response = await fetch('/api/history', { method: 'DELETE' });
                if (response.ok) {
                    UIUtils.showToast('History cleared successfully', 'success');
                    // Reload history
                    if (typeof loadHistory === 'function') {
                        loadHistory();
                    }
                } else {
                    throw new Error('Failed to clear history');
                }
            } catch (error) {
                UIUtils.showToast('Failed to clear history', 'error');
            }
        }
    }

    async function deleteSelectedBookmarks(checkboxes) {
        const ids = checkboxes.map(cb => cb.dataset.bookmarkId);
        const promises = ids.map(id =>
            fetch(`/api/bookmark/${id}`, { method: 'DELETE' })
        );

        await Promise.all(promises);

        // Reload bookmarks
        if (typeof loadBookmarks === 'function') {
            loadBookmarks();
        }
    }

    function updateBulkActions() {
        const selected = document.querySelectorAll('.bookmark-item input[type="checkbox"]:checked');
        const deleteBtn = document.getElementById('delete-selected');
        if (deleteBtn) {
            deleteBtn.disabled = selected.length === 0;
        }
    }

    function toggleBookmark(card) {
        const btn = card.querySelector('.bookmark-quick');
        const isBookmarked = btn.classList.contains('active');

        if (isBookmarked) {
            btn.classList.remove('active');
            UIUtils.showToast('Bookmark removed', 'info');
        } else {
            btn.classList.add('active');
            UIUtils.showToast('Bookmark added', 'success');
        }

        // TODO: Implement actual bookmark API call
    }

    function shareRestaurant(card) {
        const name = card.querySelector('h3')?.textContent || 'Restaurant';
        const url = window.location.href;

        if (navigator.share) {
            navigator.share({
                title: name,
                text: `Check out ${name}!`,
                url: url
            }).catch(() => { });
        } else {
            UIUtils.copyToClipboard(url);
        }
    }

    function getDirections(card) {
        // Extract coordinates from card data
        const lat = card.dataset.lat;
        const lng = card.dataset.lng;

        if (lat && lng) {
            const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
            window.open(url, '_blank');
        } else {
            UIUtils.showToast('Location not available', 'warning');
        }
    }

    function addExportFunctionality() {
        // Add export button to results section
        const resultsActions = document.querySelector('.results-actions');
        if (resultsActions) {
            const exportBtn = document.createElement('button');
            exportBtn.className = 'action-btn';
            exportBtn.innerHTML = '<i class="fas fa-download"></i> Export Results';
            exportBtn.onclick = exportResults;
            resultsActions.appendChild(exportBtn);
        }
    }

    async function exportResults() {
        if (typeof currentRestaurants === 'undefined' || !currentRestaurants.length) {
            UIUtils.showToast('No results to export', 'info');
            return;
        }

        const filename = `restaurants_${new Date().toISOString().split('T')[0]}.csv`;
        const data = currentRestaurants.map(r => ({
            Name: r['Restaurant Name'] || r.name,
            Cuisines: r.Cuisines || r.cuisines,
            Rating: r['Aggregate rating'] || r.rating,
            Cost: r['Average Cost for two'] || r.cost,
            City: r.City || r.city
        }));

        UIUtils.exportToCSV(data, filename);
        UIUtils.showToast('Results exported successfully', 'success');
    }

    function addClearAllFilters() {
        const filterContent = document.getElementById('filter-content');
        if (!filterContent) return;

        const clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.className = 'btn-secondary';
        clearBtn.innerHTML = '<i class="fas fa-times-circle"></i> Clear All Filters';
        clearBtn.style.marginTop = '1rem';
        clearBtn.onclick = clearAllFilters;

        filterContent.appendChild(clearBtn);
    }

    function clearAllFilters() {
        // Reset all filter inputs
        document.querySelectorAll('#filter-content input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });

        document.querySelectorAll('#filter-content select').forEach(select => {
            select.selectedIndex = 0;
        });

        UIUtils.showToast('Filters cleared', 'info');
    }

    // Override the original displayResults to add enhancements
    const originalDisplayResults = window.displayResults;
    if (originalDisplayResults) {
        window.displayResults = function (restaurants) {
            originalDisplayResults(restaurants);
            // Enhance cards after they're displayed
            if (window.enhanceCards) {
                window.enhanceCards();
            }
        };
    }

})();
