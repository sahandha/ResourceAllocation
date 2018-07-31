/*
 * pure-knob
 *
 * Canvas-based JavaScript UI element implementing touch,
 * keyboard, mouse and scroll wheel support.
 *
 * Copyright 2018 Andre Plötze
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * https://www.cssscript.com/demo/canvas-javascript-knob-dial-component/
 */

"use strict";

/*
 * Custom user interface elements for pure knob.
 */
function PureKnob() {

	/*
	 * Creates a knob element.
	 */
	this.createKnob = function(width, height) {
		var heightString = height.toString();
		var widthString = width.toString();
		var smaller = width < height ? width : height;
		var fontSize = 0.2 * smaller;
		var fontSizeString = fontSize.toString();
		var canvas = document.createElement('canvas');
		var div = document.createElement('div');
		div.style.display = 'inline-block';
		div.style.height = heightString + 'px';
		div.style.position = 'relative';
		div.style.textAlign = 'center';
		div.style.width = widthString + 'px';
		div.appendChild(canvas);
		var input = document.createElement('input');
		input.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
		input.style.border = 'none';
		input.style.color = '#ff8800';
		input.style.fontFamily = 'sans-serif';
		input.style.fontSize = fontSizeString + 'px';
		input.style.height = heightString + 'px';
		input.style.margin = 'auto';
		input.style.padding = '0px';
		input.style.textAlign = 'center';
		input.style.width = widthString + 'px';
		var inputDiv = document.createElement('div');
		inputDiv.style.bottom = '0px';
		inputDiv.style.display = 'none';
		inputDiv.style.left = '0px';
		inputDiv.style.position = 'absolute';
		inputDiv.style.right = '0px';
		inputDiv.style.top = '0px';
		inputDiv.appendChild(input);
		div.appendChild(inputDiv);

		/*
		 * The knob object.
		 */
		var knob = {
			'_canvas': canvas,
			'_div': div,
			'_height': height,
			'_input': input,
			'_inputDiv': inputDiv,
			'_listeners': [],
			'_mousebutton': false,
			'_previousVal': 0,
			'_timeout': null,
			'_width': width,

			/*
			 * Notify listeners about value changes.
			 */
			'_notifyUpdate': function() {
				var properties = this._properties;
				var value = properties.val;
				var listeners = this._listeners;
				var numListeners = listeners.length;

				/*
				 * Call all listeners.
				 */
				for (var i = 0; i < numListeners; i++) {
					var listener = listeners[i];

					/*
					 * Call listener, if it exists.
					 */
					if (listener !== null)
						listener(this, value);

				}

			},

			/*
			 * Properties of this knob.
			 */
			'_properties': {
				'angleEnd': 2.0 * Math.PI,
				'angleOffset': -0.5 * Math.PI,
				'angleStart': 0,
				'colorBG': '#181818',
				'colorFG': '#ff8800',
				'needle': false,
				'readonly': false,
				'trackWidth': 0.4,
				'valMin': 0,
				'valMax': 100,
				'stepSize': 1,
				'val': 0
			},

			/*
			 * Abort value change, restoring the previous value.
			 */
			'abort': function() {
				var previousValue = this._previousVal;
				var properties = this._properties;
				properties.val = previousValue;
				this.redraw();
			},

			/*
			 * Adds an event listener.
			 */
			'addListener': function(listener) {
				var listeners = this._listeners;
				listeners.push(listener);
			},

			/*
			 * Commit value, indicating that it is no longer temporary.
			 */
			'commit': function() {
				var properties = this._properties;
				var value = properties.val;
				this._previousVal = value;
				this.redraw();
				this._notifyUpdate();
			},

			/*
			 * Returns the value of a property of this knob.
			 */
			'getProperty': function(key) {
				return this._properties[key];
			},

			/*
			 * Returns the current value of the knob.
			 */
			'getValue': function() {
				var properties = this._properties;
				var value = properties.val;
				return value;
			},

			/*
			 * Return the DOM node representing this knob.
			 */
			'node': function() {
				var div = this._div;
				return div;
			},

			/*
			 * Redraw the knob on the canvas.
			 */
			'redraw': function() {
				this.resize();
				var properties = this._properties;
				var needle = properties.needle;
				var angleStart = properties.angleStart;
				var angleOffset = properties.angleOffset;
				var angleEnd = properties.angleEnd;
				var actualStart = angleStart + angleOffset;
				var actualEnd = angleEnd + angleOffset;
				var value = properties.val;
				var valueStr = value.toString();
				var valMin = properties.valMin;
				var valMax = properties.valMax;
				var stepSize = properties.stepSize;
				var relValue = (value - valMin) / (valMax - valMin);
				var relAngle = relValue * (angleEnd - angleStart);
				var angleVal = actualStart + relAngle;
				var colorTrack = properties.colorBG;
				var colorFilling = properties.colorFG;
				var trackWidth = properties.trackWidth;
				var height = this._height;
				var width = this._width;
				var smaller = width < height ? width : height;
				var centerX = 0.5 * width;
				var centerY = 0.5 * height;
				var radius = 0.4 * smaller;
				var lineWidth = Math.round(trackWidth * radius);
				var fontSize = 0.2 * smaller;
				var fontSizeString = fontSize.toString();
				var canvas = this._canvas;
				var ctx = canvas.getContext('2d');

				/*
				 * Clear the canvas.
				 */
				ctx.clearRect(0, 0, width, height);

				/*
				 * Draw the track.
				 */
				ctx.beginPath();
				ctx.arc(centerX, centerY, radius, actualStart, actualEnd);
				ctx.lineCap = 'butt';
				ctx.lineWidth = lineWidth;
				ctx.strokeStyle = colorTrack;
				ctx.stroke();

				/*
				 * Draw the filling.
				 */
				ctx.beginPath();

				/*
				 * Check if we're in needle mode.
				 */
				if (needle)
					ctx.arc(centerX, centerY, radius, angleVal - 0.1, angleVal + 0.1);
				else
					ctx.arc(centerX, centerY, radius, actualStart, angleVal);

				ctx.lineCap = 'butt';
				ctx.lineWidth = lineWidth;
				ctx.strokeStyle = colorFilling;
				ctx.stroke();

				/*
				 * Draw the number.
				 */
				ctx.font = fontSizeString + 'px sans-serif';
				ctx.fillStyle = colorFilling;
				ctx.textAlign = 'center';
				ctx.textBaseline = 'middle';
				ctx.fillText(valueStr, centerX, centerY);

				/*
				 * Set the color of the input element.
				 */
				var elemInput = this._input;
				elemInput.style.color = colorFilling;
			},

			/*
			 * This is called as the canvas or the surrounding DIV is resized.
			 */
			'resize': function() {
				var canvas = this._canvas;
				canvas.style.height = '100%';
				canvas.style.width = '100%';
				canvas.height = this._height;
				canvas.width = this._width;
			},

			/*
			 * Sets the value of a property of this knob.
			 */
			'setProperty': function(key, value) {
				this._properties[key] = value;
				this.redraw();
			},

			/*
			 * Sets the value of this knob.
			 */
			'setValue': function(value) {
				this.setValueFloating(value);
				this.commit();
			},

			/*
			 * Sets floating (temporary) value of this knob.
			 */
			'setValueFloating': function(value) {
				var properties = this._properties;
				var valMin = properties.valMin;
				var valMax = properties.valMax;

				/*
				 * Clamp the actual value into the [valMin; valMax] range.
				 */

				if (value < valMin){
					value = valMin;}
				else if (value > valMax){
					value = valMax;}

				value = Math.round(value);
				this.setProperty('val', value);
			}

		};

		/*
		 * Convert mouse event to value.
		 */
		var mouseEventToValue = function(e, properties) {
			var canvas = e.target;
			var width = canvas.scrollWidth;
			var height = canvas.scrollHeight;
			var centerX = 0.5 * width;
			var centerY = 0.5 * height;
			var x = e.offsetX;
			var y = e.offsetY;
			var relX = x - centerX;
			var relY = y - centerY;
			var angleStart = properties.angleStart;
			var angleEnd = properties.angleEnd;
			var angleDiff = angleEnd - angleStart;
			var angle = Math.atan2(relX, -relY) - angleStart;
			var twoPi = 2.0 * Math.PI;

			/*
			 * Make negative angles positive.
			 */
			if (angle < 0) {

				if (angleDiff >= twoPi)
					angle += twoPi;
				else
					angle = 0;

			}

			var valMin = properties.valMin;
			var valMax = properties.valMax;
			var value = ((angle / angleDiff) * (valMax - valMin)) + valMin;

			/*
			 * Clamp values into valid interval.
			 */
			if (value < valMin)
				value = valMin;
			else if (value > valMax)
				value = valMax;

			return value;
		};

		/*
		 * Show input element on double click.
		 */
		var doubleClickListener = function(e) {
			var properties = knob._properties;
			var readonly = properties.readonly;

			/*
			 * If knob is not read-only, display input element.
			 */
			if (!readonly) {
				e.preventDefault();
				var inputDiv = knob._inputDiv;
				inputDiv.style.display = 'block';
				var inputElem = knob._input;
				inputElem.focus();
				knob.redraw();
			}

		};

		/*
		 * This is called when the mouse button is depressed.
		 */
		var mouseDownListener = function(e) {
			var btn = e.buttons;

			/*
			 * It is a left-click.
			 */
			if (btn === 1) {
				var properties = knob._properties;
				var readonly = properties.readonly;

				/*
				 * If knob is not read-only, process mouse event.
				 */
				if (!readonly) {
					e.preventDefault();
					var val = mouseEventToValue(e, properties);
					knob.setValueFloating(val);
				}

				knob._mousebutton = true;
			}

			/*
			 * It is a middle click.
			 */
			if (btn === 4) {
				var properties = knob._properties;
				var readonly = properties.readonly;

				/*
				 * If knob is not read-only, display input element.
				 */
				if (!readonly) {
					e.preventDefault();
					var inputDiv = knob._inputDiv;
					inputDiv.style.display = 'block';
					var inputElem = knob._input;
					inputElem.focus();
					knob.redraw();
				}

			}

		};

		/*
		 * This is called when the mouse cursor is moved.
		 */
		var mouseMoveListener = function(e) {
			var btn = knob._mousebutton;

			/*
			 * Only process event, if mouse button is depressed.
			 */
			if (btn) {
				var properties = knob._properties;
				var readonly = properties.readonly;

				/*
				 * If knob is not read-only, process mouse event.
				 */
				if (!readonly) {
					e.preventDefault();
					var val = mouseEventToValue(e, properties);
					knob.setValueFloating(val);
				}

			}

		};

		/*
		 * This is called when the mouse button is released.
		 */
		var mouseUpListener = function(e) {
			var btn = knob._mousebutton;

			/*
			 * Only process event, if mouse button was depressed.
			 */
			if (btn) {
				var properties = knob._properties;
				var readonly = properties.readonly;

				/*
				 * If knob is not read only, process mouse event.
				 */
				if (!readonly) {
					e.preventDefault();
					var val = mouseEventToValue(e, properties);
					knob.setValue(val);
				}

			}

			knob._mousebutton = false;
		};

		/*
		 * This is called when the drag action is canceled.
		 */
		var mouseCancelListener = function(e) {
			var btn = knob._mousebutton;

			/*
			 * Abort action if mouse button was depressed.
			 */
			if (btn) {
				knob.abort();
				knob._mousebutton = false;
			}

		};

		/*
		 * This is called when the size of the canvas changes.
		 */
		var resizeListener = function(e) {
			knob.redraw();
		};

		/*
		 * This is called when the mouse wheel is moved.
		 */
		var scrollListener = function(e) {
			var readonly = knob.getProperty('readonly');
			var stepSize = knob.getProperty('stepSize')
			/*
			 * If knob is not read only, process mouse wheel event.
			 */
			if (!readonly) {
				e.preventDefault();
				var delta = e.deltaY;
				var direction = delta > 0 ? -stepSize : (delta < 0 ? +stepSize : 0);
				var val = knob.getValue();
				val += direction;
				knob.setValueFloating(val);

				/*
				 * Perform delayed commit.
				 */
				var commit = function() {
					knob.commit();
				};

				var timeout = knob._timeout;
				window.clearTimeout(timeout);
				timeout = window.setTimeout(commit, 250);
				knob._timeout = timeout;
			}

		};

		/*
		 * This is called when the user presses a key on the keyboard.
		 */
		var keyPressListener = function(e) {
			var kc = e.keyCode;

			/*
			 * Hide input element when user presses enter or escape.
			 */
			if ((kc === 13) || (kc === 27)) {
				var inputDiv = knob._inputDiv;
				inputDiv.style.display = 'none';
				var input = e.target;

				/*
				 * Only evaluate value when user pressed enter.
				 */
				if (kc === 13) {
					var value = input.value;
					var val = parseInt(value);
					var valid = isFinite(val);

					/*
					 * Check if input is a valid number.
					 */
					if (valid)
						knob.setValue(val);

				}

				input.value = '';
			}

		};

		canvas.addEventListener('dblclick', doubleClickListener);
		canvas.addEventListener('mousedown', mouseDownListener);
		canvas.addEventListener('mouseleave', mouseCancelListener);
		canvas.addEventListener('mousemove', mouseMoveListener);
		canvas.addEventListener('mouseup', mouseUpListener);
		canvas.addEventListener('resize', resizeListener);
		canvas.addEventListener('touchstart', mouseDownListener);
		canvas.addEventListener('touchmove', mouseMoveListener);
		canvas.addEventListener('touchend', mouseUpListener);
		canvas.addEventListener('touchcancel', mouseCancelListener);
		canvas.addEventListener('wheel', scrollListener);
		input.addEventListener('keypress', keyPressListener);
		return knob;
	};

}

var pureknob = new PureKnob();
