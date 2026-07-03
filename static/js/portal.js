// portal.js

document.addEventListener("DOMContentLoaded", () => {
    // 1. Theme Toggle Sync
    const toggleCheckbox = document.getElementById('toggle');
    if (toggleCheckbox) {
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

    // 2. Market Analysis Card - Inactive
    const btnMarketAnalysisCard = document.getElementById("btnMarketAnalysisCard");
    if (btnMarketAnalysisCard) {
        btnMarketAnalysisCard.addEventListener("click", () => {
            alert("Market Analysis module is currently locked. Exploration configurations will be enabled in a future release.");
        });
    }

    // 3. Modal Controls
    const projectModal = document.getElementById("projectModal");
    const projectModalContent = document.getElementById("projectModalContent");
    const btnBuildingCard = document.getElementById("btnBuildingCard");
    const btnCancelModal = document.getElementById("btnCancelModal");
    const projectForm = document.getElementById("projectForm");

    function openModal() {
        projectModal.classList.remove("hidden");
        projectModal.classList.add("flex");
        // Force reflow
        void projectModal.offsetWidth;
        projectModalContent.classList.remove("opacity-0", "scale-95");
        projectModalContent.classList.add("opacity-100", "scale-100");
    }

    function closeModal() {
        projectModalContent.classList.remove("opacity-100", "scale-100");
        projectModalContent.classList.add("opacity-0", "scale-95");
        setTimeout(() => {
            projectModal.classList.remove("flex");
            projectModal.classList.add("hidden");
        }, 200);
    }

    if (btnBuildingCard) {
        btnBuildingCard.addEventListener("click", openModal);
    }

    if (btnCancelModal) {
        btnCancelModal.addEventListener("click", closeModal);
    }

    // Submit Project Form
    if (projectForm) {
        projectForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const name = document.getElementById("projectName").value.trim();
            const address = document.getElementById("projectAddress").value.trim();

            if (!name || !address) return;

            try {
                const response = await fetch("/api/select-project", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ name, address })
                });

                if (response.ok) {
                    // Redirect to project workspace
                    window.location.href = "/project-dashboard";
                } else {
                    alert("Failed to create project workspace. Please try again.");
                }
            } catch (err) {
                console.error("Error setting project state:", err);
                alert("Connection error. Could not setup project.");
            }
        });
    }
});
