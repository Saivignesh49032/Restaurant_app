// Restaurant Details Page JavaScript
document.addEventListener('DOMContentLoaded', () => {
    // Initialize map if coordinates are available
    const mapContainer = document.getElementById('restaurant-map');
    if (mapContainer) {
        // Get coordinates from data attributes or try to parse from page
        let lat = parseFloat(mapContainer.dataset.lat);
        let lon = parseFloat(mapContainer.dataset.lon);
        
        // If not in data attributes, try to get from restaurant data
        if (!lat || !lon || isNaN(lat) || isNaN(lon)) {
            // Try to get from a script tag with restaurant data
            const restaurantDataScript = document.getElementById('restaurant-data');
            if (restaurantDataScript) {
                try {
                    const data = JSON.parse(restaurantDataScript.textContent);
                    lat = parseFloat(data.latitude || data.Latitude);
                    lon = parseFloat(data.longitude || data.Longitude);
                } catch (e) {
                    console.error('Error parsing restaurant data:', e);
                }
            }
        }
        
        if (lat && lon && !isNaN(lat) && !isNaN(lon)) {
            const map = L.map('restaurant-map').setView([lat, lon], 15);
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);
            
            const restaurantName = document.querySelector('.restaurant-title-section h1')?.textContent || 'Restaurant';
            const address = document.querySelector('.contact-item span')?.textContent || '';
            
            const marker = L.marker([lat, lon]).addTo(map);
            marker.bindPopup(`
                <div class="map-popup">
                    <h4>${restaurantName}</h4>
                    <p>${address}</p>
                </div>
            `).openPopup();
        }
    }

    // Dark mode toggle
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
    }

    function updateDarkModeIcon(theme) {
        const icon = darkModeToggle.querySelector('i');
        if (icon) {
            icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }
});

