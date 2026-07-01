document.addEventListener("DOMContentLoaded", () => {

    document
        .getElementById("generateBtn")
        .addEventListener("click", generateDXF);

    document
        .getElementById("downloadBtn")
        .addEventListener("click", downloadDXF);

});

let currentImageUrl = null;

async function generateDXF() {

    const status =
        document.getElementById("status");

    const statusDot =
        document.getElementById("statusDot");

    const viewer =
        document.getElementById("viewer");

    try {

        status.innerText =
            "Generating layout...";

        statusDot.className =
            "w-2.5 h-2.5 rounded-full bg-yellow-500 animate-pulse";

        const response =
            await fetch(
                "/api/multifloor-image",
                {
                    method: "POST"
                }
            );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }

        const blob =
            await response.blob();

        if (currentImageUrl) {
            URL.revokeObjectURL(
                currentImageUrl
            );
        }

        currentImageUrl =
            URL.createObjectURL(blob);

        viewer.src =
            currentImageUrl;

        status.innerText =
            "Layout generated successfully";

        statusDot.className =
            "w-2.5 h-2.5 rounded-full bg-green-500";

    } catch (err) {

        console.error(err);

        status.innerText =
            "Generation failed";

        statusDot.className =
            "w-2.5 h-2.5 rounded-full bg-red-500";
    }
}

async function downloadDXF() {

    const response =
        await fetch(
            "/api/multifloor-dxf",
            {
                method: "POST"
            }
        );

    const blob =
        await response.blob();

    const url =
        URL.createObjectURL(blob);

    const link =
        document.createElement("a");

    link.href = url;
    link.download = "multifloor.dxf";

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
}
















