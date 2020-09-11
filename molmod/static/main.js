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

            // Make select2-dropdowns
            var geneSelS2 = $('#gene_sel').select2({
                placeholder: 'Select target gene'
            });
            var fwSelS2 = $('#fw_prim_sel').select2({
                placeholder: 'Select forward primer'
            });
            var rvSelS2 = $('#rv_prim_sel').select2({
                placeholder: 'Select reverse primer'
            });
            var kingdomSelS2 = $('#kingdom_sel').select2({
                placeholder: 'Select kingdom'
            });
            var phylumSelS2 = $('#phylum_sel').select2({
                placeholder: 'Select phylum'
            });
            var classSelS2 = $('#class_sel').select2({
                placeholder: 'Select class'
            });
            var orderSelS2 = $('#order_sel').select2({
                placeholder: 'Select order'
            });

            // Filter every dropdown box on selection(s) made in other boxes
            $('.select2').on('change', function () {
                $( '.select2.form-control:not( #'+$(this).attr('id')+')').each( function () {
                    filterDropOptions($(this).attr('id'));
                });
            });

            // Re-apply filter(s) on reload
            var totSel = 0;
            //Sum no. of selections over all boxes
            $('.select2.form-control').each( function () {
                totSel = totSel + $(this).select2('data').length;
            });
            // Re-filter all boxes, if at least one selection was made
            if (totSel>0){
                $( '.select2.form-control').each( function () {
                    filterDropOptions($(this).attr('id'));
                });
            }

            function getColNames(dropID){
                /* Translates select2-box ID to corresponding API view
                columns used in filter and display */
                var name, display;
                switch(dropID){
                    case 'fw_prim_sel':
                        name = 'fw_name';
                        display = 'fw_display';
                        break;
                    case 'rv_prim_sel':
                        name = 'rv_name';
                        display = 'rv_display';
                        break;
                    case 'order_sel':
                        name = 'oorder';
                        display = 'oorder';
                        break;
                    default:
                        name = dropID.replace("_sel", "");
                        display = name;
                        break;
                    }
                var item = {};
                item['name'] = name;
                item['display'] = display;
                return item;
            }

            function filterDropOptions(dropID){
                var url = 'http://localhost:3000/app_filter_mixs_tax';
                // For every other dropdown box (= row filter source)
                $('.select2.form-control:not( #' + dropID + ')').each( function () {
                    var fltDrop = $( this );
                    // If some selection has been made
                    if (fltDrop.val() != ''){
                        // Get corresponding view column
                        var filtCol = getColNames(fltDrop.attr('id'))['name'];
                        // Prepend with '?' if first filter to be added
                        if (url.charAt(url.length-1) !== '?') url = url + '?';
                        // Add selection as row filter to URL
                        url = url + '&' + filtCol + '=in.(' + fltDrop.val() + ')';
                    }
                });
                // Get view col names for focal dropdown box
                var nameCol = getColNames(dropID)['name'];
                var dispCol = getColNames(dropID)['display'];
                // Prepend with '?' if no row filters were added above
                if (url.indexOf('?') < 0) url += '?';
                // Exclude empty options, add column filter and sort order
                url = url + nameCol + '=not.eq.' + '&select=' + nameCol + ',' + dispCol + '&order=' + dispCol;
                // Make API request
                $.getJSON(url, function(data) {
                    var drop = $('#' + dropID);
                    // Save old selection(s)
                    var oldSel = drop.val();
                    // Remove old options
                    drop.find('option').remove();
                    // Add option for each unique item in returned JSON object
                    var lookup = {};
                    $.each(data, function(i,e) {
                        // If new item
                        if (!(e[dispCol] in lookup)) {
                            lookup[e[dispCol]] = 1;
                            drop.append('<option value="' + e[nameCol] + '">' + e[dispCol] + '</option>');
                        }
                    });
                    // Reapply old selection
                    drop.val(oldSel);
                });
            }

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

// Make jQuery dataTable
function makeDataTbl(table_id, data, columns) {
    // Set cols for seq expansion and sort order
    // BLAST
    if ( table_id === 'blast_result_table' ) {
        var detNo = 3; var ordNo = 2;
    }
    // API SEARCH
    else { var detNo = 2; var ordNo = 2; }
    var dTbl = $('#'+table_id).DataTable( {
        // Respect CSS settings
        autoWidth : false,
        data : data,
        // Process one page at a time, for speed
        deferRender: true,
        columns : columns,
        columnDefs: [
            { targets: 0, defaultContent: '', orderable: false,
            className: 'select-checkbox' },
            // Add control for sequence expansion
            { targets: detNo, className: 'details-control' },
            // Hide ID and subject seq
            { targets:[1,7], visible: false },
        ],
        // Use checkbox col for row selection
        select: { style: 'multi', selector: 'td:nth-child(1)' },
        order: [[ ordNo, 'asc' ]],
        // Set table layout:
        // l=Show X.., f=Search, tr=table, i=Showing.., p=pagination
        dom: "<'row'<'col-md-4'l><'col-md-8'f>>" +
        "<'row'<'col-md-12't>>" +
        "<'row'<'col-md-3'B><'col-md-3'i><'col-md-6'p>>",
        buttons: [
            'excel', 'csv'
        ]
    });
    return dTbl;
}
