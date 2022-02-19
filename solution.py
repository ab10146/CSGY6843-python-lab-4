import socket
from socket import *
import os
import sys
import struct
import time
import select
import statistics
# Should use stdev

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

        # Fetch the ICMP header from the IP packet
        # Per the lab: "The ICMP header starts after bit 160 of the IP header".
        # Given 8 bits in a byte, ICMP header starts at byte 20 (160/8=20).
        # 8+8+16+16+16=64; 64/8=8; ICMP header is 8 bytes long. ICMP = byte[20:28]
        # Not populating checksum or sequence as I don't reference those values below.
        icmpType, icmpCode, _, icmpID, _ = struct.unpack("bbHHh", recPacket[20:28])

        if ID == icmpID and icmpType == 0 and icmpCode == 0:
            # 28th byte has the added time.time data. Get the size of added float data to use in only
            # grabbing the expected float time.time data from when the packet was sent. This value
            # can then be used to determine the returned delay based on the received time.
            return timeReceived - struct.unpack("d", recPacket[28:28 + struct.calcsize("d")])[0]

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
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data)

    # Get the right checksum, and put in the header

    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network  byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data

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
    # timeout=1 means: If one second goes by without a reply from the server,
    # the client assumes that either the client's ping or the server's pong is lost
    vars = ['0', '0.0', '0', '0.0']

    try:
        dest = gethostbyname(host)
        print("Pinging " + dest + " using Python:")
        print("")

        # Calculate vars values and return them
        # Send ping requests to a server separated by approximately one second
        pMin = pMax = 0
        dVals = []
        for i in range(0,4):
            delay = doOnePing(dest, timeout) * 1000
            print(delay)
            dVals.append(delay)
            if i == 0:
                pMin = pMax = delay
            else:
                pMin = min(pMin, delay)
                pMax = max(pMax, delay)

            time.sleep(1)  # one second

        vars = [str(round(pMin, 2)), str(round(statistics.mean(dVals), 2)),
                str(round(pMax, 2)), str(round(statistics.stdev(dVals), 2))]
    except OSError:
        # If the host doesnt exist, continue on.
        pass

    return vars

if __name__ == '__main__':
    ping("google.co.il")
