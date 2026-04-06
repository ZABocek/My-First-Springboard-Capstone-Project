(function () {
    'use strict';

    // Count existing ingredient groups on page load to determine the first
    // available index.  The counter is never decremented on removal, so every
    // dynamically-added field gets a unique WTForms-compatible name.
    var ingredientIndex = document.querySelectorAll('.ingredient-group').length;

    document.getElementById('add-ingredient').addEventListener('click', function () {
        var ingredientGroup = document.createElement('div');
        ingredientGroup.classList.add('ingredient-group');

        var ingredientField = document.createElement('input');
        ingredientField.name = 'ingredients-' + ingredientIndex;
        ingredientField.type = 'text';
        ingredientGroup.appendChild(ingredientField);
        ingredientGroup.appendChild(document.createElement('br'));

        var measureLabel = document.createElement('strong');
        measureLabel.innerText = 'Measures:';
        ingredientGroup.appendChild(measureLabel);
        ingredientGroup.appendChild(document.createElement('br'));

        var measureField = document.createElement('input');
        measureField.name = 'measures-' + ingredientIndex;
        measureField.type = 'text';
        ingredientGroup.appendChild(measureField);
        ingredientGroup.appendChild(document.createElement('br'));

        var removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'remove-ingredient btn btn-sm btn-danger mt-1 mb-2';
        removeBtn.innerText = 'Remove';
        ingredientGroup.appendChild(removeBtn);

        document.getElementById('ingredient-fields').appendChild(ingredientGroup);
        ingredientIndex++;
    });

    document.getElementById('ingredient-fields').addEventListener('click', function (e) {
        if (e.target.classList.contains('remove-ingredient')) {
            var groups = document.querySelectorAll('.ingredient-group');
            if (groups.length > 1) {
                e.target.closest('.ingredient-group').remove();
            } else {
                alert('At least one ingredient is required!');
            }
        }
    });
}());
