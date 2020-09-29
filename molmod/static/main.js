/* Changes may require cache bypass, in Chrome/Mac: shift + cmd + r */
$(document).ready(function() {
    var hlpDiv = $('#selection_error'); // For no-selection error

    var currPage = $(location).attr('href').split("/").pop();
    switch(currPage) {

        // BLAST PAGE
        case 'blast':
            var columns = [
                {'data': ''},         // 0. Checkbox
                {'data': 'asv_id'},     // 1. Hidden ID
                {'data': 'qacc'},       // 2.
                {'data': 'sacc'},       // 3. Expandable
                {'data': 'pident'},     // 4.
                {'data': 'qcovhsp'},    // 5.
                {'data': 'evalue'},     // 6.
                {'data': 'asv_sequence'}// 7. Hidden seq
            ];
            var dTbl = makeDataTbl('blast_result_table', columns);
            break;

        // API SEARCH PAGE
        case 'search':

            // Set format for select2-dropdown boxes
            $.fn.select2.defaults.set('theme', 'bootstrap');
            // $.fn.select2.defaults.set('closeOnSelect', false);
            $.fn.select2.defaults.set('allowClear', true);

            // // Make select2-dropdowns
            // var geneSelS2 = $('#gene_sel').select2({
            //     placeholder: 'Select target gene',
            // });
            // var fwSelS2 = $('#fw_prim_sel').select2({
            //     placeholder: 'Select forward primer',
            // });
            // var rvSelS2 = $('#rv_prim_sel').select2({
            //     placeholder: 'Select reverse primer',
            // });

            $('select.taxon').each( function () {
                makeSel2drop($(this));
            });

            // Prevent opening when clearing selection
            $('select.taxon').on("select2:clearing", function (evt) {
                $(this).on("select2:opening.cancelOpen", function (evt) {
                    evt.preventDefault();
                    $(this).off("select2:opening.cancelOpen");
                });
            });

            $('#clear_all').on('click', function () {
                $('.select2.form-control').val(null).trigger('change.select2');
            });

            // RESULT FORM
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
            var dTbl = makeDataTbl('api_result_table', columns);

            break;
    }

    // Only show after Bootstrap/dataTables/Select2 styling
    $('#rform, #sform').css("visibility", "visible");

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
// Make select2 dropdowns
function makeSel2drop(drop){
    var rank = drop.attr('id');
    drop.select2({
        placeholder: 'Select taxa',
        delay: 250,
        // minimumInputLength: 3 ,
        ajax: {
            url: '/request_tax_options/'+rank,
            dataType: 'json',
            type: 'POST',
            data: function(params) {
                return {
                    term: params.term || '',
                    page: params.page || 1,
                    kingdom: $('#kingdom').val().toString(),
                    phylum: $('#phylum').val().toString(),
                    classs: $('#classs').val().toString(),
                    oorder: $('#oorder').val().toString(),
                    family: $('#family').val().toString(),
                    genus: $('#genus').val().toString(),
                    species: $('#species').val().toString()
                }
            },
            cache: true,
            beforeSend: function(xhr, settings) {
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", $('#csrf_token').val())
                }
            },
            processResults: function (data) { // select2 format
                return { results: data };
            }
        }
    });
}

// Make dataTable
function makeDataTbl(table_id, columns) {
    $.fn.dataTable.ext.errMode = 'none';
    // BLAST
    if ( table_id === 'blast_result_table' ) {
        var detNo = 3; var ordNo = 2; var url = '/blast_run';
    }
    // API SEARCH
    else {
        var detNo = 2; var ordNo = 2; var url = '/search_run';
    }
    var dTbl = $('#'+table_id)
        .on('error.dt', function (e, settings, techNote, message) {
            console.log( 'An error has been reported by DataTables: ', message );
            $('#flash_container').html('Sorry, the query was not successful. Please, contact support if this error persists.');
        })
        .DataTable({
        deferRender: true, // Process one page at a time
        autoWidth : false, // Respect CSS settings
        ajax: {
            url: url,
            type: 'POST',
            data: function () { return $("#sform").serialize(); } // Includes CSRF-token
        },
        columns : columns,
        columnDefs: [
            { targets: 0, orderable: false, defaultContent: '', className: 'select-checkbox' },
            { targets: detNo, className: 'details-control' }, // Seq expansion
            { targets:[1,7], visible: false }, // Hidden ID & seq
        ],
        select: { style: 'multi', selector: 'td:nth-child(1)' }, // Checkbox selection
        order: [[ ordNo, 'asc' ]],
        // Layout: l=Show.., f=Search, tr=table, i=Showing.., p=pagination
        dom: "<'row'<'col-md-4'l><'col-md-8'f>>" +
        "<'row'<'col-md-12't>>" +
        "<'row'<'col-md-3'B><'col-md-3'i><'col-md-6'p>>",
        buttons: [ 'excel', 'csv' ]
    });
    return dTbl;
}
