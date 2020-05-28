/* May require cache bypass in Chrome/Mac: shift + cmd + r */

// Add checked ids to hidden textarea - for POST to SBDI
function addCheckedToArea(asvBoxes, sbdiArea) {
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
    sbdiArea.val(ids.join('\n'));
}

// Warn & stop if no selection for SBDI submission / download
function alertNoSelection(hlpElem, hlpDiv) {
    hlpDiv.addClass('visHlpDiv');
    hlpElem.addClass('visHlpElem');
    return false;
}

function makeDataTbl(htmlTbl, CheckBoxIdx) {
    var dataTbl = htmlTbl.dataTable({
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
