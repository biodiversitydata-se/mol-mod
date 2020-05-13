
// Require at least one selected row
function requireRowSelection(cno) {
    if (!$('#raw_names').val()) {
        // Highlight checkbox column
        $('#result_table tr > td:nth-child('+cno+'), #result_table tr>th:nth-child('+cno+')').attr('bgcolor', '#f2e4e4');
        // Show error msg
        $('#asv_error').attr('style', 'text-align:right; color:#aa4442');
        // Stop submission
        return false;
    }
}
