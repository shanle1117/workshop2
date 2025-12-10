/**
 * Admin Dashboard JavaScript
 */

class AdminDashboard {
    constructor() {
        this.loadDashboardData();
        this.loadKnowledgeBase();
        this.attachEventListeners();
    }
    
    /**
     * Escape HTML entities to prevent XSS attacks
     * @param {string} text - Text to escape
     * @returns {string} - Escaped HTML string
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    attachEventListeners() {
        document.getElementById('refresh-kb')?.addEventListener('click', () => {
            this.loadKnowledgeBase();
        });
        
        document.getElementById('kb-search')?.addEventListener('input', (e) => {
            this.filterKBEntries(e.target.value);
        });
        
        document.getElementById('kb-category-filter')?.addEventListener('change', (e) => {
            this.filterKBEntries(null, e.target.value);
        });
    }
    
    async loadDashboardData() {
        try {
            const response = await fetch('/api/admin/dashboard/');
            
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('Dashboard API endpoint not found');
                } else if (response.status >= 500) {
                    throw new Error('Server error occurred');
                } else {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
            }
            
            let data;
            try {
                data = await response.json();
            } catch (jsonError) {
                throw new Error('Invalid JSON response from server');
            }
            
            // Update stats
            document.getElementById('total-conversations').textContent = data.total_conversations || 0;
            document.getElementById('total-messages').textContent = data.total_messages || 0;
            document.getElementById('active-users').textContent = data.active_users || 0;
            
            // Update intent distribution
            this.renderIntentChart(data.intent_distribution || {});
            
            // Update popular queries
            this.renderPopularQueries(data.popular_queries || []);
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            const container = document.getElementById('intent-chart');
            if (container) {
                container.innerHTML = '<p style="color: #ef4444;">Error loading dashboard data. Please refresh the page.</p>';
            }
        }
    }
    
    renderIntentChart(distribution) {
        const container = document.getElementById('intent-chart');
        if (!container) return;
        
        if (Object.keys(distribution).length === 0) {
            container.innerHTML = '<p>No data available</p>';
            return;
        }
        
        const items = Object.entries(distribution)
            .sort((a, b) => b[1] - a[1])
            .map(([intent, count]) => {
                const escapedIntent = this.escapeHtml(intent);
                const escapedCount = this.escapeHtml(String(count));
                return `
                    <div class="list-item">
                        <span><strong>${escapedIntent}</strong></span>
                        <span>${escapedCount}</span>
                    </div>
                `;
            }).join('');
        
        container.innerHTML = items;
    }
    
    renderPopularQueries(queries) {
        const container = document.getElementById('popular-queries');
        if (!container) return;
        
        if (queries.length === 0) {
            container.innerHTML = '<p>No queries available</p>';
            return;
        }
        
        const items = queries.map(query => {
            const escapedQuery = this.escapeHtml(query.query);
            const escapedCount = this.escapeHtml(String(query.count));
            return `
                <div class="list-item">
                    <span>${escapedQuery}</span>
                    <span>${escapedCount}</span>
                </div>
            `;
        }).join('');
        
        container.innerHTML = items;
    }
    
    async loadKnowledgeBase() {
        const container = document.getElementById('kb-entries');
        if (!container) return;
        
        try {
            const response = await fetch('/api/admin/kb/');
            
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('Knowledge base API endpoint not found');
                } else if (response.status >= 500) {
                    throw new Error('Server error occurred');
                } else {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
            }
            
            let data;
            try {
                data = await response.json();
            } catch (jsonError) {
                throw new Error('Invalid JSON response from server');
            }
            
            if (!data || !data.entries) {
                throw new Error('Invalid response format');
            }
            
            this.renderKBEntries(data.entries || []);
            this.updateCategoryFilter(data.entries || []);
        } catch (error) {
            console.error('Error loading knowledge base:', error);
            const errorMessage = error.message || 'Error loading knowledge base';
            container.innerHTML = `<p style="color: #ef4444;">${this.escapeHtml(errorMessage)}. Please try again later.</p>`;
        }
    }
    
    renderKBEntries(entries) {
        const container = document.getElementById('kb-entries');
        if (!container) return;
        
        if (entries.length === 0) {
            container.innerHTML = '<p>No entries found</p>';
            return;
        }
        
        const items = entries.map(entry => {
            const escapedCategory = this.escapeHtml(entry.category);
            const escapedQuestion = this.escapeHtml(entry.question);
            const answerPreview = entry.answer.substring(0, 150);
            const escapedAnswer = this.escapeHtml(answerPreview) + (entry.answer.length > 150 ? '...' : '');
            const escapedViewCount = this.escapeHtml(String(entry.view_count || 0));
            const escapedHelpfulCount = this.escapeHtml(String(entry.helpful_count || 0));
            return `
                <div class="kb-entry">
                    <span class="category">${escapedCategory}</span>
                    <h4>${escapedQuestion}</h4>
                    <p>${escapedAnswer}</p>
                    <div class="stats">
                        <span>Views: ${escapedViewCount}</span>
                        <span>Helpful: ${escapedHelpfulCount}</span>
                    </div>
                </div>
            `;
        }).join('');
        
        container.innerHTML = items;
    }
    
    updateCategoryFilter(entries) {
        const filter = document.getElementById('kb-category-filter');
        if (!filter) return;
        
        const categories = [...new Set(entries.map(e => e.category))].sort();
        const currentValue = filter.value;
        
        filter.innerHTML = '<option value="">All Categories</option>' +
            categories.map(cat => {
                const escapedCat = this.escapeHtml(cat);
                return `<option value="${escapedCat}">${escapedCat}</option>`;
            }).join('');
        
        if (currentValue) {
            filter.value = currentValue;
        }
    }
    
    filterKBEntries(searchText, category) {
        // Simple client-side filtering
        const entries = document.querySelectorAll('.kb-entry');
        entries.forEach(entry => {
            const text = entry.textContent.toLowerCase();
            const entryCategory = entry.querySelector('.category')?.textContent.toLowerCase();
            
            let show = true;
            
            if (searchText && !text.includes(searchText.toLowerCase())) {
                show = false;
            }
            
            if (category && entryCategory !== category.toLowerCase()) {
                show = false;
            }
            
            entry.style.display = show ? 'block' : 'none';
        });
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.adminDashboard = new AdminDashboard();
});

