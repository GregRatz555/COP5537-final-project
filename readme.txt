Florida Network Simulator by Gregory Ratz
for COP5537 Final project

    This program displays an animated map of Florida as nodes are randomly distributed around the cities specified, creating connections when nodes are within range of eachother, and
optionally using Prim's algorithm to show the MST of the currently available network nodes
visible to a selected city. 
    The program provides an initial option to use the default settings, but an 'n' response
will allow for a custom setup.
The available cities are listed, with the letter used to select in bracket. For example [o]rlando is selected by including the letter o in the response.
Any combination up to all listed cities is acceptable and will determine where the root nodes are placed.
    After the cities are selected, the prompt asks to place an MST in any city (using Prim's algorithm), whose city will be specified after, and if any city gets investment.
An investment is a number of nodes forced to spawn at iteration 0, to help a city in a less dense region connect to the major network clusters, representing more targeted efforts to increase network use in an area.
    The user will specify for each city whether of not to make it the center of the MST or how much to invest, though leaving either blank will default to not MST and 0 investment (beyond the single root node). If no MST city is provided after an MST is requested, none shall be generated.
    The program will ask how many iterations to run, an iteration is one pass through the existing nodes in the network, checking if each will spawn and making any connections to nodes in range.
    Next it will ask how many iterations between examinations, this will pause the network growth after the specified iterations to allow for zooming and examining the network at its current state, and require user input to resume growth. If a prim city is specified, its network structure may be generated and shown at this point as well. The e[x]it function is also available to cut the simulation short.
    The program next asks for connection range (distance in miles that nodes may make connections), the spread factor (How commonly and far from center generated nodes appear, larger means bigger and wider reach), and spawn chance (base probability for nodes to create new nodes). These may be changed if needed but are best left to defaults.
    After that, the node connection and child counts are requested. These simply allow for a cap on how many connections a node can make, and how many times it may spawn a child node. Making these numbers smaller improves the speed of the simulation somewhat by pruning many calculations from the update loop, but pressing enter defaults to no limits.
    Finally, the program asks to end simulation on victory condition, meaning that when a city has child nodes that connect to child nodes spawned from every other cities, the simulation ends. This should be set to 'n' for simulations with only one city or two nearby (like St Petersburg and Tampa for example) so that they do not end prematurely (or immediately in the case of a one city sim).
    The program will automatically graph the nodes as generated (colored by home city) and links between them and the iteration count, new node count, and total node counts will be shown in the console. The console is also used to resume after an examination pause.
