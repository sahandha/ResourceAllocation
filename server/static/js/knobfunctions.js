
var elems = document.getElementsByClassName("knob");
var i;
var node;
for (i = 0; i < elems.length; i++) {
  var knob = makeKnob(elems[i]);
  var node = knob.node();
  elems[i].appendChild(node);
}



function makeKnob(elem) {
  var min = elem.getAttribute("min")
  var max = elem.getAttribute("max")
  var val = elem.getAttribute("value")
  var stepSize = elem.getAttribute("step")
  var size = elem.getAttribute("size")
  var readonly = elem.getAttribute("readonly")

  var knob = pureknob.createKnob(size, size);

  // Set properties.
  knob.setProperty('angleStart', -0.75 * Math.PI);
  knob.setProperty('angleEnd', 0.75 * Math.PI);
  knob.setProperty('colorFG', '#18458e');
  knob.setProperty('colorBG', '#b6bdc6');
  knob.setProperty('trackWidth', 0.4);
  knob.setProperty('valMin', Number(min));
  knob.setProperty('valMax', Number(max));
  knob.setProperty('val', Number(val));
  knob.setProperty('stepSize', Number(stepSize));
  knob.setProperty('readonly', readonly);

  // Set initial value.
  knob.setValue(val);

  elem.getElementsByTagName("input")[0].value=val
  /*
  * Event listener.
  *
  * Parameter 'knob' is the knob object which was
  * actuated. Allows you to associate data with
  * it to discern which of your knobs was actuated.
  *
  * Parameter 'value' is the value which was set
  * by the user.
  */
  var listener = function(knob, value) {
    elem.getElementsByTagName("input")[0].value=value
    console.log(value);
  };

  knob.addListener(listener);

  return knob
}
