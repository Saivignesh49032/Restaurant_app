// Review Submission Form JavaScript
// Add to static/js/details.js or create new file

document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('reviewSubmissionForm');
    const stars = document.querySelectorAll('.star-rating-input i');
    const ratingInput = document.getElementById('ratingValue');
    const ratingText = document.querySelector('.rating-text');
    const reviewText = document.getElementById('reviewText');
    const charCount = document.querySelector('.char-count');
    const charMin = document.querySelector('.char-min');
    const submitBtn = document.querySelector('.submit-review-btn');
    const message = document.getElementById('reviewSubmissionMessage');

    const ratingLabels = {
        1: 'Poor',
        2: 'Fair',
        3: 'Good',
        4: 'Very Good',
        5: 'Excellent'
    };

    // Star rating functionality
    let selectedRating = 0;

    stars.forEach(star => {
        star.addEventListener('click', function () {
            selectedRating = parseInt(this.dataset.rating);
            ratingInput.value = selectedRating;
            updateStars(selectedRating);
            ratingText.textContent = ratingLabels[selectedRating];
            validateForm();
        });

        star.addEventListener('mouseenter', function () {
            const rating = parseInt(this.dataset.rating);
            updateStars(rating);
        });
    });

    document.querySelector('.star-rating-input').addEventListener('mouseleave', function () {
        updateStars(selectedRating);
    });

    function updateStars(rating) {
        stars.forEach((star, index) => {
            if (index < rating) {
                star.classList.remove('far');
                star.classList.add('fas', 'active');
            } else {
                star.classList.remove('fas', 'active');
                star.classList.add('far');
            }
        });
    }

    // Character count
    reviewText.addEventListener('input', function () {
        const length = this.value.length;
        charCount.textContent = `${length}/1000`;

        if (length < 20) {
            charMin.style.display = 'block';
        } else {
            charMin.style.display = 'none';
        }

        validateForm();
    });

    // Form validation
    function validateForm() {
        const isValid = selectedRating > 0 && reviewText.value.trim().length >= 20;
        submitBtn.disabled = !isValid;
    }

    // Form submission
    if (form) {
        form.addEventListener('submit', async function (e) {
            e.preventDefault();

            const rating = parseInt(ratingInput.value);
            const text = reviewText.value.trim();

            if (!rating || text.length < 20) {
                showMessage('Please provide a rating and write at least 20 characters', 'error');
                return;
            }

            // Get restaurant data
            const restaurantData = JSON.parse(document.getElementById('restaurant-data').textContent);
            const restaurantId = '{{ restaurant.get("Restaurant ID") or restaurant.get("id") or restaurant.get("Restaurant Name", "").replace(" ", "_") }}';
            const restaurantName = restaurantData.name;
            const city = '{{ restaurant.get("City") or restaurant.get("city") or "" }}';

            // Show loading state
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';

            try {
                const response = await fetch('/api/reviews/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        restaurant_id: restaurantId,
                        restaurant_name: restaurantName,
                        city: city,
                        rating: rating,
                        review_text: text
                    })
                });

                const data = await response.json();

                if (data.success) {
                    showMessage(data.message, 'success');
                    form.reset();
                    selectedRating = 0;
                    updateStars(0);
                    ratingText.textContent = '';
                    charCount.textContent = '0/1000';

                    // Refresh review analysis after 2 seconds
                    setTimeout(() => {
                        if (window.reviewAnalysis) {
                            reviewAnalysis.fetchReviews(true);
                        }
                    }, 2000);
                } else {
                    showMessage(data.error || 'Failed to submit review', 'error');
                }
            } catch (error) {
                console.error('Error submitting review:', error);
                showMessage('An error occurred. Please try again.', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Submit Review';
            }
        });
    }

    function showMessage(text, type) {
        message.textContent = text;
        message.className = `submission-message ${type}`;
        message.style.display = 'block';

        setTimeout(() => {
            message.style.display = 'none';
        }, 5000);
    }
});
