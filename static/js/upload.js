document.getElementById("uploadForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    const input = document.getElementById("photoInput");
    const btn = document.getElementById("uploadBtn");
    const progressDiv = document.getElementById("progress");
    const progressBar = document.getElementById("progressBar");
    const progressText = document.getElementById("progressText");
    const resultDiv = document.getElementById("result");

    if (!input.files.length) return;

    const formData = new FormData();
    for (const file of input.files) {
        formData.append("photos", file);
    }

    btn.disabled = true;
    progressDiv.style.display = "block";
    resultDiv.style.display = "none";
    progressBar.style.width = "10%";
    progressText.textContent = `Uploading ${input.files.length} photo(s)...`;

    try {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/upload");

        xhr.upload.addEventListener("progress", (e) => {
            if (e.lengthComputable) {
                const pct = Math.round((e.loaded / e.total) * 90) + 10;
                progressBar.style.width = pct + "%";
                progressText.textContent = `Uploading... ${pct}%`;
            }
        });

        xhr.onload = function () {
            progressBar.style.width = "100%";
            progressText.textContent = "Upload complete!";

            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                resultDiv.style.display = "block";
                resultDiv.innerHTML = `
                    <div class="alert alert-success">
                        <strong>${data.queued} photo(s) uploaded.</strong>
                        Face matching is running in the background.
                        Guests will be emailed when processing is complete.
                    </div>`;
            } else {
                resultDiv.style.display = "block";
                resultDiv.innerHTML = `<div class="alert alert-error">Upload failed. Please try again.</div>`;
            }
            btn.disabled = false;
        };

        xhr.onerror = function () {
            progressText.textContent = "Network error.";
            btn.disabled = false;
        };

        xhr.send(formData);
    } catch (err) {
        progressText.textContent = "Error: " + err.message;
        btn.disabled = false;
    }
});
