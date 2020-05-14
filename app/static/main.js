function mtest() {
    alert('då');
    // alert(value);
}

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
//
// Warn & stop if no selection for SBDI submission / download
function alertNoSelection(cno) {
    // Colour checkbox column
    $('#result_table tr > td:nth-child('+cno+'), #result_table tr>th:nth-child('+cno+')').attr('bgcolor', '#f2e4e4');
    // Show error msg
    $('#asv_error').attr('style', 'text-align:right; color:#aa4442');
    // Stop further action
    return false;
}
