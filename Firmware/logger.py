-TileColor" content="#da532c">
        <meta name="theme-color" content="#ffffff">

        <script src="https://code.jquery.com/jquery-3.6.1.min.js"></script>
        <style>
            .led {
                width: 20em;
                margin-bottom: 1em;
            }

            .led-outer {
                border: 1px solid black;
            }

            .led-center {
                border: 5px solid blue;
            }

            .led-inner {
                border: 1px solid black;
                padding: 0.5em;
            }

            .led-index {
                text-align: center;
                margin-bottom: 0.5em;
            }

            .led-inner div label {
                text-align: right;
                min-width: 1em;
                float: left;
            }

            .led-inner div.range {
                width: 20em;    
            }   

            .led-inner span.value {
                width: 4em;
                text-align: right;
            }

            #swatch {
                background-color: blue;
            }

            #rgbHex {
                text-align: center;
                margin-top: 0.5em;
            }

            </style>
        </head>
    <body>
            
        <h1>Heinrichsweg 9</h1>

        <div class="led" id="led0"">
            <div class="led-outer"><div class="led-center"><div class="led-inner">
                <div class="led-index">#0</div>
                <div>
                    <label for="slider_r">R</label>
                    <div class="range"><input type="range" min="0" max="255" value="0" class="slider" id="slider_r"><span class="value" id="value_r"></span></div>
                </div>
                <div>
                    <label for="slider_g">G</label>
                    <div class="range"><input type="range" min="0" max="255" value="0" class="slider" id="slider_g"><span class="value" id="value_g"></span></div>
                </div>
                <div>
                    <label for="slider_b">B</label>
                    <div class="range"><input type="range" min="0" max="255" value="0" class="slider" id="slider_b"><span class="value" id="value_b"></span></div>
                </div>
                <div>
                    <label for="slider_h">H</label>
                    <div class="range"><input type="range" min="0" max="360" value="0" class="slider" id="slider_h"><span class="value" id="value_h"></span></div>
                </div>
                <div>
                    <label for="slider_s">S</label>
                    <div class="range"><input type="range" min="0" max="100" value="0" class="slider" id="slider_s"><span class="value" id="value_s"></span></div>
                </div>
                <div>
                    <label for="slider_v">V</label>
                    <div class="range"><input type="range" min="0" max="100" value="0" class="slider" id="slider_v"><span class="value" id="value_v"></span></div>
                </div>
                <div id="rgbHex"></div>
            </div></div></div>
        </div>

    </body>

    <script>
        var rgb = [[0,0,0]]; // [[0..255, 0..255, 0..255], [..], [..]]
        var hsv = [[0,0,0]]; // [[0.0 .. 1.0, 0.0 .. 1.0, 0.0 .. 1.0], [..], [..]]

        var inflight = null;
        
        function rgbToHsv() {
            var ledcount = rgb.length;
            for (var ledindex = 0; ledindex < ledcount; ledindex++) { 
                var r = rgb[ledindex][0] / 255.0;
                var g = rgb[ledindex][1] / 255.0;
                var b = rgb[ledindex][2] / 255.0;
                
                var max = Math.max(r, g, b), min = Math.min(r, g, b);
                var h, s, v = max;

                var d = max - min;
                s = max == 0 ? 0 : d / max;

                if (max == min) {
                    h = 0; // achromatic
                } else {
                    switch (max) {
                    case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                    case g: h = (b - r) / d + 2; break;
                    case b: h = (r - g) / d + 4; break;
                    }

                    h = h/6;
                }

                hsv[ledindex] = [h, s, v];
            }
        }

        function hsvToRgb() {
            var ledcount = rgb.length;
            for (var ledindex = 0; ledindex < ledcount; ledindex++) { 
                var h = hsv[ledindex][0];
                var s = hsv[ledindex][1];
                var v = hsv[ledindex][2];
                
                var r, g, b;

                var i = Math.floor(h * 6);
                var f = h * 6 - i;
                var p = v * (1 - s);
                var q = v * (1 - f * s);
                var t = v * (1 - (1 - f) * s);

                switch (i % 6) {
                    case 0: r = v, g = t, b = p; break;
                    case 1: r = q, g = v, b = p; break;
                    case 2: r = p, g = v, b = t; break;
                    case 3: r = p, g = q, b = v; break;
                    case 4: r = t, g = p, b = v; break;
                    case 5: r = v, g = p, b = q; break;
                }

                rgb[ledindex] = [Math.trunc(r*255), Math.trunc(g*255), Math.trunc(b*255)];
            }
        }

        function toHex(n) {
            n = Math.max(0, Math.min(Math.trunc(n),255)); // clamp
            return "0123456789abcdef".charAt((n-n%16)/16) + "0123456789abcdef".charAt(n%16);
        }

        function updateUI() {
            console.log("updateUI()");

            var ledcount = rgb.length;
            for (var ledindex = 0; ledindex < ledcount; ledindex++) { 
                leddiv = $("#led" + ledindex);

                leddiv.find("#slider_r").val(rgb[ledindex][0]);
                leddiv.find("#slider_g").val(rgb[ledindex][1]);
                leddiv.find("#slider_b").val(rgb[ledindex][2]);

                leddiv.find("#value_r").text(rgb[ledindex][0]);
                leddiv.find("#value_g").text(rgb[ledindex][1]);
                leddiv.find("#value_b").text(rgb[ledindex][2]);
                
                leddiv.find("#slider_h").val(Math.trunc(hsv[ledindex][0] * 360));
                leddiv.find("#slider_s").val(Math.trunc(hsv[ledindex][1] * 100));
                leddiv.find("#slider_v").val(Math.trunc(hsv[ledindex][2] * 100));

                leddiv.find("#value_h").text(Math.trunc(hsv[ledindex][0] * 360));
                leddiv.find("#value_s").text(Math.trunc(hsv[ledindex][1] * 100));
                leddiv.find("#value_v").text(Math.trunc(hsv[ledindex][2] * 100));

                rgbhex = "#" + toHex(rgb[ledindex][0]) + toHex(rgb[ledindex][1]) + toHex(rgb[ledindex][2]);
                leddiv.find("#rgbHex").text(rgbhex);
                leddiv.find(".led-center").css("border-color", rgbhex);
            }
        }

        function postLEDs() {
            params = "";

            var ledcount = rgb.length;
            for (var ledindex = 0; ledindex < ledcount; ledindex++) { 
                if (params) {
                    params += "&";
                }                        
                params += "r" + ledindex + "=" + rgb[ledindex][0] + "&g" + ledindex +"=" + rgb[ledindex][1] + "&b" + ledindex + "=" + rgb[ledindex][2];
            }

            url = "/set?" + params
            // console.log("postLEDs() " + url);
            
            $.post(url); // don't care about any results.
        }

        $(document).ready(function() {
            
            // Clone UI from led #0 to the rest.
            led0div = $("#led0");

            for(i = 7 ; i >= 1 ; i--)
            {
                leddiv = led0div.clone().prop("id", "led" + i);
                leddiv.find(".led-index").text("#" + i);
                
                led0div.after(leddiv);

                // All LEDs are initialized the same.
                rgb.push([rgb[0][0], rgb[0][1], rgb[0][2]]); // Force a deep copy.
                hsv.push([0, 0, 0]); // Values do not matter, they will be calculated from RGB.
            }

            // Wire controls.
            $("input[type=range]").on("input", function() {
                ledindex = $(this).parents(".led").attr("id").substring(3);
                console.log("changing led #" + ledindex);

                switch ($(this).attr("id") ) {
                    case "slider_r":
                        rgb[ledindex][0] = $(this).val();
                        rgbToHsv();
                        break;
                    case "slider_g":
                        rgb[ledindex][1] = $(this).val();
                        rgbToHsv();
                        break;
                    case "slider_b":
                        rgb[ledindex][2] = $(this).val();
                        rgbToHsv();
                        break;
                    case "slider_h":
                        hsv[ledindex][0] = $(this).val() / 360.0;
                        hsvToRgb();
                        break;
                    case "slider_s":
                        hsv[ledindex][1] = $(this).val() / 100.0;
                        hsvToRgb();
                        break;
                    case "slider_v":
                        hsv[ledindex][2] = $(this).val() / 100.0;
                        hsvToRgb();
                        break;
                    default:
                        console.log("unhandled " + $(this).attr("id"));
                        break;
                }
                
                updateUI();
            
                clearTimeout(inflight)
                inflight = setTimeout(postLEDs, 100);
            });

            // Calculate initial HSV values.
            rgbToHsv();

            // Update the UI once.
            updateUI();
            
            // Synchronize physical LEDs to UI.
            // postLEDs(); // Don't. We want the animation to keep running until the user actually makes a change.
        });    
    </script>
    
</html>