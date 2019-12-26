$(function() {

   // Setup Daterange picker
   $('input[name="daterange"]').daterangepicker({
     opens: 'right',
     timePicker: true,
     startDate: moment().startOf('hour'),
     endDate: moment().startOf('hour').add(24, 'hour'),
   }, function(start, end, label) {
      $('input[name=start_date]').val(start.format('YYYY/MM/DD hh:mm'));
      $('input[name=end_date]').val(end.format('YYYY/MM/DD hh:mm'))
   });
 });