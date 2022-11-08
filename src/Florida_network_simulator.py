'''
Gregory Ratz 2021
gr700613
Final Project for Network Optimization
Florida Network Rollout Simulation
'''
import math
import random
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import shapefile
from matplotlib import cm
from matplotlib.path import Path

# Read in the population data and county shapes
county_data = pd.read_csv('../data/USA_Counties_(Generalized).csv')
pop_data = pd.DataFrame(county_data, columns = ['NAME', 'POPULATION', 'POP_SQMI', 'SQMI'])
county_shapes = shapefile.Reader('../data/county_shapefiles/USA_Counties_(Generalized)')
# Useful global stats
num_counties = len(county_data)
max_pop_sqmi = max(pop_data['POP_SQMI'])
median_pop_sqmi = np.median(pop_data['POP_SQMI'])
avg_pop_sqmi = np.average(pop_data['POP_SQMI'])


def getCounty(point):
	#Returns the (index, name) of the county containing the specified point
	# or 'N/A' if not in a known county
	for c in range(len(county_shapes)):
		shape = county_shapes.shape(c)
		lon = np.zeros((len(shape.points),1))
		lat = np.zeros((len(shape.points),1))
		countybbox = Path(shape.points)
		if countybbox.contains_point(point):
			return (c,pop_data['NAME'][c])
	return (-1, 'N/A')

def getCountyColor(county):
# Returns the bin's intended colormap value
	pop_dense = pop_data.loc[county]['POP_SQMI']
	if pop_dense > 750 : return 1.0
	if pop_dense > 250 : return 0.8
	if pop_dense > 100 : return 0.6
	if pop_dense >  50 : return 0.4
	return 0.2
	
def getCountySpread(county):
# Returns the local spread by bin
	pop_dense = pop_data.loc[county]['POP_SQMI']
	if pop_dense > 750 : return 0.75
	if pop_dense > 250 : return 0.25
	if pop_dense > 100 : return 0.10
	if pop_dense >  50 : return 0.05
	return 0.02

##############################
##### Class declaration  #####
##############################

class Node:
	def __init__(self, position, addr = 0, parent=0, county = (-1, 'N/A'), home_city = []):
		self.addr = addr		# Unique id, determined by index in containing network
		self.position = position 	# (Longitude, Latitude)
		# Links
		self.reachable   = [] 		# List of nodes that can possibly be reached
		self.neighbor_dist = {}		# Dict of distances to nodes {node: distance}
		self.children    = []		# Addresses of nodes this node is responsible for creating
		self.parent = parent		# Address of node that spawned this node
		# Location
		self.county = county		# County by location, use to find local pop density
		self.home_city= home_city 	# First city network attached, used to find victory condition
		self.network = None			# For accessing network attributes
		
class Network:
	def __init__(self):
		self.nodes = []			# List of all Nodes
		self.history = []		# Node count per iteration
		self._disthistory = {}  # Store distances for memoization shortcut
		self.cities = {}
		# City index, easy method of accessing connected city matrix {'name': index}
		self.c_index = {}
		self.connected_cities = [] # Adjacency matrix for connected cities

	def init_connected_cities(self):
	# Sets up the city connection part of the network
		self.connected_cities = np.zeros((len(self.cities), len(self.cities)))
		# Connect each city to itself
		for diagonal in range(len(self.cities)): self.connected_cities[diagonal][diagonal] = 1

	########################
	##### Node methods #####
	########################
	def add_node(self, position, parent=0, county=None, home_city = None):
		# Initiates a node and automatically enters it into the networks list
		# returns it for specific reference
		if county == None: county = getCounty(position)
		if home_city == None: home_city = self.nodes[parent].home_city
		new_node = Node(position, addr=len(self.nodes), parent=parent, county=county,
						home_city=home_city)
		new_node.network = self
		self.nodes.append(new_node)
		#print(f'add_node position: {position} county: {county} home city: {home_city}')
		# Put the node on the map
		colormap2 = cm.get_cmap('seismic', 128)
		self.draw_node(new_node, 
				color = [colormap2(self.c_index[new_node.home_city] / len(self.cities))])
		return new_node

	def node_distance(self, a, b):
	# Returns the distance between nodes a and b, in miles
		def hav(theta):    return math.sin(theta/2)**2    # Haversine formula
		def archav(theta): return math.asin(theta**0.5)*2 # arcHaversine formula

		# Initialize history 
		if self._disthistory == None: self._disthistory = {}
		if self._disthistory.get((a.position,b.position)) != None :
			return self._disthistory[(a,b)]

		# Calculates miles between (lon,lat) points a and b
		earth_radius = 3960 #3958.761 but source was lost?
		deg_to_rad = (math.pi/180)
		a_rad = (a.position[0]*deg_to_rad, a.position[1]*deg_to_rad)
		b_rad = (b.position[0]*deg_to_rad, b.position[1]*deg_to_rad)
		d_lon = abs(b.position[0]-a.position[0])*deg_to_rad
		d_lat = abs(b.position[1]-a.position[1])*deg_to_rad

		# Calculate with haversine formula
		havdist = hav(d_lat) + (1-hav(d_lat)-hav(a_rad[1]+b_rad[1]))*hav(d_lon)
		distance = earth_radius * archav(havdist)
		self._disthistory[(a,b)] = distance
		return distance	

	##########################
	##### Update methods #####
	##########################
	def spawn_node(self, parent_node, force=False):
	# Simulate a probability of spawning a child node, if spawn occurs,
	# generate a random located node near this parent node, using a gaussian distribution
		spawning = False
		if len(parent_node.children) > MAX_CHILDREN and not force: return # apply limit
		#local_spread = county_data.loc[parent_node.county[0]]['POP_SQMI'] / max_pop_sqmi
		local_spread = getCountySpread(parent_node.county[0])
		spawn_chance = random.random()
		spawning = spawn_chance < BASE_SPREAD_CHANCE + 0.1*local_spread
		#print(f'\tspawn chance: {spawn_chance} < {local_spread}: {spawning}')
		if spawning or force:
			#print(f'\tcounty {parent_node.county} local spread {local_spread}')
			#print(f"county {parent_node.county} popsqmi {county_data.loc[parent_node.county[0]]['POP_SQMI']}")
			# Generate a random position(on land), retry if in water
			actually_on_map = False
			while not actually_on_map:
				new_x = random.gauss(parent_node.position[0], SPREAD_FACTOR*local_spread)
				new_y = random.gauss(parent_node.position[1], SPREAD_FACTOR*local_spread)
				new_county = getCounty((new_x,new_y))
				if new_county[0] != -1: actually_on_map = True
			# Add node to network list
			new_node = self.add_node((new_x, new_y), parent=parent_node.addr, county=new_county)
			parent_node.children.append(new_node.addr)
			#print(f'\tNew node {new_node.addr} at {new_x, new_y}')
					

	def update_nodes(self):
	# Generate new nodes then check connections between them, update county averages
		# Tell each node to attempt spawn, track results
		#print(f'updating {len(self.nodes)} nodes')
		for node in self.nodes:
			self.spawn_node(node)
		self.history.append(len(self.nodes)) # Track growth of network
		if len(self.history) > 1: print(f'\tCreated {self.history[-1] - self.history[-2]} nodes, total: {len(self.nodes)}')

		# Separate loop to account for new nodes
		visited = []
		unvisited = [node for node in self.nodes] # COPY!
		while len(unvisited) != 0:
			cur_node = unvisited.pop()
			for other_node in unvisited:
				self.update_node_connections(cur_node, other_node)
			visited.append(cur_node)

	def update_node_connections(self, a, b):
	# Check distance between nodes, put them in the list of reachable direct neighbors
		#if b not in a.connections.values(): # Skip connected nodes
		if len(a.reachable) >= MAX_CONNECTIONS or len(b.reachable) >= MAX_CONNECTIONS :
			return
		distance = self.node_distance(a,b)
		if  distance < RANGE:
			# Don't add if already known connection
			if not b.addr in a.reachable: a.reachable.append(b.addr)
			if not a.addr in b.reachable: b.reachable.append(a.addr)
			# Put link on map
			self.draw_link(a,b)

			a.neighbor_dist[b.addr] = distance; b.neighbor_dist[a.addr] = distance
			# Communicate to each other what cities they connect to now
			# Connect cities if both connected to distinct cities
			if not None in (a.home_city, b.home_city) and a.home_city != b.home_city:
				# Only report new connections
				if self.connected_cities[self.c_index[a.home_city]][self.c_index[b.home_city]] == 0:
					# Update network connected city matrix
						self.connected_cities[self.c_index[a.home_city]][self.c_index[b.home_city]] = 1
						self.connected_cities[self.c_index[b.home_city]][self.c_index[a.home_city]] = 1
						print("=================MULTI CITY CONNECTION FORMED=================")
						print(f'=== CONNECTED {a.home_city} and {b.home_city} ===')
						print(self.connected_cities)
			# Adding unlinked to existing city
			if a.home_city == None and b.home_city != None: a.home_city = b.home_city
			if b.home_city == None and a.home_city != None: b.home_city = a.home_city

	def checkVictoryCondition(self):
		# Returns if all currently existing cities are connected
		for i in range(len(self.cities)):
			victory_condition = True
			for j in range(len(self.cities)):
				if self.connected_cities[i][j] == 0:
					victory_condition = False
			if victory_condition: return True
		return False

	def prim(self, root, visible=False):
	# Finds a minimum spanning tree starting at node root
	# Returns S, the list of nodes in the MST, this can be used to test if a city is connected
		S = [root.addr]
		T = []
		last_S_len = 0
		while len(S) - last_S_len != 0: # Stop if no new nodes added to MST
			# Find least cost edge with one end in s and the other not
			last_S_len = len(S)
			least_cost = float('inf')
			edge = None
			for s in S:
				for addr in self.nodes[s].reachable:
					if addr not in S: 
						if self.nodes[s].neighbor_dist[addr] < least_cost:
							least_cost = self.nodes[s].neighbor_dist[addr]
							edge = (s,addr)
			if edge != None:
				T.append(edge)
				S.append(edge[1])
				if visible:
					self.draw_link(self.nodes[edge[0]], self.nodes[edge[1]],
								   color='white', zorder=500)
		print(f'LEN OF MST: {len(S)}')
		return S
	
	def get_subnet_diameter(self, nodes):
	# Returns the greatest inter-node distance in a subset of nodes
	# Useful for determining size of a MST found with prim
	# In fact since this was made for that purpose, the nodes list must be addresses, sorry
		diameter = 0;
		visited = []
		unvisited = [node for node in nodes]
		while len(unvisited) != 0:
			cur_node = unvisited.pop()
			for other_node in unvisited:
				cur_dist = self.node_distance(self.nodes[cur_node], self.nodes[other_node])
				if cur_dist > diameter: diameter = cur_dist;
			visited.append(cur_node)
		return diameter


	def main_loop_iteration(self):
		florida.update_nodes()
		return florida.checkVictoryCondition()
		
	#################################
	##### Launch the Simulation #####
	#################################

	def simulate(self):
	# launch program with live node map
		fig = plt.figure()
		ax = plt.subplot(1,1,1)
		plt.xlabel('Longitude') ; plt.ylabel('Latitude')
		# Draw map
		self.draw_map()
		# Draw data iteratively
		for ITER in range(int(ITERATIONS/ITER_BATCH_SIZE)):
			for STEP in range(ITER_BATCH_SIZE):
				print(f"ITERATION {ITER*ITER_BATCH_SIZE+STEP}")
				if END_ON_VICTORY and self.main_loop_iteration(): 
					print(f"VICTORY DETECTED IN ITERATION {ITER}")
					break
				fig.canvas.draw()
				fig.canvas.flush_events()
				fig.show()
			user_action = input("Examine the figure. [C]ontinue [P]rim e[X]it: ")
			if user_action in ['P', 'p']:
				mst = florida.prim(florida.nodes[florida.c_index[prim_city]], visible=True)
				print(f"Diameter of {prim_city}'s network: {florida.get_subnet_diameter(mst)} miles")
			if user_action in ['X', 'x']:
				exit()

	############################
	##### Graphics methods #####
	############################

	def draw_node(self, node, color='blue', zorder=200):
	# Plots this point on the graph
		plt.scatter(node.position[0], node.position[1], c=color, zorder=zorder)

	def draw_circle(self, position, radius=0.05, color='blue', fill=False, zorder=150):
	# Draws a circle around the node, 
		circ = plt.Circle(position, radius=radius, color=color, fill=fill, zorder=zorder)
		ax.add_patch(circ)

	def draw_link(self, a, b, color='black', zorder=200):
	# draws the link between two nodes
		plt.plot((a.position[0], b.position[0]), (a.position[1], b.position[1]),
		color=color, zorder=zorder, linewidth=1)
	
	def draw_map(self):
	# Graph Florida with county pop/mi^2 heatmap
		#Prepare colormap for density display
		colormap = cm.get_cmap('RdYlGn', 128)
		# Initiate graph/map
		for c in range(len(county_shapes)):
			shape = county_shapes.shape(c)
			lon = np.zeros((len(shape.points),1))
			lat = np.zeros((len(shape.points),1))
			for p in range(len(shape.points)):
				lon[p] = shape.points[p][0]
				lat[p] = shape.points[p][1]
			#cmap_value = 1-(pop_data.loc[c]['POP_SQMI']/max_pop_sqmi)
			cmap_value = 1-getCountyColor(c)
			plt.fill(lon, lat,
					 facecolor=colormap(cmap_value),
					 edgecolor='gray', linewidth=2, zorder=0)

##########################
##### Text Interface #####
##########################

florida = Network()
city_letter_choices = ['c', 'g', 'j', 'l', 'b', 'm', 'o', 's', 't', 'w']
city_choices = {
				'c': ('chattahoochee',  (-84.8429759, 30.7051916)),
				'g': ('gainesville', 	(-82.32483, 29.65163)),
				'j': ('jacksonville',  	(-81.65565, 30.33218)),
				'l': ('lakeland',		(-81.94980, 28.03947)),
				'b': ('melbourne', 		(-80.60811, 28.08363)),
				'm': ('miami', 			(-80.19366, 25.77427)),
				'o': ('orlando', 	 	(-81.37924, 28.53834)),
				's': ('stpetersburg',  	(-82.67927, 27.77086)),
				't': ('tampa', 			(-82.45843, 27.94752)),
				'w': ('westpalmbeach', 	(-80.13865, 26.82339))
				}
# User interface
print("Florida network rollout simulator")
if input('use all defaults? [y/n]: ') not in ['Y', 'y', '']:
	print("\tCities:")
	print("\t\t[c]hattahoochee")
	print("\t\t[g]ainesville")
	print("\t\t[j]acksonville")
	print("\t\t[l]akeland")
	print("\t\tmel[b]ourne")
	print("\t\t[m]iami")
	print("\t\t[o]rlando")
	print("\t\t[s]t petersburg")
	print("\t\t[t]ampa")
	print("\t\t[w]est palm beach")
	root_cities = input('Enter the letter(s) of the cities to start as root nodes: ')
	prim_alg    = input('Show MST of any city? (limit one) [y/n]: ') in ['Y', 'y']
	prim_city   = None
	investing 	= input('Special investment in any cities? [y/n]: ') in ['Y', 'y']
	for c in root_cities:
		if c in city_letter_choices:
			city_info = city_choices[c]
			florida.c_index[city_info[0]] = len(florida.cities)
			florida.cities[city_info[0]] = city_info[1]
			city_node = florida.add_node(city_info[1], home_city = city_info[0])
			if prim_alg and prim_city == None:
				if input(f' Span MST from {city_info[0]} ? [y/n]: ') == 'y': prim_city = city_info[0]
			if investing:
				investment = input(f'{city_info[0]} investment (extra nodes at start): ')
				if investment in ['', 'n']: investment = 0 # Allow easy skipping
				for i in range(int(investment)): 
					# Fix requirement to force spawn
					BASE_SPREAD_CHANCE=0.20; SPREAD_FACTOR=0.15; MAX_CHILDREN= float('inf')
					florida.spawn_node(city_node, force=True)
		else: 
			print(f'Unknown city selection {c}')
			exit()
	if (prim_alg and prim_city == None):
		print('No city specified for MST, cancelling MST calculation...')
		prim_alg = False
	ITERATIONS = input("How many iterations to run? (default=100): ")
	if ITERATIONS ==  '': ITERATIONS = 100 
	else: ITERATIONS = int(ITERATIONS)
	ITER_BATCH_SIZE= input("How many iterations between examinations? (default=20): ")
	if ITER_BATCH_SIZE ==  '': ITER_BATCH_SIZE = 20 
	else: ITER_BATCH_SIZE = int(ITER_BATCH_SIZE)
	RANGE = input('Node connection range? (default = 2.0): ')
	if RANGE ==  '': RANGE = 2.0 
	else: RANGE = float(RANGE)
	SPREAD_FACTOR = input('Node spread factor? (default = 0.15): ')
	if SPREAD_FACTOR ==  '': SPREAD_FACTOR =  0.15
	else: SPREAD_FACTOR = float(SPREAD_FACTOR)
	BASE_SPREAD_CHANCE = input('Node spawn chance? (default = 0.20)')
	if BASE_SPREAD_CHANCE ==  '': BASE_SPREAD_CHANCE =  0.20
	else: BASE_SPREAD_CHANCE = float(BASE_SPREAD_CHANCE)
	MAX_CONNECTIONS = input('Max node connection count? (default = no limit): ')
	if MAX_CONNECTIONS == '': MAX_CONNECTIONS = float('inf')
	else: MAX_CONNECTIONS = int(MAX_CONNECTIONS)
	MAX_CHILDREN = input('Max node child count? (default = no limit): ')
	if MAX_CHILDREN == '': MAX_CHILDREN = float('inf')
	else: MAX_CHILDREN = int(MAX_CHILDREN)
	END_ON_VICTORY = input('End simulation on victory condition? (default = y): ')
	if END_ON_VICTORY in ['y', 'Y', 'True', ''] : END_ON_VICTORY = True
	else: END_ON_VICTORY = False
else : # Load defaults
	florida.cities = {'jacksonville':  	(-81.65565, 30.33218),
					  'gainesville':	(-82.32483, 29.65163),
					  'lakeland':		(-81.94980, 28.03947),
					  'melbourne':		(-80.60811, 28.08363),
					  'miami': 			(-80.19366, 25.77427),
					  'orlando': 	 	(-81.37924, 28.53834),
					  'stpetersburg':  	(-82.67927, 27.77086),
					  'tampa': 			(-82.45843, 27.94752),
					  'westpalmbeach': 	(-80.13865, 26.82339)}
	florida.c_index = {'jacksonville': 	 0,
					   'gainesville':	 1,
					   'lakeland':		 2,
					   'melbourne':		 3,
					   'miami':			 4,
					   'orlando':		 5,
					   'stpetersburg':	 6,
					   'tampa':			 7,
					   'westpalmbeach':	 8}
	for city in florida.cities.keys(): 
		florida.add_node(florida.cities[city], home_city = city)
	ITERATIONS 			= 100
	RANGE 				= 2.0
	SPREAD_FACTOR 		= 0.15
	BASE_SPREAD_CHANCE 	= 0.20
	MAX_CONNECTIONS 	= float('inf')
	MAX_CHILDREN		= float('inf')
	END_ON_VICTORY		= True
	ITER_BATCH_SIZE		= 20
	prim_alg = False
	prim_city = None

###############################
##### Execute Simulation  #####
###############################
florida.init_connected_cities()
florida.simulate()
