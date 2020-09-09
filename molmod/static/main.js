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
                    {'data': null},         // 0. Checkbox
                    {'data': 'asv_id'},     // 1. Hidden ID
                    {'data': 'qacc'},       // 2.
                    {'data': 'sacc'},       // 3. Expandable
                    {'data': 'pident'},     // 4.
                    {'data': 'qcovhsp'},    // 5.
                    {'data': 'evalue'},     // 6.
                    {'data': 'asv_sequence'}// 7. Hidden seq
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
            var kingdomSelS2 = $('#kingdom_sel').select2({
                placeholder: 'Select kingdom(s)'
            });
            var phylumSelS2 = $('#phylum_sel').select2({
                placeholder: 'Select phylum/phyla'
            });


            function filterDropOptions (filter, childDrop, apiView) {
                var selParent = eval(filter + 'SelS2').val();
                var url = 'http://localhost:3000/' + apiView;
                // Filter url with selected parent(s)
                if (selParent.length !== 0) {
                    url = url + '?' + filter + '=in.(' + selParent + ')';
                }

                // Make AJAX request for JSON of filtered primers
                $.getJSON(
                    url,
                    function(data) {
                        // Save old selection & options
                        var oldSel = childDrop.val();
                        var oldOpt = childDrop.find('option:selected').clone();
                        // Remove old options
                        childDrop.find('option').remove();
                        // data format: [{"display":"ITS1F: CTTGGTCATTTAGAGGAAGTAA","name":"ITS1F"}]
                        // Add option for each item in returned JSON object
                        var newOpt = []
                        $.each(data, function(i,e) {
                            childDrop.append('<option value="' + e.name + '">' + e.display + '</option>');
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
                        childDrop.val(oldSel);
                    }
                );
            };

            // Filter primer options if a gene was selected before reload/submit
            if (geneSelS2.val() != ''){
                // alert('gene selected');
                filterDropOptions ('gene', fwSelS2, 'app_filter_fw_primers');
                filterDropOptions ('gene', rvSelS2, 'app_filter_rv_primers');
            }
            // Filter primer options when genes are selected
            geneSelS2.change(function () {
                // alert('gene changed');
                filterDropOptions ('gene', fwSelS2, 'app_filter_fw_primers');
                filterDropOptions ('gene', rvSelS2, 'app_filter_rv_primers');
            });
            // Dito for kingdom/phyla
            if (kingdomSelS2.val() != ''){
                filterDropOptions ('kingdom', phylumSelS2, 'app_filter_phyla');
            }
            kingdomSelS2.change(function () {
                filterDropOptions ('kingdom', phylumSelS2, 'app_filter_phyla');
            });


            // RESULT FORM
            // Convert results to jQuery dataTable
            if(typeof apiResults !== "undefined") {
                var columns = [
                    {'data': null},         // 0. Checkbox
                    {'data': 'asv_id'},     // 1. Hidden ID
                    {'data': 'asv_tax'},    // 2. Expandable
                    {'data': 'gene'},       // 3.
                    {'data': 'sub'},        // 4.
                    {'data': 'fw_name'},    // 5.
                    {'data': 'rv_name'},    // 6.
                    {'data': 'asv_sequence'}// 7. Hidden seq
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
                $('.table tr td:first-child').removeClass('visHlpElem');
            }
        });

        // Toggle show/hide of ASV sequence as child row
        dTbl.on('click', 'td.details-control', function () {
            var tr = $(this).closest('tr');
            var row = dTbl.row(tr);
            var data = row.data();
            // Set no. of empty cells to show before seq, depending on table type
            if (dTbl.table().node().id === 'blast_result_table'){
                var tds = '<tr><td></td><td></td><td colspan="4">';
            }
            else { var tds = '<tr><td></td><td colspan="5">'; }
            var childRow = $(tds+data.asv_sequence+'</td></tr>');
            // Toggle
            if(row.child.isShown()) {
                row.child.hide();
                tr.removeClass("shown");
            }
            else {
                row.child(childRow).show();
                tr.addClass("shown");
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
                $('.table tr td:first-child').addClass('visHlpElem');
                return false;
            }
        });
    }

});

// Make jQuery dataTable from html table
function makeDataTbl(table_id, data, columns) {
    if ( table_id === 'blast_result_table' ) {
        var detNo = 3; var ordNo = 3;
    }
    else { var detNo = 2; var ordNo = 2; }
    var dTbl = $('#'+table_id).DataTable( {
        autoWidth : false,
        data : data,
        deferRender: true,
        columns : columns,
        columnDefs: [
            { targets: 0, defaultContent: '', orderable: false,
              className: 'select-checkbox' },
            { targets: detNo, className: 'details-control' },
            { targets:[1,7], visible: false },
        ],
        select: { style: 'multi', selector: 'td:nth-child(1)' },
        order: [[ ordNo, 'asc' ]],
        // Modify layout of dataTable components:
        // l=Show.., f=Search, tr=table, i=Showing.., p=pagination
        dom: "<'row'<'col-md-4'l><'col-md-8'f>>" +
        "<'row'<'col-md-12't>>" +
        "<'row'<'col-md-3'B><'col-md-3'i><'col-md-6'p>>",
        buttons: [
            'excel', 'csv'
        ]
    });

    return dTbl;
}
