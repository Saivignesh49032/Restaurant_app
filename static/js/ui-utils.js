// UI Utilities for Enhanced UX
class UIUtils {
    // Toast Notifications
    static showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <i class="fas fa-${this.getToastIcon(type)}"></i>
            <span>${message}</span>
        `;

        document.body.appendChild(toast);

        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);

        // Auto remove
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    static getToastIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    // Loading States
    static showLoader(element, text = 'Loading...') {
        const loader = document.createElement('div');
        loader.className = 'loader-overlay';
        loader.innerHTML = `
            <div class="loader-content">
                <div class="spinner"></div>
                <p>${text}</p>
            </div>
        `;
        element.style.position = 'relative';
        element.appendChild(loader);
        return loader;
    }

    static hideLoader(loader) {
        if (loader && loader.parentElement) {
            loader.remove();
        }
    }

    // Skeleton Loaders
    static createSkeleton(type = 'card', count = 3) {
        const container = document.createElement('div');
        container.className = 'skeleton-container';

        for (let i = 0; i < count; i++) {
            const skeleton = document.createElement('div');
            skeleton.className = `skeleton skeleton-${type}`;
            skeleton.innerHTML = this.getSkeletonTemplate(type);
            container.appendChild(skeleton);
        }

        return container;
    }

    static getSkeletonTemplate(type) {
        if (type === 'card') {
            return `
                <div class="skeleton-header"></div>
                <div class="skeleton-body">
                    <div class="skeleton-line"></div>
                    <div class="skeleton-line short"></div>
                    <div class="skeleton-line"></div>
                </div>
            `;
        }
        return '<div class="skeleton-line"></div>';
    }

    // Confirmation Modals
    static async confirm(message, title = 'Confirm Action') {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay confirm-modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3><i class="fas fa-question-circle"></i> ${title}</h3>
                    <p>${message}</p>
                    <div class="modal-actions">
                        <button class="btn-cancel">Cancel</button>
                        <button class="btn-confirm">Confirm</button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
            setTimeout(() => modal.classList.add('show'), 10);

            modal.querySelector('.btn-cancel').onclick = () => {
                modal.classList.remove('show');
                setTimeout(() => modal.remove(), 300);
                resolve(false);
            };

            modal.querySelector('.btn-confirm').onclick = () => {
                modal.classList.remove('show');
                setTimeout(() => modal.remove(), 300);
                resolve(true);
            };
        });
    }

    // Form Validation
    static validateField(input, rules) {
        const value = input.value.trim();
        const errors = [];

        if (rules.required && !value) {
            errors.push('This field is required');
        }

        if (rules.minLength && value.length < rules.minLength) {
            errors.push(`Minimum ${rules.minLength} characters required`);
        }

        if (rules.pattern && !rules.pattern.test(value)) {
            errors.push(rules.patternMessage || 'Invalid format');
        }

        this.showFieldError(input, errors[0]);
        return errors.length === 0;
    }

    static showFieldError(input, message) {
        // Remove existing error
        const existingError = input.parentElement.querySelector('.field-error');
        if (existingError) existingError.remove();

        input.classList.toggle('error', !!message);

        if (message) {
            const error = document.createElement('span');
            error.className = 'field-error';
            error.textContent = message;
            input.parentElement.appendChild(error);
        }
    }

    // Debounce utility
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Local Storage helpers
    static saveToStorage(key, data) {
        try {
            localStorage.setItem(key, JSON.stringify(data));
            return true;
        } catch (e) {
            console.error('Storage error:', e);
            return false;
        }
    }

    static getFromStorage(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error('Storage error:', e);
            return defaultValue;
        }
    }

    // Export data
    static exportToJSON(data, filename) {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        this.downloadBlob(blob, filename);
    }

    static exportToCSV(data, filename) {
        if (!data.length) return;

        const headers = Object.keys(data[0]);
        const csv = [
            headers.join(','),
            ...data.map(row => headers.map(h => `"${row[h] || ''}"`).join(','))
        ].join('\n');

        const blob = new Blob([csv], { type: 'text/csv' });
        this.downloadBlob(blob, filename);
    }

    static downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // Animate elements
    static animateIn(element, animation = 'fadeIn') {
        element.style.opacity = '0';
        element.style.animation = `${animation} 0.3s ease forwards`;
    }

    // Copy to clipboard
    static async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showToast('Copied to clipboard!', 'success');
            return true;
        } catch (e) {
            this.showToast('Failed to copy', 'error');
            return false;
        }
    }

    // Format date
    static formatDate(date) {
        const d = new Date(date);
        const now = new Date();
        const diff = now - d;

        // Less than 1 minute
        if (diff < 60000) return 'Just now';

        // Less than 1 hour
        if (diff < 3600000) {
            const mins = Math.floor(diff / 60000);
            return `${mins} minute${mins > 1 ? 's' : ''} ago`;
        }

        // Less than 1 day
        if (diff < 86400000) {
            const hours = Math.floor(diff / 3600000);
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        }

        // Less than 1 week
        if (diff < 604800000) {
            const days = Math.floor(diff / 86400000);
            return `${days} day${days > 1 ? 's' : ''} ago`;
        }

        // Default format
        return d.toLocaleDateString();
    }
}

// Make available globally
window.UIUtils = UIUtils;
