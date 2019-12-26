$(function() {

   // Setup Daterange picker
   $('input[name="daterange"]').daterangepicker({
     opens: 'right',
     timePicker: true,
     //startDate: moment().startOf('day').add(-24, 'hour'),
     //endDate: moment().startOf('day'),
     startDate: moment($('input[name=start_date]').val()).format('YYYY/MM/DD hh:mm'),
     endDate: moment($('input[name=end_date]').val()).format('YYYY/MM/DD hh:mm')
     locale: {
      format: 'YYYY/MM/DD hh:mm'
    }
   }, function(start, end, label) {
      $('input[name=start_date]').val(start.format('YYYY/MM/DD hh:mm'));
      $('input[name=end_date]').val(end.format('YYYY/MM/DD hh:mm'))
   });
 });