
$(document).ready(function() {
    // Add sub-form
    $('.add-visitor-subform').click(function() {
        let index = $('#visitors_list .visitor-subform').length;
        let html = '{% include "inc/_visitor_creation_item.html" with index=index, v_id=None %}';
        $('#visitors_list').append(html);
    });

    // Remove sub-form
    $('#visitors_list').on('click', '.remove-visitor-subform', function() {
        $(this).closest('.visitor-subform').remove();
    });
});