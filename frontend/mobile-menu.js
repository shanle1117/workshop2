/**
 * Mobile Menu JavaScript for FAIX Website
 * Handles mobile navigation menu toggle and interactions
 */

document.addEventListener('DOMContentLoaded', () => {
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    const mainNav = document.getElementById('main-nav');
    const mobileNavOverlay = document.getElementById('mobile-nav-overlay');
    const navDropdowns = document.querySelectorAll('.has-dropdown');
    
    if (!mobileMenuToggle || !mainNav) {
        return; // Menu elements not found, skip initialization
    }
    
    // Toggle mobile menu
    function toggleMobileMenu() {
        const isActive = mainNav.classList.contains('active');
        
        if (isActive) {
            closeMobileMenu();
        } else {
            openMobileMenu();
        }
    }
    
    function openMobileMenu() {
        mainNav.classList.add('active');
        mobileMenuToggle.classList.add('active');
        if (mobileNavOverlay) {
            mobileNavOverlay.classList.add('active');
        }
        document.body.style.overflow = 'hidden';
    }
    
    function closeMobileMenu() {
        mainNav.classList.remove('active');
        mobileMenuToggle.classList.remove('active');
        if (mobileNavOverlay) {
            mobileNavOverlay.classList.remove('active');
        }
        document.body.style.overflow = '';
        
        // Close all dropdowns
        navDropdowns.forEach(dropdown => {
            dropdown.classList.remove('active');
        });
    }
    
    // Toggle button click
    mobileMenuToggle.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleMobileMenu();
    });
    
    // Overlay click to close
    if (mobileNavOverlay) {
        mobileNavOverlay.addEventListener('click', () => {
            closeMobileMenu();
        });
    }
    
    // Handle dropdown toggles on mobile
    navDropdowns.forEach(dropdown => {
        const dropdownLink = dropdown.querySelector('> a');
        
        if (dropdownLink) {
            dropdownLink.addEventListener('click', (e) => {
                // Only prevent default on mobile
                if (window.innerWidth <= 992) {
                    e.preventDefault();
                    dropdown.classList.toggle('active');
                }
            });
        }
    });
    
    // Close menu when clicking on a non-dropdown link
    const navLinks = mainNav.querySelectorAll('.nav-menu > li:not(.has-dropdown) > a');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 992) {
                closeMobileMenu();
            }
        });
    });
    
    // Close menu when window is resized to desktop size
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            if (window.innerWidth > 992) {
                closeMobileMenu();
            }
        }, 250);
    });
    
    // Close menu on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && mainNav.classList.contains('active')) {
            closeMobileMenu();
        }
    });
    
    // Prevent body scroll when menu is open (touch devices)
    let touchStartY = 0;
    let touchEndY = 0;
    
    if (mobileNavOverlay) {
        mobileNavOverlay.addEventListener('touchstart', (e) => {
            touchStartY = e.touches[0].clientY;
        }, { passive: true });
        
        mobileNavOverlay.addEventListener('touchmove', (e) => {
            if (mainNav.classList.contains('active')) {
                e.preventDefault();
            }
        }, { passive: false });
    }
});
