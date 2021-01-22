/* Changes may require cache bypass, in Chrome/Mac: shift + cmd + r */
$(document).ready(function() {
    var hlpDiv = $('#selection_error'); // For no-selection error

    var currPage = $(location).attr('href').split("/").pop();
    switch(currPage) {

        // BLAST PAGE
        case 'blast':
            $('#sequence_textarea').on('input', function(){
                $('#sequence_count').text($(this).val().length+'/500000 characters');
            });
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
            var dTbl = makeDataTbl('blast_run', columns);
            break;

        // API SEARCH PAGE
        case 'filter':

            // Set format for select2-dropdown boxes
            $.fn.select2.defaults.set('theme', 'bootstrap');
            // $.fn.select2.defaults.set('closeOnSelect', false);
            $.fn.select2.defaults.set('allowClear', true);

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

            var columns = [
                { data: null, orderable: false, defaultContent: '', className: 'select-checkbox' },
                { data: 'asv_id', visible: false },
                { data: 'asv_tax', className: 'details-control asv' },
                { data: 'gene'},
                { data: 'sub'},
                // { data: 'fw_name', className: 'details-control fwPrim' },
                // { data: 'rv_name', className: 'details-control rvPrim' },
                { data: 'fw_name' },
                { data: 'rv_name' },
                { data: 'asv_sequence', visible: false },
                { data: 'fw_sequence', visible: false },
                { data: 'rv_sequence', visible: false }
            ];
            var dTbl = makeDataTbl('/filter_run', columns);

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
    var field = drop.attr('id');
    drop.select2({
        placeholder: 'Select option(s)',
        delay: 250,
        // minimumInputLength: 3 ,
        ajax: {
            url: '/request_drop_options/' + field,
            dataType: 'json',
            type: 'POST',
            data: function(params) {
                console.log(field, params.term, params.page);
                return {
                    term: params.term || '',
                    page: params.page || 1,
                    gene: $('#gene').val() || null,
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
            }
        }
    });
}

// Make dataTable
function makeDataTbl(url, columns) {
    $.fn.dataTable.ext.errMode = 'none';
    var dTbl = $('.table')
        .on('error.dt', function (e, settings, techNote, message) {
            console.info( 'An error has been reported by DataTables: ', message );
            $('#flash_container').html('Sorry, something unexpected happened during the search. '
              + 'Please, contact support if this error persists.');
            $("#show_occurrences").prop("disabled",true);
            dTbl.buttons().disable();
        })
        .DataTable({
        deferRender: true, // Process one page at a time
        autoWidth : false, // Respect CSS settings
        ajax: {
            url: url,
            type: 'POST',
            dataSrc: function ( json ) {
                if (json.data.length < 1) {
                    $("#show_occurrences").prop("disabled",true);
                    dTbl.buttons().disable();
                }
                return json.data;
            } ,
            data: function () { return $("#sform").serialize(); } // Includes CSRF-token
        },
        columns : columns,
        processing: true, // Add indicator
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
