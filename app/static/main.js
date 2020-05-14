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
function alertNoSelection(tblName, cno, eBox) {
    // Colour checkbox column
    // $(tbl+'tr > td:nth-child('+cno+'), '+tbl+' tr>th:nth-child('+cno+')').attr('bgcolor', '#f2e4e4');
    $('#'+tblName+' tr > td:nth-child('+cno+'), '+tblName+' tr>th:nth-child('+cno+')').attr('bgcolor', '#f2e4e4');
    // Show error msg
    eBox.attr('style', 'text-align:right; color:#aa4442');
    // Stop further action
    return false;
}
