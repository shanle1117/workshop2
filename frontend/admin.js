/**
 * Admin Dashboard JavaScript
 */

class AdminDashboard {
    constructor() {
        this.loadDashboardData();
        this.loadKnowledgeBase();
        this.attachEventListeners();
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
            const data = await response.json();
            
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
                return `
                    <div class="list-item">
                        <span><strong>${intent}</strong></span>
                        <span>${count}</span>
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
            return `
                <div class="list-item">
                    <span>${query.query}</span>
                    <span>${query.count}</span>
                </div>
            `;
        }).join('');
        
        container.innerHTML = items;
    }
    
    async loadKnowledgeBase() {
        try {
            const response = await fetch('/api/admin/kb/');
            const data = await response.json();
            
            this.renderKBEntries(data.entries || []);
            this.updateCategoryFilter(data.entries || []);
        } catch (error) {
            console.error('Error loading knowledge base:', error);
            document.getElementById('kb-entries').innerHTML = '<p>Error loading knowledge base</p>';
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
            return `
                <div class="kb-entry">
                    <span class="category">${entry.category}</span>
                    <h4>${entry.question}</h4>
                    <p>${entry.answer.substring(0, 150)}${entry.answer.length > 150 ? '...' : ''}</p>
                    <div class="stats">
                        <span>Views: ${entry.view_count || 0}</span>
                        <span>Helpful: ${entry.helpful_count || 0}</span>
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
            categories.map(cat => `<option value="${cat}">${cat}</option>`).join('');
        
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

