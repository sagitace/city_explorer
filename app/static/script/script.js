document.addEventListener("DOMContentLoaded", function (event) {
	document.getElementById("readProductButton").click();
});

document.addEventListener("DOMContentLoaded", function () {
	// Get all elements with the data-modal-toggle attribute
	const buttons = document.querySelectorAll("[data-modal-toggle]");

	// Loop through each button and add a click event listener
	buttons.forEach(function (button) {
		button.addEventListener("click", function () {
			// Get the corresponding modal ID from the data-modal-target attribute
			const modalId = button.getAttribute("data-modal-target");
			const modal = document.getElementById(modalId);

			// If the modal exists, toggle its visibility
			if (modal) {
				modal.classList.toggle("hidden");
			}
		});
	});
});

//gallery
const mainImage = document.getElementById("mainImage");

// Get all thumbnail images
const thumbnails = document.querySelectorAll(".thumbnail");

// Add click event listener to each thumbnail
thumbnails.forEach((thumbnail) => {
	thumbnail.addEventListener("click", function () {
		// Update the src of the main image with the clicked thumbnail's src
		mainImage.src = this.src;
	});
});

$(document).ready(function () {
	$("#city").select2({
		placeholder: "Select a city",
		allowClear: true,
	});
});
