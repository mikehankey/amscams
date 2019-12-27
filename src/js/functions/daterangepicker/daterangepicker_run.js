$(function() {

   // Setup Daterange picker
   $('input[name="daterange"]').daterangepicker({
     opens: 'right', 
     //startDate: moment().startOf('day').add(-24, 'hour'),
     //endDate: moment().startOf('day'),
     startDate: moment($('input[name=start_date]').val()).format('YYYY/MM/DD'),
     endDate: moment($('input[name=end_date]').val()).format('YYYY/MM/DD'),
     locale: {
      format: 'YYYY/MM/DD HH:mm'
    }
   }, function(start, end, label) {
      //$('input[name=start_date]').val(start.format('YYYY/MM/DD HH:mm'));
      //$('input[name=end_date]').val(end.format('YYYY/MM/DD HH:mm'));
      new_url = update_url_param(window.location.href ,'start_date',start.format('YYYY/MM/DD'));
      window.location   = update_url_param(new_url ,'end_date',end.format('YYYY/MM/DD'));
   });
 });