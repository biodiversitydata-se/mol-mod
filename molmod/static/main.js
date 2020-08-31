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
        if(typeof blastResults !== "undefined") {
            var columns = [
                {'data': ''},
                {'data': 'asv_id'},
                {'data': 'qacc'},
                {'data': 'sacc'},
                {'data': 'pident'},
                {'data': 'qcovhsp'},
                {'data': 'evalue'}
            ];
            // Make dataTable
            var dTbl = makeDataTbl('blast_result_table', blastResults, columns);
        }
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

                var url = 'http://localhost:3000/app_filter_' + dir + '_primers';

                // If no selected gene, get all primers
                if (gene.length !== 0) {
                    url = url + '?gene=in.(' + gene + ')';
                }

                // Make AJAX request for JSON of filtered primers
                $.getJSON(
                    url,
                    function(data) {
                        // Save old selection & options
                        var oldSel = primDrop.val();
                        var oldOpt = primDrop.find('option:selected').clone();
                        // Remove old options
                        primDrop.find('option').remove();
                        // data format: [{"display":"ITS1F: CTTGGTCATTTAGAGGAAGTAA","name":"ITS1F"}]
                        // Add option for each item in returned JSON object
                        var newOpt = []
                        $.each(data, function(i,e) {
                            primDrop.append('<option value="' + e.name + '">' + e.display + '</option>');
                            newOpt.push(e.name);
                        });
                        // Uncomment to keep primer selection when primers are selected
                        // But then perhaps change search to primer=x OR gene=y instead of AND
                        // $.each(oldOpt, function(i,e) {
                        //     if (newOpt.indexOf(e.value) === -1){
                        //         primDrop.append(e);
                        //     }
                        // });
                        // Reapply old selection
                        // (otherwise existing selection disappears if user adds new gene)
                        primDrop.val(oldSel);
                    }
                );
            };

            // Filter primer options if a gene was selected before reload/submit
            if (geneSelS2.val() != ''){
                // alert('gene selected');
                filterPrimerOptions('fw');
                filterPrimerOptions('rv');
            }

            // Re-filter primer options when genes are selected
            geneSelS2.change(function () {
                // alert('gene changed');
                filterPrimerOptions('fw');
                filterPrimerOptions('rv');
            });

            // RESULT FORM            // Get tbl col holding checkboxes (to highlight when needed)
            // Convert results to jQuery dataTable
            if(typeof apiResults !== "undefined") {
                var columns = [
                    {'data': ''},
                    {'data': 'asv_id'},
                    {'data': 'asv_tax'},
                    {'data': 'gene'},
                    {'data': 'sub'},
                    {'data': 'fw_name'},
                    {'data': 'rv_name'}
                ];
                // alert(JSON.stringify(apiResults));
                var dTbl = makeDataTbl('api_result_table', apiResults, columns);
            }
            break;


        // Neither BLAST nor API
        default:
            break;
    }

    // Only show forms after Bootstrap/dataTables/Select2 styling is done
    // to avoid flash of unstyled content (FOUC)
    $('#rform').css("visibility", "visible");
    $('#sform').css("visibility", "visible");

    // ANY RESULT FORM
    if(typeof dTbl !== "undefined") {

        // Add Select-all function to hdr checkbox
        dTbl.on('click', '#select_all', function () {
            if ($('#select_all:checked').val() === 'on')
                dTbl.rows().select();
            else
                dTbl.rows().deselect();
        });

        // Uncheck hdr checkbox if any row is unselected
        dTbl.on( 'deselect', function () {
            if ($('#select_all:checked').val() === 'on'){
                $('#select_all:checked').prop("checked", false);
            }
        });

        // Remove no-selection warnings if they exist
        dTbl.on( 'select', function () {
            if($('#selection_error').hasClass('visHlpDiv')){
                $('#selection_error').removeClass('visHlpDiv');
                $('#result_table tr td:first-child').removeClass('visHlpElem');
            }
        });
        $('#rform').submit(function() {
            // Get selected ASV IDs
            var ids = $.map(dTbl.rows('.selected').data(), function (item) {
                return item['asv_id']
            });
            // Remove duplicates
            ids = ids.filter(function(item, i, ids) {
                return i == ids.indexOf(item);
            });
            // Add IDs to textarea
            $('#raw_names').val(ids.join('\n'));

            // Warn if no selection
            if (!$('#raw_names').val()) {
                $('#selection_error').addClass('visHlpDiv');
                $('#result_table tr td:first-child').addClass('visHlpElem');
                return false;
            }
        });
    }

});

// Make jQuery dataTable from html table
// hlpElem/Div needs to be passed here
function makeDataTbl(table_id, data, columns) {
    var dTbl = $('#'+table_id).DataTable( {
        autoWidth : false,
        data : data,
        columns : columns,
        deferRender: true,
        columnDefs: [ {
            targets: 0,
            data: null,
            defaultContent: '',
            orderable: false,
            className: 'select-checkbox',
        },
        {
            targets:1,
            visible: false}],
            select: {
                style:    'multi',
                selector: 'td:first-child'
        },
        order: [[ 3, 'asc' ]],
        // Modify layout of dataTable components:
        // l=Show.., f=Search, tr=table, i=Showing.., p=pagination
        dom: "<'row'<'col-md-4'l><'col-md-8'f>>" +
        "<'row'<'col-md-12't>>" +
        "<'row'<'col-md-3'B><'col-md-3'i><'col-md-6'p>>",
        buttons: [
            'copy', 'excel', 'csv'
        ]
    });

    return dTbl;
}
