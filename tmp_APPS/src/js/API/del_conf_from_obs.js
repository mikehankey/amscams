// WARNING HERE WE SEND "CROPPED VIDEO" BECAUSE IT'S IN THE TEMPLATE
// AND WE KNOW IT'S UNIQUE FOR THE DETECTION
function setup_single_conf_buttons() {
   $('.confSingle').click(function() {
      send_API_task({'toConf':cropped_video},'','');
      return false;
   });
}