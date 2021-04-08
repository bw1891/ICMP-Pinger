from socket import *
import os
import sys
import struct
import time
import select
import binascii
# Should use stdev
from statistics import *

ICMP_ECHO_REQUEST = 8


def checksum(string):
   csum = 0
   countTo = (len(string) // 2) * 2
   count = 0

   while count < countTo:
       thisVal = (string[count + 1]) * 256 + (string[count])
       csum += thisVal
       csum &= 0xffffffff
       count += 2

   if countTo < len(string):
       csum += (string[len(string) - 1])
       csum &= 0xffffffff

   csum = (csum >> 16) + (csum & 0xffff)
   csum = csum + (csum >> 16)
   answer = ~csum
   answer = answer & 0xffff
   answer = answer >> 8 | (answer << 8 & 0xff00)
   return answer



def receiveOnePing(mySocket, ID, timeout, destAddr):
   timeLeft = timeout

   while 1:
       startedSelect = time.time()
       whatReady = select.select([mySocket], [], [], timeLeft)
       howLongInSelect = (time.time() - startedSelect)
       if whatReady[0] == []:  # Timeout
           return "Request timed out."

       timeReceived = time.time()
       recPacket, addr = mySocket.recvfrom(1024)

       # Fill in start

       # Fetch the ICMP header from the IP packet

       # IP header = 20 bytes
       # ICMP header = 8 bytes (starts at index 20!)
       # Timestamp is from byte 28 to 36 (part of data in icmp payload)
       # TTL is from bytes 8 to 9
       # Source IP is bytes 12 to 15

       #send_time, = struct.unpack('d', recPacket[28:])
       #header = struct.unpack('bbHHh', recPacket[20:28])
       #print("HEADER =",header)

       # Fetch the ICMP header from the IP packet
       icmp_type, icmp_code, icmp_checksum, icmp_id, icmp_seq, timeSent = struct.unpack('bbHHhd', recPacket[20:36])
       
       # Get TTL from IP header
       ttl, = struct.unpack('b', recPacket[8:9])
       #print("TTL =",ttl)

       #print("TYPE =",icmp_type)
       #print("CODE =", icmp_code)
       #print("CHECKSUM =", icmp_checksum)
       #print("ID =", icmp_id)
       #print("SEQ = ",icmp_seq)
       #print("SENT =", timeSent)
       
       # Get IP Header
       ip_header = struct.unpack('!BBHHHBBH4s4s',recPacket[:20])
       
       # Get source address from IP header
       sourceAddress = inet_ntoa(ip_header[8])
       #print(sourceAddress)

       
       # Calculate RTT
       rtt = round(((timeReceived - timeSent) * 1000),7) # Convert to milliseconds

       # Get Packet Length
       packetLength = len(recPacket)

       #print("Reply from ",sourceAddress,": ","bytes=",packetLength," time=",rtt,"ms"," TTL=",ttl, sep='')

       vars = (sourceAddress,packetLength,rtt,ttl)
       return vars
       # Fill in end
       timeLeft = timeLeft - howLongInSelect
       if timeLeft <= 0:
           return "Request timed out."


def sendOnePing(mySocket, destAddr, ID):
   # Header is type (8), code (8), checksum (16), id (16), sequence (16)

   myChecksum = 0
   # Make a dummy header with a 0 checksum
   # struct -- Interpret strings as packed binary data
   header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
   data = struct.pack("d", time.time())
   #print("DATA - TIMESTAMP = ", struct.unpack('d', data))
   # Calculate the checksum on the data and the dummy header.
   myChecksum = checksum(header + data)

   # Get the right checksum, and put in the header

   if sys.platform == 'darwin':
       # Convert 16-bit integers from host to network  byte order
       myChecksum = htons(myChecksum) & 0xffff
   else:
       myChecksum = htons(myChecksum)


   header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
   #print("HEADER =", header)
   packet = header + data
  #print("PACKET =", packet)

   mySocket.sendto(packet, (destAddr, 1))  # AF_INET address must be tuple, not str


   # Both LISTS and TUPLES consist of a number of objects
   # which can be referenced by their position number within the object.

def doOnePing(destAddr, timeout):
   icmp = getprotobyname("icmp")


   # SOCK_RAW is a powerful socket type. For more details:   http://sockraw.org/papers/sock_raw
   mySocket = socket(AF_INET, SOCK_RAW, icmp)

   myID = os.getpid() & 0xFFFF  # Return the current process i
   sendOnePing(mySocket, destAddr, myID)
   delay = receiveOnePing(mySocket, myID, timeout, destAddr)
   mySocket.close()
   return delay


def ping(host, timeout=1):
   # timeout=1 means: If one second goes by without a reply from the server,      # the client assumes that either the client's ping or the server's pong is lost
   dest = gethostbyname(host)
   print("Pinging " + dest + " using Python:")
   print("")
   # Calculate vars values and return them
   #  vars = [str(round(packet_min, 2)), str(round(packet_avg, 2)), str(round(packet_max, 2)),str(round(stdev(stdev_var), 2))]
   # Send ping requests to a server separated by approximately one second
  
   #packet_min = 99999
   #packet_sum = 0
   #packet_avg = 0
   count = 0
   #packet_max = 0
   rtt_all = ()

   
   for i in range(0,4):
       delay = doOnePing(dest, timeout)
       #print(delay)
       print("Reply from ",delay[0],": ","bytes=",delay[1]," time=",delay[2],"ms"," TTL=",delay[3], sep='')
       #rtt = delay[2]
       #packet_min = min(packet_min, rtt)
       #packet_max = max(packet_max, rtt)
       #packet_sum+=rtt
       rtt_all = rtt_all +(delay[2],)
       count+=1
       time.sleep(1)  # one second
   #print("All =", rtt_all)
   packet_min = min(rtt_all)
   packet_max = max(rtt_all)
   packet_avg = sum(rtt_all) / len(rtt_all)
   stdev_var = list(rtt_all)
   packet_loss = 100 - ((len(rtt_all) / count) * 100)
   
   
   vars = [str(round(packet_min, 2)), str(round(packet_avg, 2)), str(round(packet_max, 2)),str(round(pstdev(stdev_var), 2))]
   print("\n---",host,"ping statistics ---")
   print(count," packets transmitted, ", len(rtt_all)," packets received, ",packet_loss,"% packet loss", sep='' )
   print("round-trip min/avg/max/stddev = ",vars[0],"/",vars[1],"/",vars[2],"/",vars[3]," ms", sep='')
   return vars

if __name__ == '__main__':
   ping("google.co.il")
   #ping("92.242.140.241")
   #ping("no.no.e")
   #ping("127.0.0.1")
