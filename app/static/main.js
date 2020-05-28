/* May require cache bypass in Chrome/Mac: shift + cmd + r */
$(document).ready(function() {

    var hlpDiv = $('#selection_error');
    
    var currPage = $(location).attr('href').split("/").pop();
    switch(currPage) {
        case 'blast':

        // Get input seq length for display
        $('#sequence_textarea').bind('input', function(){
            $('#sequence_count').text($(this).val().length);
        });

        var hlpElem = $('#result_table tr > td:nth-child(6), #result_table tr>th:nth-child(6)');


        // Convert reasults to jQuery dataTable
        var dataTbl = makeDataTbl(5, hlpElem, hlpDiv)
        // Enable access to checkboxes in all rows over all pages

        break;
        case 'search_api':
        alert('This is api');
        break;
        default:
        alert('This neither blast nor api');
        break;
    }

    var allPages = dataTbl.fnGetNodes();
    var asvBoxes = $('.asv_id', allPages);


    // When any ASV checkbox is changed
    asvBoxes.change(function () {
        // Toggle download selection
        $(this).closest('tr').toggleClass('selectedRow', this.checked);
        // Remove no-selection warnings (if any)
        if (this.checked) {
            hlpElem.removeClass('visHlpElem');
            hlpDiv.removeClass('visHlpDiv');
        }
    });

    // When header checkbox is changed
    $('#select_all').change(function () {
        // Toggle all ASV checkboxes
        asvBoxes.prop('checked', this.checked);
        // Toggle download selection
        asvBoxes.closest('tr').toggleClass('selectedRow', this.checked);
        // Remove no-selection warnings (if any)
        hlpElem.removeClass('visHlpElem');
        hlpDiv.removeClass('visHlpDiv');
    });

    // At SBDI submit
    $('#rform').submit(function() {
        // Copy ASV ids to hidden area
        addCheckedToArea(asvBoxes, $('#raw_names'));
        // Warn & stop if no selection
        if (!$('#raw_names').val()) {
            return alertNoSelection(hlpElem, hlpDiv);
        }
    });

});

// Add checked ids to hidden textarea - for POST to SBDI
function addCheckedToArea(asvBoxes) {
    var ids = [];
    // Add checked ids to list
    asvBoxes.map(function () {
        if($(this).is(":checked")){
            ids.push(this.id);
        }
    });
    // Remove duplicates
    ids = ids.filter(function(item, i, ids) {
        return i == ids.indexOf(item);
    });
    // Add ids to textarea
    $('#raw_names').val(ids.join('\n'));
}

// Warn & stop if no selection for SBDI submission / download
function alertNoSelection(hlpElem, hlpDiv) {
    hlpDiv.addClass('visHlpDiv');
    hlpElem.addClass('visHlpElem');
    return false;
}

// Make jQuery dataTable from html table
// hlpElem/Div needs to be passed here
function makeDataTbl(CheckBoxIdx, hlpElem, hlpDiv) {
    var dataTbl = $('#result_table').dataTable({
        // Modify layout of dataTable components:
        // l=Show.., f=Search, tr=table, i=Showing.., p=pagination
        dom: "<'row'<'col-md-4'l><'col-md-8'f>>" +
        "<'row'<'col-md-12't>>" +
        "<'row'<'col-md-3'B><'col-md-3'i><'col-md-6'p>>",
        stateSave: true,
        // Add download buttons
        buttons: [
            { extend: 'csv',
                exportOptions: { rows: '.selectedRow'},
                action: function ( e, dt, node, config ) {
                    // Warn & stop if no selection
                    if (dt.rows('.selectedRow').count() == 0) {
                        return alertNoSelection(hlpElem, hlpDiv);
                    }
                    $.fn.DataTable.ext.buttons.csvHtml5.action.call(this, e, dt, node, config);
                }
            },
            { extend: 'excel',
                exportOptions: { rows: '.selectedRow'},
                action: function ( e, dt, node, config ) {
                    // Warn & stop if no selection
                    if (dt.rows('.selectedRow').count() == 0) {
                        return alertNoSelection(hlpElem, hlpDiv);
                    }
                    $.fn.DataTable.ext.buttons.excelHtml5.action.call(this, e, dt, node, config);
                }
            }
        ],
        // Disable sort on select col - as it does not work
        'columnDefs': [
            { 'orderable': false, 'targets': CheckBoxIdx }
        ]
    });
    return dataTbl
}
