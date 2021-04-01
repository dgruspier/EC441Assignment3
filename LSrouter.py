####################################################
# LSrouter.py
# Name: Daniel Gruspier
# BU ID: U88626811
#####################################################

import sys
from collections import defaultdict
from router import Router
from packet import Packet
from json import dumps, loads
import networkx as nx # implement Dijkstra's algorithm as nx.dijkstra_path

class LSrouter(Router):
    """Link state routing protocol implementation."""

    def __init__(self, addr, heartbeatTime):
        """TODO: add your own class fields and initialization code here"""
        Router.__init__(self, addr)  # initialize superclass - don't remove
        self.heartbeatTime = heartbeatTime
        self.last_time = 0
        # Hints: initialize local state
        self.fwd_table = {}				# Format is dstAddr:port
	self.link_state = {}				# Format is addr:cost
	self.neighbors = {}				# Format is addr:port
	self.seq = 0					# Sequence number	
	self.G = nx.Graph()				# For tracking foreign link states
	self.G.add_node(self.addr)			# Add myself to the network graph
	self.most_recent = ''
	self.all_LS = {}


    def handlePacket(self, port, packet):
        """TODO: process incoming packet"""
        if packet.isTraceroute():
            # Hints: this is a normal data packet
            # if the forwarding table contains packet.dstAddr
            #   send packet based on forwarding table, e.g., self.send(port, packet)
            if packet.dstAddr in self.fwd_table:		# If I have dst in my forwarding table
		if self.fwd_table[packet.dstAddr] != 0:		# and there is a path to it...
			self.send(self.fwd_table[packet.dstAddr],packet)	# Forward it accordingly
        else:
            # Hints: this is a routing packet generated by your routing protocol
            # check the sequence number
            # if the sequence number is higher and the received link state is different
            #   update the local copy of the link state
            #   update the forwarding table
            #   broadcast the packet to other neighbors
	    msg = loads(packet.content)				# De-json the packet content
	    seq_num = msg[0]					# Take note of the sequence number
	    recv_state = msg[1]					# Take note of the recv'd link state
	    self.most_recent = msg
	    update = True
	    if packet.srcAddr in self.all_LS:
	    	if recv_state == self.all_LS[packet.srcAddr]:
			update = False
		else:
			self.all_LS[packet.srcAddr] = recv_state
	    else:
		self.all_LS[packet.srcAddr] = recv_state 
            if seq_num > self.seq and update:			# As long as this is a new seq num...
		self.seq = seq_num				# Update my sequence number
		if self.G.has_node(packet.srcAddr):		# If topology has this address:
			self.G.remove_node(packet.srcAddr)	# Prepare to update it
		self.G.add_node(packet.srcAddr)			
		for address in recv_state:			# Loop through recv'd LS
			if self.G.has_edge(packet.srcAddr,address):	# If an edge exists b/t them:
				self.G.remove_edge(packet.srcAddr,address)			# Remove it
			self.G.add_edge(packet.srcAddr,address,weight=recv_state[address])	# Update topology
			if not address in self.fwd_table and address != self.addr:	# Add src's neighbors (except me) to my fwd_table
				self.fwd_table[address] = 0
		if not packet.srcAddr in self.fwd_table:	# Add src to my fwd_table if needbe
			self.fwd_table[packet.srcAddr] = 0
		for dst in self.fwd_table:			# Update my forwarding table
			try:
				path = nx.dijkstra_path(self.G,self.addr,dst,'weight')	# Calculate shortest path to each entry
				self.fwd_table[dst] = self.neighbors[path[1]]	# path = [me, neighbor, ...]
			except:
				self.fwd_table[dst] = 0
		for dst in self.neighbors:			# Forward to all neighbors...
			if self.neighbors[dst] != port:		# Except the neighbor from whom I got the packet
				self.send(self.neighbors[dst],packet)
				pass


    def handleNewLink(self, port, endpoint, cost):
        """TODO: handle new link"""
        # Hints:
        # update the forwarding table
        # broadcast the new link state of this router to all neighbors
        self.link_state[endpoint] = cost	# Create entry in my link state
	self.neighbors[endpoint] = port		# Create entry in neighbors
	self.fwd_table[endpoint] = port		# Create entry in my forwarding table

	self.G.add_node(endpoint)		# Add new neighbor to network topology
	self.G.add_edge(self.addr,endpoint,weight=cost)	# Connect to myself in network topology
	for dst in self.fwd_table:		# Update my forwarding table
		try:
			path = nx.dijkstra_path(self.G,self.addr,dst,'weight')	# Calcualte shortest path to each entry
			self.fwd_table[dst] = self.neighbors[path[1]]	# path = [me, neighbor, ...-
		except:
			self.fwd_table[dst] = 0
	self.seq += 1				# Advance my sequence number

	for dst in self.neighbors:		# Forward to all neighbors
		pkt = Packet(kind=Packet.ROUTING,srcAddr=self.addr,dstAddr=dst)	# Make a routing packet
		pkt.content = dumps([self.seq,self.link_state])			# Convert seq num and my LS to JSON
		self.send(self.neighbors[dst],pkt)
		pass

    def handleRemoveLink(self, port):
        """TODO: handle removed link"""
        # Hints:
        # update the forwarding table
        # broadcast the new link state of this router to all neighbors
	
	
	for friend in self.neighbors:			# Identify address where link was
		if self.neighbors[friend] == port:
			to_remove = friend
			break
	self.G.remove_edge(self.addr,to_remove)	# Disconnect myself from ex-neighbor in network topology
	self.link_state.pop(to_remove)	# Delete entry from my link state
	self.neighbors.pop(to_remove)	# Delete entry from my neighbors
	#self.fwd_table[to_remove] = 0	# Prepare to modify forwarding table

	
	for dst in self.fwd_table:	# Update forwarding table
		try:
			path = nx.dijkstra_path(self.G,self.addr,dst,'weight')	# Calculate best path to each entry
			self.fwd_table[dst] = self.neighbors[path[1]]	# path = [me, neighbor, ...]		
		except:
			self.fwd_table[dst] = 0
			#self.fwd_table.pop(dst)
	self.seq += 1			# Advance my sequence number

	for dst in self.neighbors:	# Forward to all neighbors
		pkt = Packet(kind=Packet.ROUTING,srcAddr=self.addr,dstAddr=dst)	# Make a routing packet
		pkt.content = dumps([self.seq,self.link_state])			# Convert seq num and my LS to JSON
		self.send(self.neighbors[dst],pkt)
		pass    

    def handleTime(self, timeMillisecs):
        """TODO: handle current time"""
        if timeMillisecs - self.last_time >= self.heartbeatTime:
            self.last_time = timeMillisecs
            # Hints:
            # broadcast the link state of this router to all neighbors
            #for neighbor in link_state:
	    #	self.send(neighbor,link_state)
		#pass
	    for dst in self.neighbors:
	    	pkt = Packet(kind=Packet.ROUTING,srcAddr=self.addr,dstAddr=dst)
		pkt.content = dumps([self.seq,self.link_state])
		self.send(self.neighbors[dst],pkt)
		pass

    def debugString(self):
        """TODO: generate a string for debugging in network visualizer"""
	table_str = ''
	for dst in self.fwd_table:
		table_str = table_str + 'For msg going to ' + str(dst) + ' forward to ' + str(self.fwd_table[dst]) + '\n'
        return 'LS: ' + str(self.link_state) + '\n Neighbors: ' + str(self.neighbors) + \
			"\n This router's seq num: " + str(self.seq) + '\n\nMost recent packet contents recvd: \n' + str(self.most_recent) \
			+ '\n' + table_str
