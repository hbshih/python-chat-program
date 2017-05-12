# python-chat-program

This program is an instant chat program that supports message exchanges between peers directly. To find out which chatroom groups are available and discover the contact information of all group members in the chatroom, the system uses a Room server to keep track of the information.

The P2PChat program accepts three command line arguments: 
P2PChat <roomserver_address> <roomserver_port> <myport> 
with <roomserver_address> specifies the hostname or IP address of the Room server, <roomserver_port> specifies the port number listened by the Room server, and <myport> specifies the listening port number used by the P2PChat program (for accepting TCP connections). 

