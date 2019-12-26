$(function() {

   // Setup Daterange picker
   $('input[name="daterange"]').daterangepicker({
     opens: 'right',
     timePicker: true,
     startDate: moment().startOf('hour'),
     endDate: moment().startOf('hour').add(24, 'hour'),
   }, function(start, end, label) {
      alert("A new date selection was made: " + start.format('YYYY-MM-DD') + ' to ' + end.format('YYYY-MM-DD'));
   });
 });