/**
 * Datify - Main JavaScript File
 * Handles UI interactions, navbar behavior, and form validation
 */

document.addEventListener('DOMContentLoaded', function() {
    // Navbar scroll effect
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
        
        // Initial check for page refresh
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        }
    }
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]:not([href="#"])').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                window.scrollTo({
                    top: target.offsetTop - 100,
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Bootstrap tooltips initialization
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Password strength meter
    const passwordInput = document.getElementById('password');
    const passwordStrength = document.getElementById('password-strength');
    
    if (passwordInput && passwordStrength) {
        passwordInput.addEventListener('input', function() {
            const password = this.value;
            let strength = 0;
            
            // Length check
            if (password.length >= 8) strength += 1;
            
            // Contains lowercase
            if (/[a-z]/.test(password)) strength += 1;
            
            // Contains uppercase
            if (/[A-Z]/.test(password)) strength += 1;
            
            // Contains number
            if (/[0-9]/.test(password)) strength += 1;
            
            // Contains special character
            if (/[^A-Za-z0-9]/.test(password)) strength += 1;
            
            // Update UI
            passwordStrength.className = 'password-strength';
            
            if (password.length === 0) {
                passwordStrength.textContent = '';
            } else if (strength < 2) {
                passwordStrength.textContent = 'Weak';
                passwordStrength.classList.add('weak');
            } else if (strength < 4) {
                passwordStrength.textContent = 'Medium';
                passwordStrength.classList.add('medium');
            } else {
                passwordStrength.textContent = 'Strong';
                passwordStrength.classList.add('strong');
            }
        });
    }
    
    // Mobile menu close when clicking outside
    const navbarCollapse = document.querySelector('.navbar-collapse');
    if (navbarCollapse) {
        document.addEventListener('click', function(e) {
            const isNavbarToggler = e.target.closest('.navbar-toggler');
            const isNavbarCollapse = e.target.closest('.navbar-collapse');
            
            if (!isNavbarToggler && !isNavbarCollapse && navbarCollapse.classList.contains('show')) {
                const bsCollapse = new bootstrap.Collapse(navbarCollapse);
                bsCollapse.hide();
            }
        });
    }
    
    // Back to top button
    const backToTopBtn = document.getElementById('back-to-top');
    if (backToTopBtn) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 300) {
                backToTopBtn.style.display = 'block';
            } else {
                backToTopBtn.style.display = 'none';
            }
        });
        
        backToTopBtn.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }
    
    // Image preview on upload
    const profileImageInput = document.getElementById('profile-image');
    const imagePreviewContainer = document.getElementById('image-preview');
    
    if (profileImageInput && imagePreviewContainer) {
        profileImageInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    imagePreviewContainer.innerHTML = `<img src="${e.target.result}" class="img-fluid rounded-circle" alt="Profile Preview">`;
                }
                
                reader.readAsDataURL(this.files[0]);
            }
        });
    }
});

