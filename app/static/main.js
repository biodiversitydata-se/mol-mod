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
