
$(document).ready(function() {
// Add sub-form
    $('.add-car-subform').click(function() {
        let index = $('#cars_list .car-subform').length;
        let html = '{% include "inc/_car_creation_item.html" with c_id=None %}';
        // $('#cars_list').insertAdjacentHTML('afterbegin', html);
        const box = document.getElementById('cars_list');

        box.insertAdjacentHTML(
          'beforeend',
          html,
        );

    });

    // Remove sub-form
    $('#cars_list').on('click', '.remove-car-subform', function() {
        $(this).closest('.car-subform').remove();
    });
});