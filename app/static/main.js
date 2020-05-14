// function xtest() {
//     alert('xtest');
// }
//
//
// // Add checked ids to hidden textarea - for POST to SBDI
// function addCheckedToArea(obj, table) {
//     // alert('adding checked');
//     var ids = [1,2,3];
//     // Add checked ids to list
//     $(cbox, tbl).map(function () {
//         ids.push(this.id);
//     });
//     alert(ids);
//     // // Remove duplicates
//     // ids = ids.filter(function(item, i, ids) {
//     //     return i == ids.indexOf(item);
//     // });
//     // // Add ids to textarea
//     // $('#raw_names').val(ids.join('\n'));
// }
//
// // Require at least one selected row
// function requireSelection(cno) {
//     if (!$('#raw_names').val()) {
//         // Highlight checkbox column
//         $('#result_table tr > td:nth-child('+cno+'), #result_table tr>th:nth-child('+cno+')').attr('bgcolor', '#f2e4e4');
//         // Show error msg
//         $('#asv_error').attr('style', 'text-align:right; color:#aa4442');
//         // Stop submission
//         return false;
//     }
//     return true;
// }
