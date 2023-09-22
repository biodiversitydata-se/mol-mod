/* Changes may require cache bypass, in Chrome/Mac: shift + cmd + r */
$(document).ready(function() {

    switch(page) {

        // BLAST PAGE
        case '/blast':
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
                { data: 'stitle', className: 'details-control asv'},
                { data: 'pident'},
                { data: 'qcovhsp'},
                { data: 'evalue'},
                { data: 'asv_sequence', visible: false }
            ];
            // Make BLAST search result table
            var dTbl = makeResultTbl('blast_run', columns);
            break;

        // FILTER PAGE
        case '/filter':

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
            var dTbl = makeResultTbl('/filter_run', columns);
            break;

        case '/download':
            // Define columns for download table
            var columns = [
                { data: null, orderable: false, defaultContent: '', className: 'select-checkbox' },
                { data: 'annotation_target'},
                { data: 'institution_code'},
                { data : null,
                  render : function ( data, type, row ) {
                        return '<a href="'+iptBaseUrl+'/resource?r='+data.ipt_resource_id+'" target="_blank">'+data.dataset_name+'</a>';
                  },
                  className: 'ds'
                },
                { data : null,
                  render : function ( data, type, row ) {
                      return '<a href="'+data.ipt_download_url+'" target="_blank">'+data.ipt_resource_id+'</a>';
                  }
                 }
            ];
            // Make dataset download table
            var dTbl = makeDownloadTbl('/list_datasets', columns);
            break;

        case '/upload':
            // Note that the actual file upload field (#file) is hidden, and a
            // span element (#file-shown) is shown instead, for styling reasons

            // When a user selects a new file
            // (or, in Chrome, cancels after previously selecting one. No
            // change is detected in Firefox or Safari for the latter case)
            $("#file").change(function(){
                var selFile = $("#file")[0].files[0];
                // If a file was actually selected, show that name in span
                if(typeof selFile !== "undefined") {
                    $("#file-shown").text(selFile.name);
                }
                // If the selection was cancelled after a previous
                // selection was made, Chrome empties the actual input field,
                // so reapply the placeholder in the visble span element
                else {
                    $("#file-shown").text('No file selected');
                }
                // Replace any obsolete msg with original placeholder to avoid flicker
                $("#upload_err_container").html('<span style="visibility:hidden">placeholder</span>');

            });

            $('#uform').on('submit', function() {
                // Checks file size and name against variables in .env file.
                // Additional validation is performed in flask (see forms.py),
                // and size limits are also set in proxy config:
                // https://github.com/biodiversitydata-se/proxy-ws-mol-mod-docker/blob/master/nginx-proxy.confin but this will allow
                // but these checks allow for quicker response for large files.

                // Stop if span is empty, even if the hidden field has data
                // (may happen in Chrome when user hits back + fw buttons),
                // to avoid confusion.
                if ($('#file-shown').text() === 'No file selected') {
                    $("#upload_err_container").html('Please select a file!');
                    return false;
                }

                if ($("#file").val()) {

                    var selFile = $('#file')[0].files[0];

                    // Check size
                    if( selFile.size > maxFileSize ) {
                        $('#upload_err_container').html('The file you tried to upload was larger than the ' + maxFileSize / (1024 * 1024) + ' MB we can deal with here. '
                        + 'Please <a href="' + sbdiContactPage + '">contact SBDI support</a>, and we will find another option for you.');
                        return false;
                    }
                    // Check extension
                    var valExtArr = validExtensions.split(', ');
                    var nmParts = selFile.name.split('.');
                    // If no extension
                    if (nmParts.length < 2){
                        $("#upload_err_container").html('Select a valid file (' + validExtensions + '), please!');
                        return false;
                    }
                    // Catches single extension part, e.g. xlsx
                    var sngExt = nmParts[nmParts.length - 1];
                    // Catches double extension parts, e.g. tar.gz
                    var dblExt = nmParts[nmParts.length - 2] + '.' + sngExt;
                    // If neither matches allow extensions
                    if ((valExtArr.indexOf(sngExt.toLowerCase()) == -1) &&
                       (valExtArr.indexOf(dblExt.toLowerCase()) == -1)) {
                        $("#upload_err_container").html('Select a valid file (' + validExtensions + '), please!');
                        return false;
                    }
                }
                return true;
            });

    }

    // Show forms after Bootstrap/dataTables/Select2 styling is done
    // to avoid Flash of unstyled content
    $('#rform, #sform').css("visibility", "visible");

    // If we have a DataTable
    if(typeof dTbl !== "undefined") {

        // Add Select/Deselect-all function to checkbox in table header
        dTbl.on('click', '#select_all', function () {
            if ($('#select_all:checked').val()  === 'on')
                dTbl.rows({search: 'applied'}).select(); // Only select filtered records, if filter is applied
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
            $('#dtbl_err_container').addClass('hiddenElem');
            $('.table tr td:first-child').removeClass('visHlpElem');
        });

        if (page === '/blast' || page === '/filter') {
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
            $('#rform').on('submit', function() {
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
                    $('#dtbl_err_container').removeClass('hiddenElem');
                    $('#dtbl_err_container').html('Please, select at least one row. ');
                    $('.table tr td:first-child').addClass('visHlpElem');
                    return false;
                }
            });
        }

        else if (page === '/download') {
            $('#rform').on('submit', function() {
                // Get selected IPT resource IDs from table
                var ids = $.map(dTbl.rows({selected: true}).data(), function (item) {
                    return item['ipt_resource_id']
                });

                // Warn and abort if no selection has been made in table
                if (ids.length == 0) {
                    $('#dtbl_err_container').removeClass('hiddenElem');
                    $('#dtbl_err_container').html('Please, select at least one row. ');
                    $('.table tr td:first-child').addClass('visHlpElem');
                    return false;
                }

                function downloadWithDelay(index) {
                // Downloads selected datasets

                    if (index >= ids.length) {
                        return;
                    }

                    var downloadLink = iptBaseUrl + '/archive.do?r=' + ids[index];

                    // Create a hidden anchor element and trigger a click to download
                    var hiddenAnchor = document.createElement('a');
                    hiddenAnchor.href = downloadLink;
                    hiddenAnchor.style.display = 'none'; // Hide the anchor
                    document.body.appendChild(hiddenAnchor);
                    hiddenAnchor.click();
                    document.body.removeChild(hiddenAnchor);

                    // Delay before starting the next download
                    // (to allow multiple downloads in Chrome)
                    setTimeout(function () {
                        downloadWithDelay(index + 1);
                    }, 1000); // Adjust the delay duration (in milliseconds) as needed
                }

                // Start the download process from the first link
                downloadWithDelay(0);

                return false;


            });
        }
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
            // Add the CSRF token to HTTP header
            beforeSend: function(xhr, settings) {
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", $('#csrf_token').val())
                }
            },
            error: function(err, errText, errType) {
                // If user types too fast for select2
                if (   err.readyState == 0
                    && err.status == 0
                    && err.statusText == "abort"
                    && errText == "abort"
                    && errType == "abort")
                {
                    //Log but do nothing!
                    console.log('Select2.js fast type-ahead error condition encountered and handled properly');
                } else {
                    //Process proper errors
                    $('#filt_err_container').removeClass('hiddenElem');
                    $('#filt_err_container').html('Sorry, something unexpected happened during page load. '
                    + 'Please, <a href="' + sbdiContactPage + '">contact SBDI support</a> if this error persists.');

                    $('.btn').prop('disabled',true);
                    return { results: [] };
                }
            }
        }
    });
}

function makeResultTbl(url, columns) {
    // Makes DataTables-table of (FILTER or BLAST search) results
    // received in AJAX request to Flask endpoint
    // Pagination handled by client
    $.fn.dataTable.ext.errMode = 'none';
    var dTbl = $('.table')
        // Handle errors, including serverside BLAST errors causing response
        // to be empty string instead of JSON
        .on('error.dt', function (e, settings, techNote, message) {
            // console.log( 'An error has been reported by DataTables: ', message );
            $('#dtbl_err_container').removeClass('hiddenElem');
            $('#dtbl_err_container').html('Sorry, something unexpected happened during the search. '
            + 'Please <a href="' + sbdiContactPage + '">contact SBDI support</a> if this error persists.');

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
                    $('#dtbl_err_container').removeClass('hiddenElem');
                    $('#dtbl_err_container').html('Please note that only the first 1000 hits are returned. '
                      + 'Refine your search to make sure results are not truncated.');
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
        dom: "<'row'<'col-md-5'l><'col-md-7'f>>" +
        "<'row'<'col-md-12't>>" +
        "<'row'<'col-md-2'B><'col-md-5'i><'col-md-5'p>>",
        buttons: [ 'excel', 'csv' ]
    });
    return dTbl;
}

function makeDownloadTbl(url, columns) {
    $.fn.dataTable.ext.errMode = 'none';
    var dTbl = $('.table')
        // Handle errors causing response to be empty string instead of JSON
        .on('error.dt', function (e, settings, techNote, message) {
            // console.log( 'An error has been reported by DataTables: ', message );
            $('#dtbl_err_container').removeClass('hiddenElem');
            $('#dtbl_err_container').html('Sorry, something unexpected happened during the search. '
            + 'Please <a href="' + sbdiContactPage + '">contact SBDI support</a> if this error persists.');

            // Disable dataset download and list export options
            $("#show_occurrences").prop("disabled",true);
            dTbl.buttons().disable();
        })
        .DataTable({
        //pageLength: 100,
        deferRender: true, // Process one page at a time
        autoWidth : false, // Respect CSS settings
        ajax: {
            url: url,
            type: 'GET',
            dataSrc: function ( json ) {
                // If (no errors but) no results were found
                if (json.data.length < 1) {
                    // Disable dataset download and list export options
                    $("#download").prop("disabled",true);
                    dTbl.buttons().disable();
                }
                return json.data;
            }
        },
        columns : columns,
        processing: true, // Show 'Loading' indicator
        order: [], // Required for non-orderable col 0
        select: { style: 'multi', selector: 'td:nth-child(1)' }, // Checkbox selection
        // Layout: l=Show.., f=Search, tr=table, i=Showing.., p=pagination
        dom: "<'row'<'col-md-5'l><'col-md-7'f>>" +
        "<'row'<'col-md-12't>>" +
        "<'row'<'col-md-2'B><'col-md-5'i><'col-md-5'p>>",
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
