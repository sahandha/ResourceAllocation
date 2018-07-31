var elems = document.getElementsByClassName("timer");



for (i = 0; i < elems.length; i++) {

  var startTime = elems[i].getAttribute("start-time")
  var duration  = elems[i].getAttribute("duration")
  var endTime   = new Date(new Date(startTime).getTime()+duration*60000).getTime()

  // Update the count down every 1 second
  var x = setInterval(function(){
      // Get todays date and time
      var now = new Date().getTime();

      // Find the distance between now an the count down date
      var distance = endTime - now;


      // Time calculations for days, hours, minutes and seconds
      var days    = Math.floor( distance / (1000 * 60 * 60 * 24));
      var hours   = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      var seconds = Math.floor((distance % (1000 * 60)) / 1000);

      // Output the result in an element with id="demo"
      elems[i].innerHTML = days + "d " + hours + "h "
      + minutes + "m " + seconds + "s ";

      // If the count down is over, write some text
      if (distance < 0) {
          clearInterval(x);
          elems[i].innerHTML = "EXPIRED";
      }
  },1000)
}
