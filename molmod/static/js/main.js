/* Changes may require cache bypass, in Chrome/Mac: shift + cmd + r */
$(document).ready(function() {

    var hlpDiv = $('#selection_error'); // For displaying no-selection warning

    var currPage = $(location).attr('href').split("/").pop();
    switch(currPage) {

        // BLAST PAGE
        case 'blast':
            // Update info on query sequence length
            // after BLAST (page is reloaded)
            updateSeqLength();
            // and when textarea input changes
            $('#sequence_textarea').on('input', function(){
                updateSeqLength();
            });
            $('#clear_all').on('click', function () {
                $('#sequence_textarea').val('');
                $('#min_identity_input').val('');
                $('#min_qry_cover_input').val('');
            });
            // Define columns for BLAST search result table
            var columns = [
                { data: null, orderable: false, defaultContent: '', className: 'select-checkbox'},
                { data: 'asv_id', visible: false },
                { data: 'qacc', className: 'qacc'},
                { data: 'sacc', className: 'details-control asv'},
                { data: 'pident'},
                { data: 'qcovhsp'},
                { data: 'evalue'},
                { data: 'asv_sequence', visible: false }
            ];
            // Make BLAST search result table
            var dTbl = makeDataTbl('blast_run', columns);
            break;

        // FILTER PAGE
        case 'filter':

            // Set format for select2-dropdown boxes
            $.fn.select2.defaults.set('theme', 'bootstrap');
            $.fn.select2.defaults.set('allowClear', true);

            // Make select2-boxes from each <select> element on page
            $('select').each( function () {
                makeSel2drop($(this));
            });

            // Prevent list from opening when clearing selection with 'x'
            $('select').on("select2:clearing", function (evt) {
                $(this).on("select2:opening.cancelOpen", function (evt) {
                    evt.preventDefault();
                    $(this).off("select2:opening.cancelOpen");
                });
            });

            $('#clear_all').on('click', function () {
                $('.select2.form-control').val(null).trigger('change.select2');
            });

            // Define columns for FILTER search result table
            var columns = [
                { data: null, orderable: false, defaultContent: '', className: 'select-checkbox' },
                { data: 'asv_id', visible: false },
                { data: 'asv_tax', className: 'details-control asv' },
                { data: 'gene'},
                { data: 'sub'},
                { data: 'fw_name' },
                { data: 'rv_name' },
                { data: 'asv_sequence', visible: false },
                { data: 'fw_sequence', visible: false },
                { data: 'rv_sequence', visible: false }
            ];
            // Make FILTER search result table
            var dTbl = makeDataTbl('/filter_run', columns);
            break;
    }

    // Show forms after Bootstrap/dataTables/Select2 styling is done
    // to avoid Flash of unstyled content
    $('#rform, #sform').css("visibility", "visible");

    // If we have a (FILTER or BLAST search) result table
    if(typeof dTbl !== "undefined") {

        // Add Select/Deselect-all function to checkbox in table header
        dTbl.on('click', '#select_all', function () {
            if ($('#select_all:checked').val() === 'on')
                dTbl.rows().select();
            else
                dTbl.rows().deselect();
        });

        // Uncheck header checkbox if any row is deselected
        dTbl.on( 'deselect', function () {
            if ($('#select_all:checked').val() === 'on'){
                $('#select_all:checked').prop("checked", false);
            }
        });

        // Remove no-selection warnings when any row is selected
        dTbl.on( 'select', function () {
            if($('#selection_error').hasClass('visHlpDiv')){
                $('#selection_error').removeClass('visHlpDiv');
                $('.table tr td:first-child').removeClass('visHlpElem');
            }
        });

        // Toggle show/hide of ASV sequence as child row
        // when +/- button (or whole cell, actually) is clicked
        dTbl.on('click', 'td.details-control', function () {
            var tr = $(this).closest('tr');
            var row = dTbl.row(tr);
            var data = row.data().asv_sequence;
            // Set no. of empty cells to show before data
            // BLAST
            if (dTbl.table().node().id === 'blast_result_table'){
                var tds = '<tr><td></td><td></td><td class="child" colspan="4">';
            }
            // SEARCH
            else { var tds = '<tr><td></td><td class="child" colspan="5">'; }
            var childRow = $(tds+data+'</td></tr>');
            // Toggle show/hide
            if(row.child.isShown()) {
                row.child.hide();
                tr.removeClass("shown");
            }
            else {
                row.child(childRow).show();
                tr.addClass("shown");
            }
        });

        // Prepare ASV id:s for POST to Bioatlas
        $('#rform').submit(function() {
            // Get selected ASV IDs from table
            var ids = $.map(dTbl.rows({selected: true}).data(), function (item) {
                return item['asv_id']
            });
            // Remove duplicates
            ids = ids.filter(function(item, i, ids) {
                return i == ids.indexOf(item);
            });
            // Add IDs to hidden textarea, one row per ID
            $('#raw_names').val(ids.join('\n'));

            // Warn and abort if no selection has been made in table
            if (!$('#raw_names').val()) {
                $('#selection_error').addClass('visHlpDiv');
                $('.table tr td:first-child').addClass('visHlpElem');
                return false;
            }
        });
    }

});

function makeSel2drop(drop){
    // Makes select2 dropdown from <select> element, eg. target gene
    // and populates this with data from AJAX request to Flask endpoint
    // Uses server-side pagination, i.e. first receives rows 1:x,
    // and then rows x+1:2x when user scrolls past x
    var field = drop.attr('id');
    drop.select2({
        placeholder: 'Select option(s)',
        //Avoid sending requests before user has finished typing search term
        delay: 250,
        // Alt. to delay
        // minimumInputLength: 3 ,
        ajax: {
            url: '/request_drop_options/' + field, // Flask endpoint
            dataType: 'json',
            type: 'POST',
            data: function(params) {
                // console.log(field, params.term, params.page);
                return {
                    // Collect form (or default) values to send to Flask
                    term: params.term || '', // Entered search term
                    page: params.page || 1, // For pagination
                    gene: $('#gene').val() || null, // Selected gene options...
                    sub: $('#sub').val() || null,
                    fw_prim: $('#fw_prim').val() || null,
                    rv_prim: $('#rv_prim').val() || null,
                    kingdom: $('#kingdom').val() || null,
                    phylum: $('#phylum').val() || null,
                    classs: $('#classs').val() || null,
                    oorder: $('#oorder').val() || null,
                    family: $('#family').val() || null,
                    genus: $('#genus').val() || null,
                    species: $('#species').val() || null
                }
            },
            cache: true,
            beforeSend: function(xhr, settings) {
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", $('#csrf_token').val())
                }
            },
            error: function (jqXHR, status, error) {
                // console.log(error);
                $('#filt_err_container').html('Sorry, something unexpected happened during page load. '
                + 'Please <u><a href="' + sbdiContactPage + '">contact SBDI support</a></u> if this error persists.');

                $('.btn').prop('disabled',true);
                return { results: [] };
            }
        }
    });
}

function makeDataTbl(url, columns) {
    // Makes DataTables-table of (FILTER or BLAST search) results
    // received in AJAX request to Flask endpoint
    // Pagination handled by client
    $.fn.dataTable.ext.errMode = 'none';
    var dTbl = $('.table')
        // Handle errors, including serverside BLAST errors causing response
        // to be empty string instead of JSON
        .on('error.dt', function (e, settings, techNote, message) {
            // console.log( 'An error has been reported by DataTables: ', message );
            $('#search_err_container').html('Sorry, something unexpected happened during the search. '
            + 'Please <u><a href="' + sbdiContactPage + '">contact SBDI support</a></u> if this error persists.');

            // Disable Bioatlas POST option and data export
            $("#show_occurrences").prop("disabled",true);
            dTbl.buttons().disable();
        })
        .DataTable({
        deferRender: true, // Process one page at a time
        autoWidth : false, // Respect CSS settings
        ajax: {
            url: url,
            type: 'POST',
            // Disable Bioatlas POST option and data export if no results found
            dataSrc: function ( json ) {
                // If (no errors but) no results were found
                if (json.data.length < 1) {
                    // Disable Bioatlas POST option and data export
                    $("#show_occurrences").prop("disabled",true);
                    dTbl.buttons().disable();
                }
                if (json.data.length > 999) {
                    $('#search_err_container').html('Only the first 1000 rows are shown. '
                      + 'Please, refine your search to make sure results are not truncated.');
                }
                return json.data;
            } ,
            // Include CSRF-token in POST
            data: function () { return $("#sform").serialize(); }
        },
        columns : columns,
        processing: true, // Show 'Loading' indicator
        order: [[2, 'asc']], // Required for non-orderable col 0
        select: { style: 'multi', selector: 'td:nth-child(1)' }, // Checkbox selection
        // Layout: l=Show.., f=Search, tr=table, i=Showing.., p=pagination
        dom: "<'row'<'col-md-4'l><'col-md-8'f>>" +
        "<'row'<'col-md-12't>>" +
        "<'row'<'col-md-3'B><'col-md-3'i><'col-md-6'p>>",
        buttons: [ 'excel', 'csv' ]
    });
    return dTbl;
}

function updateSeqLength() {
    // Counts no. of characters (incl. invisibles) in query sequence(s)
    // and shows this number above textarea
    var seqLength = $('#sequence_textarea').val().length;
    $('#sequence_count').text(seqLength + '/50000 characters');
}
