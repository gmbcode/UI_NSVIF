// main_dashboard.js

document.addEventListener('DOMContentLoaded', () => {
    // 1. Theme Toggle Logic
    const toggleCheckbox = document.getElementById('toggle');
    if (toggleCheckbox) {
        // Sync toggle check status with active class
        toggleCheckbox.checked = !document.documentElement.classList.contains('light');

        toggleCheckbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                document.documentElement.classList.remove('light');
                document.documentElement.classList.add('dark');
                localStorage.setItem('theme', 'dark');
            } else {
                document.documentElement.classList.remove('dark');
                document.documentElement.classList.add('light');
                localStorage.setItem('theme', 'light');
            }
        });
    }

    // 2. Floor Selector Modal Logic
    const floorModal = document.getElementById('floorModal');
    const floorModalContent = document.getElementById('floorModalContent');
    const btnFloorPlanCard = document.getElementById('btnFloorPlanCard');
    const btnCloseFloorModal = document.getElementById('btnCloseFloorModal');

    function openModal() {
        floorModal.classList.remove('hidden');
        floorModal.classList.add('flex');
        
        // Force reflow for CSS transition
        void floorModal.offsetWidth;

        floorModalContent.classList.remove('opacity-0', 'scale-95');
        floorModalContent.classList.add('opacity-100', 'scale-100');
    }

    function closeModal() {
        floorModalContent.classList.remove('opacity-100', 'scale-100');
        floorModalContent.classList.add('opacity-0', 'scale-95');

        // Wait for animation to finish before hiding the modal overlay
        setTimeout(() => {
            floorModal.classList.remove('flex');
            floorModal.classList.add('hidden');
        }, 200); // matches transition speed
    }

    if (btnFloorPlanCard) {
        btnFloorPlanCard.addEventListener('click', (e) => {
            e.stopPropagation();
            openModal();
        });
    }

    if (btnCloseFloorModal) {
        btnCloseFloorModal.addEventListener('click', closeModal);
    }

    // Close on click outside content area
    if (floorModal) {
        floorModal.addEventListener('click', (e) => {
            if (e.target === floorModal) {
                closeModal();
            }
        });
    }
});
