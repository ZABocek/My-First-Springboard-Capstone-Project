(function () {
    'use strict';

    // Image preview on file input change.
    var fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
        fileInput.addEventListener('change', function () {
            var files = this.files;
            if (files && files[0]) {
                var img = document.querySelector('img');
                if (img) {
                    var url = URL.createObjectURL(files[0]);
                    img.src = url;
                    img.addEventListener('load', function () {
                        URL.revokeObjectURL(url);
                    }, { once: true });
                }
            }
        });
    }

    // Remove ingredient button (delegated to the container).
    var container = document.getElementById('ingredients');
    if (container) {
        container.addEventListener('click', function (e) {
            if (e.target.classList.contains('remove-ingredient')) {
                var ingredients = container.querySelectorAll('.ingredient');
                if (ingredients.length > 1) {
                    e.target.closest('.ingredient').remove();
                } else {
                    alert('At least one ingredient is required!');
                }
            }
        });
    }
}());
