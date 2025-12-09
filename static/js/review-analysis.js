/**
 * Review Analysis Frontend
 * Handles fetching, analyzing, and displaying restaurant reviews with AI insights
 */

class ReviewAnalysis {
    constructor() {
        this.currentPlaceId = null;
        this.currentRestaurantName = null;
        this.analysisData = null;
    }

    /**
     * Initialize review analysis for a restaurant
     */
    async init(placeId, restaurantName) {
        this.currentPlaceId = placeId;
        this.currentRestaurantName = restaurantName;

        // Show loading state
        this.showLoading();

        try {
            // Fetch and analyze reviews
            await this.fetchAndAnalyze();
        } catch (error) {
            console.error('Error initializing review analysis:', error);
            this.showError('Failed to load review analysis');
        }
    }

    /**
     * Fetch and analyze reviews
     */
    async fetchAndAnalyze() {
        try {
            // First, fetch reviews (will use cache if available)
            const fetchResponse = await fetch('/api/reviews/fetch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    place_id: this.currentPlaceId,
                    restaurant_name: this.currentRestaurantName,
                    force_refresh: false
                })
            });

            if (!fetchResponse.ok) {
                throw new Error('Failed to fetch reviews');
            }

            const fetchData = await fetchResponse.json();

            if (!fetchData.success || fetchData.reviews_count === 0) {
                this.showNoReviews();
                return;
            }

            // Then, analyze reviews (will use cache if available)
            const analyzeResponse = await fetch('/api/reviews/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    place_id: this.currentPlaceId,
                    use_cache: true
                })
            });

            if (!analyzeResponse.ok) {
                throw new Error('Failed to analyze reviews');
            }

            const analyzeData = await analyzeResponse.json();

            if (analyzeData.success) {
                this.analysisData = analyzeData;
                this.render();
            } else {
                throw new Error(analyzeData.error || 'Analysis failed');
            }

        } catch (error) {
            console.error('Error in fetchAndAnalyze:', error);
            this.showError(error.message);
        }
    }

    /**
     * Refresh reviews and analysis
     */
    async refresh() {
        this.showLoading();

        try {
            const response = await fetch('/api/reviews/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    place_id: this.currentPlaceId
                })
            });

            if (!response.ok) {
                throw new Error('Failed to refresh reviews');
            }

            const data = await response.json();

            if (data.success) {
                this.analysisData = data;
                this.render();

                if (typeof UIUtils !== 'undefined' && UIUtils.showToast) {
                    UIUtils.showToast('Reviews refreshed successfully!', 'success');
                }
            } else {
                throw new Error(data.error || 'Refresh failed');
            }

        } catch (error) {
            console.error('Error refreshing:', error);
            this.showError(error.message);
        }
    }

    /**
     * Render the complete analysis UI
     */
    render() {
        const container = document.getElementById('review-analysis-container');
        if (!container) return;

        const data = this.analysisData;

        container.innerHTML = `
            <div class="review-analysis-section">
                <!-- Header with refresh button -->
                <div class="analysis-header">
                    <h3><i class="fas fa-chart-line"></i> AI-Powered Review Analysis</h3>
                    <button class="refresh-btn" onclick="reviewAnalysis.refresh()">
                        <i class="fas fa-sync-alt"></i> Refresh
                    </button>
                </div>

                <!-- Sentiment Overview -->
                <div class="sentiment-overview">
                    ${this.renderSentimentChart(data)}
                </div>

                <!-- Topic Highlights -->
                <div class="topic-highlights">
                    ${this.renderTopicHighlights(data)}
                </div>

                <!-- Highlights Grid -->
                <div class="highlights-grid">
                    ${this.renderPositiveHighlights(data)}
                    ${this.renderNegativeHighlights(data)}
                </div>

                <!-- Best Items -->
                ${data.best_items && data.best_items.length > 0 ? `
                <div class="best-items-section">
                    ${this.renderBestItems(data)}
                </div>
                ` : ''}

                <!-- AI Insights -->
                <div class="ai-insights">
                    ${this.renderAISummary(data)}
                    ${this.renderAIRecommendations(data)}
                </div>

                <!-- Source Info -->
                <div class="analysis-footer">
                    <span class="source-badge">
                        <i class="fas fa-database"></i> ${data.review_source_used || 'Google Places API'}
                    </span>
                    <span class="cache-info">
                        ${data.source === 'cache' ? '<i class="fas fa-clock"></i> Cached' : '<i class="fas fa-sparkles"></i> Fresh Analysis'}
                    </span>
                    ${data.review_count ? `<span class="review-count">${data.review_count} reviews analyzed</span>` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Render sentiment breakdown chart
     */
    renderSentimentChart(data) {
        const percentages = data.sentiment_percentages || { positive: 0, neutral: 0, negative: 0 };
        const overall = data.overall_sentiment || 'neutral';

        return `
            <div class="sentiment-chart-card">
                <h4>Overall Sentiment: <span class="sentiment-${overall}">${overall.toUpperCase()}</span></h4>
                <div class="sentiment-bars">
                    <div class="sentiment-bar positive">
                        <div class="bar-fill" style="width: ${percentages.positive}%"></div>
                        <span class="bar-label">Positive ${percentages.positive}%</span>
                    </div>
                    <div class="sentiment-bar neutral">
                        <div class="bar-fill" style="width: ${percentages.neutral}%"></div>
                        <span class="bar-label">Neutral ${percentages.neutral}%</span>
                    </div>
                    <div class="sentiment-bar negative">
                        <div class="bar-fill" style="width: ${percentages.negative}%"></div>
                        <span class="bar-label">Negative ${percentages.negative}%</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render topic highlights
     */
    renderTopicHighlights(data) {
        const topics = data.top_topics || [];

        if (topics.length === 0) {
            return '<p class="no-data">No topics identified</p>';
        }

        return `
            <div class="topics-card">
                <h4><i class="fas fa-tags"></i> Key Topics</h4>
                <div class="topic-chips">
                    ${topics.map(topic => `
                        <span class="topic-chip">${topic}</span>
                    `).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Render positive highlights
     */
    renderPositiveHighlights(data) {
        const highlights = data.positive_highlights || [];

        return `
            <div class="highlights-card positive-card">
                <h4><i class="fas fa-thumbs-up"></i> What Customers Love</h4>
                ${highlights.length > 0 ? `
                    <ul class="highlights-list">
                        ${highlights.map(h => `<li><i class="fas fa-check-circle"></i> ${h}</li>`).join('')}
                    </ul>
                ` : '<p class="no-data">No positive highlights</p>'}
            </div>
        `;
    }

    /**
     * Render negative highlights
     */
    renderNegativeHighlights(data) {
        const highlights = data.negative_highlights || [];

        return `
            <div class="highlights-card negative-card">
                <h4><i class="fas fa-exclamation-triangle"></i> Areas for Improvement</h4>
                ${highlights.length > 0 ? `
                    <ul class="highlights-list">
                        ${highlights.map(h => `<li><i class="fas fa-times-circle"></i> ${h}</li>`).join('')}
                    </ul>
                ` : '<p class="no-data">No major complaints</p>'}
            </div>
        `;
    }

    /**
     * Render best items
     */
    renderBestItems(data) {
        const items = data.best_items || [];

        return `
            <div class="best-items-card">
                <h4><i class="fas fa-star"></i> Must-Try Dishes</h4>
                <div class="items-grid">
                    ${items.map(item => `
                        <div class="item-badge">
                            <i class="fas fa-utensils"></i> ${item}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Render AI summary
     */
    renderAISummary(data) {
        const summary = data.ai_summary || 'No summary available';

        return `
            <div class="ai-card summary-card">
                <h4><i class="fas fa-robot"></i> AI Summary</h4>
                <p class="ai-text">${summary}</p>
                <span class="ai-badge">Powered by Gemini AI</span>
            </div>
        `;
    }

    /**
     * Render AI recommendations
     */
    renderAIRecommendations(data) {
        const recommendations = data.ai_recommendations || 'No recommendations available';

        return `
            <div class="ai-card recommendations-card">
                <h4><i class="fas fa-lightbulb"></i> AI Recommendations</h4>
                <p class="ai-text">${recommendations}</p>
            </div>
        `;
    }

    /**
     * Show loading state
     */
    showLoading() {
        const container = document.getElementById('review-analysis-container');
        if (!container) return;

        container.innerHTML = `
            <div class="analysis-loading">
                <div class="spinner"></div>
                <p>Analyzing reviews with AI...</p>
            </div>
        `;
    }

    /**
     * Show error state
     */
    showError(message) {
        const container = document.getElementById('review-analysis-container');
        if (!container) return;

        container.innerHTML = `
            <div class="analysis-error">
                <i class="fas fa-exclamation-circle"></i>
                <p>${message}</p>
                <button onclick="reviewAnalysis.refresh()" class="retry-btn">
                    <i class="fas fa-redo"></i> Try Again
                </button>
            </div>
        `;
    }

    /**
     * Show no reviews state
     */
    showNoReviews() {
        const container = document.getElementById('review-analysis-container');
        if (!container) return;

        container.innerHTML = `
            <div class="analysis-empty">
                <i class="fas fa-comment-slash"></i>
                <p>No reviews available for this restaurant yet.</p>
                <p class="empty-subtext">Be the first to review!</p>
            </div>
        `;
    }
}

// Initialize global instance
const reviewAnalysis = new ReviewAnalysis();
