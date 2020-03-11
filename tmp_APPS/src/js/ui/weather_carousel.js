cur_weather_index=0

$('#carouselWInd .carousel-control-prev').click(function() {
	cur_weather_index++;
	if(all_weather_img.length>cur_weather_index) {
		cur_weather_index = 0;
	}
	console.log(' CUR INDEX ' , cur_weather_index=0)
});

$('#carouselWInd .carousel-control-next').click(function() {
	cur_weather_index++;
	if(all_weather_img.length>cur_weather_index) {
		cur_weather_index = 0;
	}
	console.log(' CUR INDEX ' , cur_weather_index=0)
});