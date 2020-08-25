/* Changes may require cache bypass, in Chrome/Mac: shift + cmd + r */
/* Perhaps change later to only run if BLAST or API search */

$(document).ready(function() {
    /* Code to run when page has finished loading */

    // Get div holding no-selection error msg (to make visible when needed)
    var hlpDiv = $('#selection_error');

    // Get page name from URL
    var currPage = $(location).attr('href').split("/").pop();
    switch(currPage) {

        // BLAST PAGE
        case 'blast':
            // SEARCH FORM
            // Get input seq length for display
            $('#sequence_textarea').on('input', function(){
                $('#sequence_count').text($(this).val().length);
            });
            // RESULT FORM
            // Get tbl col holding checkboxes (to highlight when needed)
            var hlpElem = selectHlpElem(6);
            // Convert BLAST results to jQuery dataTable
            var dataTbl = makeDataTbl(5, hlpElem, hlpDiv);
            break;

        // API PAGE
        case 'search_api':
            // SEARCH FORM
            // Set format for select2-dropdown boxes
            $.fn.select2.defaults.set("theme", "bootstrap");

            // Make select2-dropdowns for gene & primers
            var geneSelS2 = $('#gene_sel').select2({
                placeholder: 'Select target gene(s)'
            });
            var fwSelS2 = $('#fw_prim_sel').select2({
                placeholder: 'Select forward primer(s)'
            });
            var rvSelS2 = $('#rv_prim_sel').select2({
                placeholder: 'Select reverse primer(s)'
            });

            function filterPrimerOptions (dir) {
                /* Uses AJAX to update options in primer dropdowns
                in response to selection in gene dropdown, by getting
                filtered DB/API data from Flask endpoint, without reloading page */

                // Get selected gene(s)
                var gene = geneSelS2.val();

                // Select fw/rv primer dropdown
                if (dir === 'fw') { var primDrop = fwSelS2; }
                else { var primDrop = rvSelS2; }

                // If no selected gene, get all primers
                if (gene.length === 0) { gene = 'all'; }

                // Make AJAX request for JSON of filtered primers
                $.getJSON(
                    // Set Flask endpoint
                    '/get_primers' + '/' + gene + '/' + dir,
                    function(data) {
                        // Save current selection
                        currSel = primDrop.val();
                        // Remove old options
                        primDrop.find('option').remove();
                        // Add option for each item in returned JSON object
                        $.each(data, function(i,e) {
                            primDrop.append('<option value="' + e.name + '">' + e.display + '</option>');
                        });
                        // Reapply old selection
                        // (otherwise existing selection disappears if user adds new gene)
                        primDrop.val(currSel);
                    }
                );
            };

            // Filter primer options (i.e. even if gene selection has not changed)
            // Needed to 'keep' filters after submit ('Search')
            filterPrimerOptions('fw');
            filterPrimerOptions('rv');

            // Re-filter primer options when genes are selected
            geneSelS2.change(function () {
                filterPrimerOptions('fw');
                filterPrimerOptions('rv');
            });

            // RESULT FORM
            // Get tbl col holding checkboxes (to highlight when needed)
            var hlpElem = selectHlpElem(6);
            // Convert results to jQuery dataTable
            var dataTbl = makeDataTbl(5, hlpElem, hlpDiv);
            break;

                      // Neither BLAST nor API
        default:
            break;
    }

    // Only show forms after Bootstrap/dataTables/Select2 styling is done
    // to avoid flash of unstyled content (FOUC)
    $('#rform').css("visibility", "visible");
    $('#sform').css("visibility", "visible");

    // If BLAST or API result form
    if(typeof dataTbl !== "undefined") {
        var asvBoxes = dataTbl.$('.asv_id');

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
    }

    // When table header (select-all) checkbox is changed
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

function selectHlpElem(childColIdx){
    var hlpElem = $('#result_table tr td:nth-child(' + childColIdx + '), #result_table tr th:nth-child(' + childColIdx + ')');
    return hlpElem;
}

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
