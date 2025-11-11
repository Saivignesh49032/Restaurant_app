document.addEventListener('DOMContentLoaded', () => {
    // Map Controls
    const centerMapBtn = document.getElementById('center-map');
    const clusterToggleBtn = document.getElementById('cluster-toggle');
    const infoPanel = document.getElementById('restaurant-info');
    const toggleInfoBtn = document.getElementById('toggle-info');
    let activeMarker = null;

    // Try to discover the Folium-created map instance if 'map' is not defined
    // Folium names maps like "map_xxxxx"; detect the first L.Map on window
    // eslint-disable-next-line no-undef
    let mapRef = typeof map !== 'undefined' ? map : null;
    if (!mapRef && typeof window !== 'undefined' && window.L) {
        for (const key of Object.keys(window)) {
            try {
                if (key.startsWith('map_') && window[key] instanceof window.L.Map) {
                    mapRef = window[key];
                    break;
                }
            } catch (e) {}
        }
    }
    if (!mapRef || !window.L) {
        // Leaflet or map not ready; safely exit
        return;
    }

    // Attempt to find a MarkerClusterGroup and collect marker layers
    const Lref = window.L;
    let markerCluster = null;
    let markers = [];

    mapRef.eachLayer(layer => {
        try {
            if (Lref.MarkerClusterGroup && layer instanceof Lref.MarkerClusterGroup) {
                markerCluster = layer;
            }
        } catch (e) {}
    });

    if (markerCluster && typeof markerCluster.getLayers === 'function') {
        markers = markerCluster.getLayers();
    } else {
        // Fallback: collect simple markers and circle markers directly on the map
        mapRef.eachLayer(layer => {
            if (layer instanceof Lref.Marker || layer instanceof Lref.CircleMarker) {
                markers.push(layer);
            }
        });
    }

    // Initialize map controls
    function initMapControls() {
        // Add custom control buttons to map
        const customControl = Lref.control({ position: 'topright' });
        customControl.onAdd = function () {
            const container = Lref.DomUtil.create('div', 'custom-map-controls');
            container.innerHTML = `
                <button class="map-ctrl-btn" id="locate-me" title="Find my location">
                    <i class="fas fa-location-arrow"></i>
                </button>
                <button class="map-ctrl-btn" id="zoom-to-fit" title="Zoom to fit all markers">
                    <i class="fas fa-expand"></i>
                </button>
            `;
            return container;
        };
        customControl.addTo(mapRef);

        // Locate user
        document.getElementById('locate-me').addEventListener('click', () => {
            mapRef.locate({ setView: true, maxZoom: 15 });
        });

        // Zoom to fit all markers
        document.getElementById('zoom-to-fit').addEventListener('click', () => {
            if (markers.length > 0) {
                const group = new Lref.featureGroup(markers);
                mapRef.fitBounds(group.getBounds().pad(0.1));
            } else if (mapRef.getBounds) {
                mapRef.fitBounds(mapRef.getBounds());
            }
        });
    }

    // Handle marker clicks
    function onMarkerClick(e) {
        const restaurant = e?.target?.restaurant;
        if (!restaurant) return;

        // Reset previous active marker
        if (activeMarker && activeMarker !== e.target) {
            try {
                // defaultIcon may not exist in Folium context; ignore if missing
                // eslint-disable-next-line no-undef
                if (typeof defaultIcon !== 'undefined') activeMarker.setIcon(defaultIcon);
            } catch (err) {}
        }

        // Set new active marker
        activeMarker = e.target;
        try {
            // eslint-disable-next-line no-undef
            if (typeof activeIcon !== 'undefined') activeMarker.setIcon(activeIcon);
        } catch (err) {}

        // Show restaurant info
        showRestaurantInfo(restaurant);
    }

    // Show restaurant details in info panel
    function showRestaurantInfo(restaurant) {
        infoPanel.innerHTML = `
            <div class="info-header">
                <h2>${restaurant['Restaurant Name']}</h2>
                <div class="rating">
                    <span class="rating-value">${parseFloat(restaurant['Aggregate rating']).toFixed(1)}</span>
                    <i class="fas fa-star"></i>
                </div>
            </div>
            <div class="info-content">
                <p class="cuisines">
                    <i class="fas fa-utensils"></i> ${restaurant['Cuisines']}
                </p>
                <p class="cost">
                    <i class="fas fa-rupee-sign"></i> ${restaurant['Average Cost for two']} for two
                </p>
                <div class="features">
                    ${restaurant['Has Online delivery'] ? 
                        '<span class="feature"><i class="fas fa-motorcycle"></i> Delivery Available</span>' : ''}
                    ${restaurant['Has Table booking'] ? 
                        '<span class="feature"><i class="fas fa-chair"></i> Table Booking</span>' : ''}
                </div>
                ${restaurant['Similarity Score'] ? `
                    <div class="similarity">
                        <div class="similarity-bar" style="width: ${(restaurant['Similarity Score'] * 100).toFixed(1)}%"></div>
                        <span>${(restaurant['Similarity Score'] * 100).toFixed(1)}% match</span>
                    </div>
                ` : ''}
            </div>
            <div class="info-actions">
                <button class="info-btn directions-btn" onclick="window.open('https://www.google.com/maps/dir/?api=1&destination=${restaurant['Latitude']},${restaurant['Longitude']}', '_blank')">
                    <i class="fas fa-directions"></i> Get Directions
                </button>
                <button class="info-btn details-btn" onclick="window.location.href='/?restaurant=${restaurant['Restaurant ID']}'">
                    <i class="fas fa-info-circle"></i> View Details
                </button>
            </div>
        `;
        infoPanel.classList.add('active');
    }

    // Location found handler
    function onLocationFound(e) {
        const radius = e.accuracy / 2;
        Lref.marker(e.latlng)
            .addTo(mapRef)
            .bindPopup(`You are within ${radius} meters from this point`)
            .openPopup();
        
        Lref.circle(e.latlng, radius).addTo(mapRef);
    }

    // Location error handler
    function onLocationError(e) {
        alert(e.message);
    }

    // Map event listeners
    mapRef.on('locationfound', onLocationFound);
    mapRef.on('locationerror', onLocationError);

    // Initialize map features
    initMapControls();

    // Add marker click handlers
    if (markers && markers.length > 0) {
        markers.forEach(marker => {
            marker.on('click', onMarkerClick);
        });
    }

    // Close info panel when clicking outside
    mapRef.on('click', () => {
        if (activeMarker) {
            try {
                // eslint-disable-next-line no-undef
                if (typeof defaultIcon !== 'undefined') activeMarker.setIcon(defaultIcon);
            } catch (err) {}
            activeMarker = null;
        }
        infoPanel.classList.remove('active');
    });

    // Handle cluster toggle
    clusterToggleBtn.addEventListener('click', function() {
        this.classList.toggle('active');
        const isActive = this.classList.contains('active');
        if (!markerCluster) return;
        if (isActive) {
            // Disable clustering: remove cluster group and add individual markers
            mapRef.removeLayer(markerCluster);
            markers.forEach(marker => {
                if (!mapRef.hasLayer(marker)) marker.addTo(mapRef);
            });
        } else {
            // Enable clustering: remove individual markers and add cluster group
            markers.forEach(marker => {
                if (mapRef.hasLayer(marker)) mapRef.removeLayer(marker);
            });
            markerCluster.addTo(mapRef);
        }
    });

    // Center map button
    centerMapBtn.addEventListener('click', () => {
        if (markers && markers.length > 0) {
            const group = new Lref.featureGroup(markers);
            mapRef.fitBounds(group.getBounds().pad(0.1));
        }
    });

    // Toggle info panel visibility
    if (toggleInfoBtn) {
        toggleInfoBtn.addEventListener('click', () => {
            infoPanel.classList.toggle('active');
        });
    }
});