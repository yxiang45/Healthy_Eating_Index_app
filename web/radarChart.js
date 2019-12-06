/////////////////////////////////////////////////////////
/////////////// The Radar Chart Function ////////////////
/////////////// Written by Nadieh Bremer ////////////////
////////////////// VisualCinnamon.com ///////////////////
/////////// Inspired by the code of alangrafu ///////////
/////////////////////////////////////////////////////////
	
function RadarChart(id, data, options, TotalScore) {
	var cfg = {
	 w: 600,				//Width of the circle
	 h: 600,				//Height of the circle
	 margin: {top: 20, right: 20, bottom: 20, left: 20}, //The margins of the SVG
	 levels: 3,				//How many levels or inner circles should there be drawn
	 maxValue: 0, 			//What is the value that the biggest circle will represent
	 labelFactor: 1.25, 	//How much farther than the radius of the outer circle should the labels be placed
	 wrapWidth: 60, 		//The number of pixels after which a label needs to be given a new line
	 opacityArea: 0.35, 	//The opacity of the area of the blob
	 dotRadius: 4, 			//The size of the colored circles of each blog
	 opacityCircles: 0.1, 	//The opacity of the circles of each blob
	 strokeWidth: 2, 		//The width of the stroke around each blob
	 roundStrokes: false,	//If true the area and stroke will follow a round path (cardinal-closed)
	 color: d3.scale.category10()	//Color function
	};
	
	//Put all of the options into a variable called cfg
	if('undefined' !== typeof options){
	  for(var i in options){
		if('undefined' !== typeof options[i]){ cfg[i] = options[i]; }
	  }//for i
	}//if
	
	//If the supplied maxValue is smaller than the actual one, replace by the max in the data
	var maxValue = Math.max(cfg.maxValue, d3.max(data, function(i){return d3.max(i.map(function(o){return o.value;}))}));
		
	var allAxis = (data[0].map(function(i, j){return i.axis})),	//Names of each axis
		total = allAxis.length,					//The number of different axes
		radius = Math.min(cfg.w/2, cfg.h/2), 	//Radius of the outermost circle
		Format = d3.format('%'),			 	//Percentage formatting
		angleSlice = Math.PI * 2 / total;		//The width in radians of each "slice"
	
	//Scale for the radius
	var rScale = d3.scale.linear()
		.range([0, radius])
		.domain([0, maxValue]);
		
	/////////////////////////////////////////////////////////
	//////////// Create the container SVG and g /////////////
	/////////////////////////////////////////////////////////

	//Remove whatever chart with the same id/class was present before
	d3.select(id).select("svg").remove();
	
	//Initiate the radar chart SVG
	var svg = d3.select(id).append("svg")
			.attr("width",  cfg.w + cfg.margin.left + cfg.margin.right)
			.attr("height", cfg.h + cfg.margin.top + cfg.margin.bottom)
			.attr("class", "radar"+id);
	//Append a g element		
	var g = svg.append("g")
			.attr("transform", "translate(" + (cfg.w/2 + cfg.margin.left) + "," + (cfg.h/2 + cfg.margin.top) + ")");
	
	/////////////////////////////////////////////////////////
	////////// Glow filter for some extra pizzazz ///////////
	/////////////////////////////////////////////////////////
	
	//Filter for the outside glow
	var filter = g.append('defs').append('filter').attr('id','glow'),
		feGaussianBlur = filter.append('feGaussianBlur').attr('stdDeviation','2.5').attr('result','coloredBlur'),
		feMerge = filter.append('feMerge'),
		feMergeNode_1 = feMerge.append('feMergeNode').attr('in','coloredBlur'),
		feMergeNode_2 = feMerge.append('feMergeNode').attr('in','SourceGraphic');

	/////////////////////////////////////////////////////////
	/////////////// Draw the Circular grid //////////////////
	/////////////////////////////////////////////////////////
	
	//Wrapper for the grid & axes
	var axisGrid = g.append("g").attr("class", "axisWrapper");
	
	//Draw the background circles
	axisGrid.selectAll(".levels")
	   .data(d3.range(1,(cfg.levels+1)).reverse())
	   .enter()
		.append("circle")
		.attr("class", "gridCircle")
		.attr("r", function(d, i){return radius/cfg.levels*d;})
		.style("fill", "#CDCDCD")
		.style("stroke", "#CDCDCD")
		.style("fill-opacity", cfg.opacityCircles)
		.style("filter" , "url(#glow)");

	//Text indicating at what % each level is
	axisGrid.selectAll(".axisLabel")
	   .data(d3.range(1,(cfg.levels+1)).reverse())
	   .enter().append("text")
	   .attr("class", "axisLabel")
	   .attr("x", 4)
	   .attr("y", function(d){return -d*radius/cfg.levels;})
	   .attr("dy", "0.4em")
	   .style("font-size", "10px")
	   .attr("fill", "#737373")
	   .text(function(d,i) { return Format(maxValue * d/cfg.levels); });

	/////////////////////////////////////////////////////////
	//////////////////// Draw the axes //////////////////////
	/////////////////////////////////////////////////////////
	
	//Create the straight lines radiating outward from the center
	var axis = axisGrid.selectAll(".axis")
		.data(allAxis)
		.enter()
		.append("g")
		.attr("class", "axis");
	//Append the lines
	axis.append("line")
		.attr("x1", 0)
		.attr("y1", 0)
		.attr("x2", function(d, i){ return rScale(maxValue*1.1) * Math.cos(angleSlice*i - Math.PI/2); })
		.attr("y2", function(d, i){ return rScale(maxValue*1.1) * Math.sin(angleSlice*i - Math.PI/2); })
		.attr("class", "line")
		.style("stroke", "white")
		.style("stroke-width", "2px");

	//Append the labels at each axis
	axis.append("text")
		.attr("class", "legend")
		.style("font-size", "11px")
		.attr("text-anchor", "middle")
		.attr("dy", "0.35em")
		.attr("x", function(d, i){ return rScale(maxValue * cfg.labelFactor) * Math.cos(angleSlice*i - Math.PI/2); })
		.attr("y", function(d, i){ return rScale(maxValue * cfg.labelFactor) * Math.sin(angleSlice*i - Math.PI/2); })
		.text(function(d){return d})
		.call(wrap, cfg.wrapWidth);

	/////////////////////////////////////////////////////////
	///////////// Draw the radar chart blobs ////////////////
	/////////////////////////////////////////////////////////
	
	//The radial line function
	var radarLine = d3.svg.line.radial()
		.interpolate("linear-closed")
		.radius(function(d) { return rScale(d.value); })
		.angle(function(d,i) {	return i*angleSlice; });
		
	if(cfg.roundStrokes) {
		radarLine.interpolate("cardinal-closed");
	}
				
	//Create a wrapper for the blobs	
	var blobWrapper = g.selectAll(".radarWrapper")
		.data(data)
		.enter().append("g")
		.attr("class", "radarWrapper");


	//Append the backgrounds	
	blobWrapper
		.append("path")
		.attr("class", "radarArea")
		.attr("d", function(d,i) { return radarLine(d); })
		.style("fill", function(d,i) { return cfg.color(i); })
		.style("fill-opacity", cfg.opacityArea)
		.on('mouseover', function (d,i){

			//Dim all blobs
			d3.selectAll(".radarArea")
				.transition().duration(200)
				.style("fill-opacity", 0.1); 
			//Bring back the hovered over blob
			d3.select(this)
				.transition().duration(200)
				.style("fill-opacity", 0.7);
			tooltip
				.style("top", (event.pageY)+"px")
				.style("left",(event.pageX)+"px")
				.style("visibility", "visible");

		})
		.on('mouseout', function(){
			//Bring back all blobs
			d3.selectAll(".radarArea")
				.transition().duration(200)
				.style("fill-opacity", cfg.opacityArea);
			tooltip
				.style("visibility", "hidden");

		});
	//Set up the recommendation tooltip for when you hover over a blob

	var new_html = get_recomm(data);
	var tooltip = d3.select(id)
		.append("div")
		.attr("id","tooltip")
		.style("position", "absolute")
		.style("visibility", "hidden")
		.style("background-color", "white")
		.style("border", "solid")
		.style("border-width", "1px")
		.style("border-radius", "5px")
		.style("padding", "10px")
		.html(new_html.join(""));
		
	//Create the outlines	
	blobWrapper.append("path")
		.attr("class", "radarStroke")
		.attr("d", function(d,i) { return radarLine(d); })
		.style("stroke-width", cfg.strokeWidth + "px")
		.style("stroke", function(d,i) { return cfg.color(i); })
		.style("fill", "none")
		.style("filter" , "url(#glow)");

	
	//Append the circles
	blobWrapper.selectAll(".radarCircle")
		.data(function(d,i) { return d; })
		.enter().append("circle")
		.attr("class", "radarCircle")
		.attr("r", cfg.dotRadius)
		.attr("cx", function(d,i){ return rScale(d.value) * Math.cos(angleSlice*i - Math.PI/2); })
		.attr("cy", function(d,i){ return rScale(d.value) * Math.sin(angleSlice*i - Math.PI/2); })
		.style("fill", function(d,i,j) { return cfg.color(j); })
		.style("fill-opacity", 0.8);
	//Add total score on the top left and explanation on the left
	g.append("text")
	   .attr("class","label")
	   .attr("x",0-cfg.w+cfg.margin.left+cfg.margin.right)
       .attr("y", 0-cfg.h*0.65-5)
	   .attr("text-anchor","start")
       .text(function(){return "Total HEI: "+ TotalScore;});
	   
	g.append("text")
	   .attr("class","sublabel")
	   .attr("x",cfg.w*0.6)
       .attr("y", 0-cfg.h*0.65-5)
	   .attr("text-anchor","end")
       .text("The maximum possible Total HEI score is 100, the higher the better your diet quality");
	/////////////////////////////////////////////////////////
	//////// Append invisible circles for tooltip ///////////
	/////////////////////////////////////////////////////////
	
	var tip = d3.tip()
		.attr('class', 'd3-tip-radar')
		.offset([-10, 0])
		.html(function(d) {
			if (d.value<0.5){
				return "<strong>You can do better!</strong> Your HEI score for <strong>" + d.axis + '</strong> is <span style="color: red; font-weight: bold; font-size: 13px">' + d.HEIscore  +"</span> out of " + d.Max_score + "<br/>" 
			+ "The standard for maximum is " + d.Max_standard + "<br/>"+" The standard for minimum is " + d.Min_standard;}
			if (d.value>=0.5 && d.value <0.75){
				return "<strong>Good job!</strong> Your HEI score for <strong>" + d.axis + '</strong> is <span style="color: blue; font-weight: bold; font-size: 13px">' + d.HEIscore  +"</span> out of " + d.Max_score + "<br/>" 
			+ "The standard for maximum is " + d.Max_standard + "<br/>"+" The standard for minimum is " + d.Min_standard;}
			if (d.value>=0.75){
				return "<strong>Excellent!</strong> Your HEI score for <strong>" + d.axis + '</strong> is <span style="color: green; font-weight: bold; font-size: 13px">' + d.HEIscore  +"</span> out of " + d.Max_score + "<br/>" 
			+ "The standard for maximum is " + d.Max_standard + "<br/>"+" The standard for minimum is " + d.Min_standard;}
		})
		
	//Wrapper for the invisible circles on top
	var blobCircleWrapper = g.selectAll(".radarCircleWrapper")
		.data(data)
		.enter().append("g")
		.attr("class", "radarCircleWrapper");
	
	blobCircleWrapper.call(tip);
	//Append a set of invisible circles on top for the mouseover pop-up
	blobCircleWrapper.selectAll(".radarInvisibleCircle")
		.data(function(d,i) { return d; })
		.enter().append("circle")
		.attr("class", "radarInvisibleCircle")
		.attr("r", cfg.dotRadius*1.5)
		.attr("cx", function(d,i){ return rScale(d.value) * Math.cos(angleSlice*i - Math.PI/2); })
		.attr("cy", function(d,i){ return rScale(d.value) * Math.sin(angleSlice*i - Math.PI/2); })
		.style("fill", "none")
		.style("pointer-events", "all")
		.on("mouseover",function(d,i){
			tip.show(d,i);
			if (d.value < 0.5){
				d3.select(this)				 
				.style("fill", "red").transition().duration(200);
			}
			if (d.value >= 0.5 && d.value < 0.75){
				d3.select(this)				 
			.style("fill", "blue").transition().duration(200);
			}
			if (d.value >= 0.75){
				d3.select(this)				 
			.style("fill", "green").transition().duration(200);
			}
		})
		.on("mouseout",function(d,i){
				tip.hide(d,i);
				d3.select(this)
				.transition().duration(200)
				.style("fill", "none");
		})
		

	
	/////////////////////////////////////////////////////////
	/////////////////// Helper Function /////////////////////
	/////////////////////////////////////////////////////////

	//Taken from http://bl.ocks.org/mbostock/7555321
	//Wraps SVG text	
	function wrap(text, width) {
	  text.each(function() {
		var text = d3.select(this),
			words = text.text().split(/\s+/).reverse(),
			word,
			line = [],
			lineNumber = 0,
			lineHeight = 1.4, // ems
			y = text.attr("y"),
			x = text.attr("x"),
			dy = parseFloat(text.attr("dy")),
			tspan = text.text(null).append("tspan").attr("x", x).attr("y", y).attr("dy", dy + "em");
			
		while (word = words.pop()) {
		  line.push(word);
		  tspan.text(line.join(" "));
		  if (tspan.node().getComputedTextLength() > width) {
			line.pop();
			tspan.text(line.join(" "));
			line = [word];
			tspan = text.append("tspan").attr("x", x).attr("y", y).attr("dy", ++lineNumber * lineHeight + dy + "em").text(word);
		  }
		}
	  });
	}//wrap	
	
	//generatiion recommendation list
	function get_recomm(data){
		var recomm = {"Total Fruits":'<li>Eat a variety of fruits, emphasizing whole fruits.</li>',
			"Whole Fruits":'<li>Enjoy fruit more often than juice. When consuming juice, choose 100% juices without added sugars.</li>',
			"Total Vegetables":'<li>Eat a variety of vegetables from all of the subgroups—dark green, red and orange, legumes (beans and peas), starchy, and other.</li>',
			"Greens and Beans":'<li>Choose at least one dark green and one legume each day.</li>',
			"Whole Grains":'<li>Make half your grains whole grains. </li>',
			"Dairy":'<li>Choose fat-free or low-fat dairy, including milk, yogurt, cheese, and/or fortified soy beverages.</li>',
			"Total Protein Foods":'<li>Eat a variety of protein foods, includes seafood, lean meats and poultry, eggs, and plant proteins.</li>',
			"Seafood and Plant Proteins":'<li>Enjoy protein from seafood and legumes (beans and peas), and nuts, seeds, and soy products.</li>',
			"Refined Grains":'<li>Limit products made with refined grains, especially those high in fat, sugars, and/or sodium, such as cookies, cakes, and some snack foods.</li>',
			"Added Sugars":'<li>Consume less than 10 percent of calories per day from added sugars.</li>',
			"Fatty Acids":'<li>Limit saturated fats and trans fats, added sugars, and sodium.</li>',
			"Sodium":'<li>Consume less than 2,300 milligrams (mg) per day of sodium.</li>',
			"Saturated Fats":'<li>Consume less than 10 percent of calories per day from saturated fats.</li>'
}
	
		var html_s=['<p>To achieve a healthy eating pattern, the Dietary Guidelines for Americans encourage you to:</p>','<ul style="list-style-type:disc;text-align: left">'];
		for (var j=0;j<data[0].length;j++){
			if (data[0][j].value <=0.6){
				html_s.push(recomm[data[0][j].axis]);
			}
		}
		html_s.push('</ul>');
		return html_s;
	}
}//RadarChart